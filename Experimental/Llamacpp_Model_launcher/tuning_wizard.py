# Llamacpp_Model_launcher/tuning_wizard.py

import time
import requests
import re
from Llamacpp_Model_launcher.parameters_db import BENCHMARK_PROMPT


class TuningWizard:
    """Acts as the 'brain' for the tuning process. It decides what to test and yields high-level commands to the UI."""

    def __init__(self, analysis_results, initial_params):
        self.analysis = analysis_results
        self.initial_params = initial_params
        self.best_config = {'params': {}, 'tps': 0.0}
        self.primary_gpu_id = 0  # Will be updated by user choice
        self.base_params = {}  # Will be built dynamically

    def _calculate_dynamic_timeout(self, test_type='benchmark'):
        """
        Calculates a dynamic timeout in milliseconds based on model size.
        This provides a more generous time limit for larger models that may cause
        system thrashing or have a long initial startup time.

        Args:
            test_type (str): The type of test being run ('metadata', 'ngl_test', 'benchmark').
                             This allows for different base calculations.

        Returns:
            int: The calculated timeout in milliseconds.
        """
        # A fixed, generous timeout for simple metadata extraction, which should be fast.
        if test_type == 'metadata':
            return 45 * 1000  # 45 seconds

        model_size_gb = self.analysis.get('model_size_gb', 15.0)
        # Ensure model_size_gb is a valid number for calculation
        if not isinstance(model_size_gb, (int, float)) or model_size_gb <= 0:
            model_size_gb = 15.0

        # Base timeouts for different test types
        if test_type == 'benchmark':
            # Full benchmark with multiple API calls needs a higher base
            base_ms = 60 * 1000  # 1 minute
        else:  # 'ngl_test'
            # Stability test is just one API call
            base_ms = 45 * 1000  # 45 seconds

        # Scaling factor: add seconds per gigabyte of model size
        per_gb_ms = 10 * 1000  # 10 seconds per GB

        calculated_timeout = base_ms + (model_size_gb * per_gb_ms)

        # Enforce a reasonable minimum and a very high maximum to prevent infinite waits
        min_timeout_ms = 60 * 1000  # 1 minute
        max_timeout_ms = 20 * 60 * 1000  # 20 minutes

        final_timeout = max(min_timeout_ms, min(calculated_timeout, max_timeout_ms))

        return int(final_timeout)

    # --- MAIN DISPATCHER ---
    def run_tuning_wizard(self):
        """The main generator that dispatches tasks based on user choices."""
        yield {'action': 'log', 'message': "\n" + "=" * 25 + " Starting Tuning Wizard " + "=" * 25}

        proposed_optimizations = [
            {'id': 'flash_attn', 'label': 'Enable Flash Attention (--flash-attn)', 'checked': True,
             'params': {'--flash-attn': 'on'}},
            {'id': 'no_mmap', 'label': 'Disable Memory Mapping (--no-mmap)', 'checked': True,
             'params': {'--no-mmap': None}},
            {'id': 'kv_cache_q8', 'label': 'Enable 8-bit KV Cache (-ctk/-ctv q8_0)', 'checked': True,
             'params': {'-ctk': 'q8_0', '-ctv': 'q8_0'}},
            {'id': 'no_warmup', 'label': 'Disable Server Warmup (--no-warmup)', 'checked': True,
             'params': {'--no-warmup': None}},
        ]

        has_draft_model = '-md' in self.initial_params or '--model-draft' in self.initial_params
        if has_draft_model:
            yield {'action': 'log', 'message': "> Draft model detected. Proposing speculative decoding optimizations."}
            proposed_optimizations.extend([
                {'id': 'draft_offload', 'label': 'Fully Offload Draft Model (-ngld 99)', 'checked': True,
                 'params': {'-ngld': '99'}},
                {'id': 'draft_kv_cache', 'label': 'Enable 8-bit KV Cache for Draft Model', 'checked': True,
                 'params': {'--cache-type-k-draft': 'q8_0', '--cache-type-v-draft': 'q8_0'}}
            ])

        yield {'action': 'log', 'message': "\n[PHASE 1] Extracting Model Metadata..."}
        extraction_params = {'--no-warmup': None, '-ngl': '1', '-c': '4096'}
        yield {'action': 'update_params', 'params': extraction_params}
        metadata_timeout = self._calculate_dynamic_timeout('metadata')
        metadata_result = yield {'action': 'extract_layer_count', 'timeout_ms': metadata_timeout}

        if not metadata_result['success']:
            yield {'action': 'log', 'message': "[CRITICAL] Could not determine all model metadata. Halting."};
            return

        self.analysis['model_layers'] = metadata_result['layers']
        self.analysis['model_max_context'] = metadata_result.get('max_context', 32768)
        self.analysis['proposed_optimizations'] = proposed_optimizations
        yield from self._reorder_gpu_list(metadata_result.get('gpus', []))

        user_choices = yield {'action': 'show_summary_view', 'data': self.analysis}

        self.base_params = user_choices.get('selected_optimizations', {})
        yield {'action': 'log',
               'message': f"User settings received. Using base optimizations: {list(self.base_params.keys())}"}

        self.primary_gpu_id = user_choices.get('primary_gpu_id', self._get_best_gpu_id())
        yield {'action': 'log', 'message': f"> User selected Device {self.primary_gpu_id} as the primary GPU."}

        is_multi_gpu = len(self.analysis.get('gpus', [])) > 1
        if is_multi_gpu:
            self.base_params['-mg'] = str(self.primary_gpu_id)

        is_dense_model = self.analysis.get('model_architecture') != 'Mixture of Experts (MoE)'
        if is_multi_gpu and is_dense_model and has_draft_model:
            self.base_params['-devd'] = f'CUDA{self.primary_gpu_id}'
            yield {'action': 'log',
                   'message': f"> Pinning draft model to primary GPU with --device-draft {self.base_params['-devd']}."}

        model_path = self.initial_params.get('-m', self.initial_params.get('--model', ''))
        if 'gpt-oss' in model_path.lower():
            yield {'action': 'log', 'message': "> Applying gpt-oss specific reasoning parameter."}
            self.base_params['--chat-template-kwargs'] = '{"reasoning_effort": "medium"}'

        yield {'action': 'log', 'message': "\n[PHASE 2] Finding Optimal Layer Offload..."}
        best_offload_params = None
        strategy = user_choices.get('offload_strategy')

        if strategy == 'single_gpu':
            best_offload_params = yield from self._tune_single_gpu()
        elif strategy == 'multi_vram':
            best_offload_params = yield from self._tune_multi_vram()
        elif strategy == 'multi_cpu':
            best_offload_params = yield from self._tune_multi_cpu()

        if not best_offload_params:
            yield {'action': 'log',
                   'message': "[CRITICAL] Could not find a working offload configuration. Tuning aborted."};
            return

        yield {'action': 'log', 'message': f"> Optimal offload found: {best_offload_params}"}
        final_params = best_offload_params.copy()

        if user_choices.get('maximize_context'):
            yield {'action': 'log', 'message': "\n[PHASE 3] Maximizing Context Size (Adaptive Search)..."}
            best_context_params = yield from self._tune_context_size_adaptive(final_params)
            if best_context_params and best_context_params != final_params:
                final_params.update(best_context_params)
                yield {'action': 'log', 'message': f"> Optimal context configuration found: {best_context_params}"}
            else:
                yield {'action': 'log', 'message': "> Context tuning failed or was skipped."}

        yield {'action': 'log', 'message': "\n[PHASE 4] Final Performance Benchmark..."}
        benchmark_result = yield from self._run_final_benchmark(final_params)

        if not benchmark_result['success']:
            yield {'action': 'log', 'message': "[CRITICAL] Final configuration was unstable. Tuning aborted."};
            return

        yield {'action': 'log', 'message': "\n" + "=" * 27 + " Tuning Complete " + "=" * 28}
        yield {'action': 'log', 'message': f"Best Performance Found: {benchmark_result['tps']:.2f} t/s"}
        self.best_config = {'params': final_params, 'tps': benchmark_result['tps']}
        yield {'action': 'save_best_params'}

    # --- STRATEGY HELPERS ---
    def _tune_single_gpu(self):
        yield {'action': 'log', 'message': "> Strategy: Single GPU Only"}
        params = {'-ngl': '99', '--split-mode': 'none', '-mg': str(self.primary_gpu_id)}
        yield {'action': 'update_params', 'params': {**self.base_params, **params}}
        timeout = self._calculate_dynamic_timeout('ngl_test')
        result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout}
        if result['success']: return params
        yield {'action': 'log', 'message': "> Single GPU load failed. Asking user how to proceed."}
        user_decision = yield {'action': 'confirm_single_gpu_failure'}
        if user_decision == 'try_multi':
            yield {'action': 'log', 'message': "> User chose to try Multi-GPU. Transitioning strategy."}
            return (yield from self._tune_multi_cpu())
        else:
            yield {'action': 'log', 'message': "> User chose to abort."};
            return None

    def _tune_multi_vram(self):
        yield {'action': 'log', 'message': "> Strategy: Multi-GPU (VRAM Only)"}
        ts_proportions = self._calculate_primary_first_tensor_split(
            self.analysis['gpus'],
            self.analysis['model_size_gb'],
            self.primary_gpu_id
        )
        if not ts_proportions:
            yield {'action': 'log', 'message': "[ERROR] Could not calculate tensor split. Aborting."};
            return None
        ts_string = ",".join([f"{p:.3f}" for p in ts_proportions])
        yield {'action': 'log', 'message': f'> Using "Primary-First" tensor split: {ts_string}'}
        params = {'-ngl': '99', '-ts': ts_string, '-ncmoe': 'REMOVE'}
        yield {'action': 'update_params', 'params': {**self.base_params, **params}}
        timeout = self._calculate_dynamic_timeout('ngl_test')
        result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout}
        if result['success']: return params
        yield {'action': 'log',
               'message': "> Full VRAM offload failed. Automatically transitioning to CPU offload strategy."}
        return (yield from self._tune_multi_cpu())

    def _tune_multi_cpu(self):
        yield {'action': 'log', 'message': "> Strategy: Multi-GPU with CPU Offload"}
        is_moe = self.analysis.get('model_architecture') == 'Mixture of Experts (MoE)'
        if is_moe:
            return (yield from self._tune_moe_multi_cpu())
        else:
            return (yield from self._tune_dense_multi_cpu())

    # --- ADAPTIVE CONTEXT TUNING METHOD ---
    def _tune_context_size_adaptive(self, base_offload_params):
        try:
            low = int(base_offload_params.get('-c', '4096'))
            high = int(self.analysis.get('model_max_context', 32768))
        except (ValueError, TypeError):
            low, high = 4096, 32768

        best_known_params = base_offload_params.copy()

        yield {'action': 'log', 'message': f"> Starting adaptive context search from {low} to {high}..."}

        while low <= high:
            mid_ctx = ((low + high) // 2 // 512) * 512
            if mid_ctx == 0: mid_ctx = 512
            if mid_ctx <= int(best_known_params.get('-c', 0)):
                low = mid_ctx + 512
                continue

            yield {'action': 'log', 'message': f"\n> Testing context size: {mid_ctx}"}

            temp_params = best_known_params.copy()
            temp_params['-c'] = str(mid_ctx)

            is_multi_gpu = '-ts' in temp_params
            max_ts_adjustments = 5 if is_multi_gpu else 0
            test_succeeded = False

            for attempt in range(max_ts_adjustments + 1):
                yield {'action': 'update_params', 'params': {**self.base_params, **temp_params}}
                timeout = self._calculate_dynamic_timeout('ngl_test')
                result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout}
                if result['success']:
                    best_known_params = temp_params.copy()
                    yield {'action': 'log', 'message': f"  > SUCCESS. New best config: {best_known_params}"}
                    test_succeeded = True;
                    break
                if not is_multi_gpu or attempt >= max_ts_adjustments:
                    yield {'action': 'log',
                           'message': f"  > FAILED. No more adjustments to try for this context size."};
                    break

                error_details = result.get('error_details', {})
                failing_device = error_details.get('device_id', -1)
                yield {'action': 'log',
                       'message': f"  > FAILED (OOM on GPU {failing_device}). Attempting to re-balance tensor split."}

                ts_proportions = [float(p) for p in temp_params['-ts'].split(',')]
                victim_idx, beneficiary_idx = failing_device, -1

                if victim_idx != -1 and victim_idx < len(ts_proportions):
                    if victim_idx == self.primary_gpu_id:
                        secondary_gpus = sorted(
                            [(i, p) for i, p in enumerate(ts_proportions) if i != self.primary_gpu_id],
                            key=lambda x: x[1], reverse=True)
                        if secondary_gpus:
                            beneficiary_idx = secondary_gpus[0][0]
                            yield {'action': 'log',
                                   'message': f"  > OOM on primary GPU. Offloading from GPU {victim_idx} to GPU {beneficiary_idx}."}
                    else:
                        beneficiary_idx = self.primary_gpu_id
                        yield {'action': 'log',
                               'message': f"  > OOM on secondary GPU. Offloading from GPU {victim_idx} to primary GPU {beneficiary_idx}."}

                    if beneficiary_idx != -1:
                        ts_step = 0.05
                        if ts_proportions[victim_idx] > ts_step:
                            ts_proportions[victim_idx] -= ts_step
                            ts_proportions[beneficiary_idx] += ts_step
                            temp_params['-ts'] = ",".join([f"{p:.3f}" for p in ts_proportions])
                            yield {'action': 'log',
                                   'message': f"  > Adjusting and retrying. New tensor split: {temp_params['-ts']}"}
                        else:
                            yield {'action': 'log',
                                   'message': f"  > Cannot reduce tensor split for GPU {victim_idx} further."};
                            break
                    else:
                        yield {'action': 'log', 'message': "  > Could not determine a beneficiary GPU."};
                        break
                else:
                    yield {'action': 'log', 'message': f"  > Invalid failing device ID ({failing_device})."};
                    break

            if test_succeeded:
                low = mid_ctx + 512
            else:
                high = mid_ctx - 512

        return best_known_params

    # --- CORE LOGIC HELPERS ---
    def _tune_dense_multi_cpu(self):
        total_layers = self.analysis['model_layers'] + 1
        ts_proportions = self._calculate_primary_first_tensor_split(
            self.analysis['gpus'],
            self.analysis['model_size_gb'],
            self.primary_gpu_id
        )
        if not ts_proportions: return None
        initial_ts_string = ",".join([f"{p:.3f}" for p in ts_proportions])
        yield {'action': 'log', 'message': f'> Using "Primary-First" tensor split: {initial_ts_string}'}
        yield {'action': 'log', 'message': "> Finding a safe baseline NGL via binary search..."}

        low, high, best_known_ngl = 0, total_layers, 0
        while low <= high:
            mid = (low + high) // 2
            if mid == 0:
                low = 1
                continue

            params_for_test = {**self.base_params, '-ts': initial_ts_string, '-ngl': str(mid)}
            yield {'action': 'update_params', 'params': params_for_test}

            # --- FIX: Add an extra, synchronous yield to re-sync the generator flow ---
            yield {'action': 'log', 'message': f"> Binary Search: Testing -ngl {mid}"}

            timeout = self._calculate_dynamic_timeout('ngl_test')
            result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout}

            if result['success']:
                best_known_ngl = mid
                low = mid + 1
            else:
                high = mid - 1

        if best_known_ngl == 0:
            yield {'action': 'log', 'message': "[CRITICAL] Could not find any viable NGL value."}
            return None

        yield {'action': 'log', 'message': f"> Binary search complete. Best safe offload is -ngl {best_known_ngl}."}
        return {'-ngl': str(best_known_ngl), '-ts': initial_ts_string}

    # --- NEW: RESTORED MoE TUNING ALGORITHM ---
    def _tune_moe_multi_cpu(self):
        yield {'action': 'log', 'message': "\n[PHASE 3] Activating MoE multi-GPU tuning strategy (with CPU offload)."}

        total_layers = self.analysis.get('model_layers', 0) + 1
        best_config_params = None

        # Stage 1: Coarse search for the crossover point
        yield {'action': 'log', 'message': "> Stage 1: Coarse search for -ncmoe crossover point..."}
        yield {'action': 'update_params', 'params': {**self.base_params, '-ngl': '99', '-ts': 'REMOVE'}}

        crossover_ncmoe = -1
        for ncmoe_to_test in list(range(0, total_layers, 5)) + [total_layers - 1]:
            yield {'action': 'log', 'message': f"> Coarse Test: -ncmoe {ncmoe_to_test}"}
            yield {'action': 'update_params', 'params': {'-ncmoe': str(ncmoe_to_test)}}
            timeout = self._calculate_dynamic_timeout('ngl_test')
            result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout}

            if result['success']:
                crossover_ncmoe = ncmoe_to_test
                yield {'action': 'log', 'message': f"  > SUCCESS: Model loaded with default tensor split."}
                break

            error_details = result.get('error_details', {})
            if error_details and error_details.get('device_id') != self.primary_gpu_id:
                crossover_ncmoe = ncmoe_to_test
                yield {'action': 'log',
                       'message': f"  > Crossover found. GPU {error_details['device_id']} is now the bottleneck."}
                break
            else:
                yield {'action': 'log',
                       'message': f"  > FAILED: Primary GPU {self.primary_gpu_id} remains the bottleneck."}

        if crossover_ncmoe == -1:
            yield {'action': 'log',
                   'message': f"[CRITICAL] Could not relieve primary GPU {self.primary_gpu_id}. Halting."}
            return None

        # Stage 2: Fine-tuning loop
        yield {'action': 'log', 'message': "\n> Stage 2: Fine-tuning -ncmoe and -ts..."}
        current_ncmoe = max(0, crossover_ncmoe - 5)
        ts_proportions = self._calculate_primary_first_tensor_split(self.analysis['gpus'],
                                                                    self.analysis['model_size_gb'], self.primary_gpu_id)

        if not ts_proportions:
            yield {'action': 'log', 'message': "[CRITICAL] Could not calculate VRAM proportions. Halting."}
            return None

        max_attempts = 40
        for attempt in range(max_attempts):
            current_ts_string = ",".join([f"{p:.3f}" for p in ts_proportions])
            yield {'action': 'log',
                   'message': f"\n> Attempt {attempt + 1}/{max_attempts}: Testing -ncmoe {current_ncmoe} with -ts {current_ts_string}"}

            params_to_test = {**self.base_params, '-ngl': '99', '-ncmoe': str(current_ncmoe), '-ts': current_ts_string}
            yield {'action': 'update_params', 'params': params_to_test}
            timeout = self._calculate_dynamic_timeout('ngl_test')
            result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout}

            if result['success']:
                yield {'action': 'log', 'message': f"  > SUCCESS! Optimal configuration found."}
                best_config_params = {'-ncmoe': str(current_ncmoe), '-ts': current_ts_string, '-ngl': '99'}
                break

            error_details = result.get('error_details', {})
            if not error_details:
                yield {'action': 'log', 'message': f"  > FAILED: Unknown error. Halting."}
                break

            failing_device = error_details.get('device_id', -1)
            yield {'action': 'log', 'message': f"  > FAILED: OOM on Device {failing_device}."}

            if failing_device == self.primary_gpu_id:
                yield {'action': 'log',
                       'message': f"  > Action: Incrementing -ncmoe to relieve GPU {self.primary_gpu_id}."}
                current_ncmoe += 1
            else:
                yield {'action': 'log', 'message': "  > Action: Adjusting -ts to relieve secondary GPU."}
                ts_step = 0.02
                if failing_device < len(ts_proportions) and ts_proportions[failing_device] > ts_step:
                    ts_proportions[failing_device] -= ts_step
                    ts_proportions[self.primary_gpu_id] += ts_step
                else:
                    yield {'action': 'log',
                           'message': f"[WARNING] Cannot reduce tensor split further for device {failing_device}. Incrementing ncmoe instead."}
                    current_ncmoe += 1

            if current_ncmoe >= total_layers:
                yield {'action': 'log', 'message': "[CRITICAL] Reached max ncmoe value. Halting."}
                break

        if not best_config_params:
            yield {'action': 'log',
                   'message': f"\n[CRITICAL] Could not find a working MoE configuration after {max_attempts} attempts."}
            return None

        return best_config_params

    def _run_final_benchmark(self, params_to_test):
        final_benchmark_params = params_to_test.copy()
        try:
            if int(final_benchmark_params.get('-c', 0)) < 4096:
                final_benchmark_params['-c'] = '4096'
                yield {'action': 'log', 'message': "> Forcing benchmark context to 4096 for stability."}
        except (ValueError, TypeError):
            final_benchmark_params['-c'] = '4096'
            yield {'action': 'log', 'message': "> Forcing benchmark context to 4096 for stability."}
        yield {'action': 'update_params', 'params': {**self.base_params, **final_benchmark_params}}
        timeout = self._calculate_dynamic_timeout('benchmark')
        benchmark_result = yield {'action': 'load_and_benchmark', 'timeout_ms': timeout}
        if benchmark_result['success']:
            return {'success': True, 'tps': benchmark_result.get('avg_tps', 0.0)}
        else:
            yield {'action': 'log', 'message': f"> BENCHMARK FAILED: {benchmark_result['error']}"}
            return {'success': False, 'tps': 0.0}

    # --- UTILITY HELPERS ---
    def _get_best_gpu_id(self):
        gpus = self.analysis.get('gpus', []);
        if not gpus: return 0
        try:
            return max(gpus, key=lambda gpu: gpu.get('vram', {}).get('total_gb', 0))['id']
        except (ValueError, KeyError):
            return 0

    def _reorder_gpu_list(self, ground_truth_gpus):
        yield {'action': 'log', 'message': "> Reconciling GPU device order..."}
        if not ground_truth_gpus or not self.analysis.get('gpus') or len(self.analysis.get('gpus', [])) < 2:
            yield {'action': 'log', 'message': "> Single GPU or no ground truth data. Skipping re-ordering."};
            return

        def clean_name(name):
            return re.sub(r'[^a-zA-Z0-9]', '', name.lower().replace("nvidia", "").replace("geforce", ""))

        original_gpus = self.analysis.get('gpus', []);
        reordered_gpus = [];
        unmatched_gpus = list(original_gpus)
        original_map = {clean_name(gpu['name']): gpu for gpu in original_gpus}
        for truth_gpu in sorted(ground_truth_gpus, key=lambda x: x['id']):
            truth_name_clean = clean_name(truth_gpu['name'])
            if truth_name_clean in original_map:
                matched_gpu = original_map[truth_name_clean];
                matched_gpu['id'] = truth_gpu['id']
                reordered_gpus.append(matched_gpu)
                unmatched_gpus = [g for g in unmatched_gpus if clean_name(g['name']) != truth_name_clean]
            else:
                yield {'action': 'log', 'message': f"[WARNING] Could not match ground truth GPU: {truth_gpu['name']}"}
        if unmatched_gpus: reordered_gpus.extend(unmatched_gpus)
        if len(reordered_gpus) == len(original_gpus):
            self.analysis['gpus'] = reordered_gpus
            log_msg = "> Successfully re-ordered GPU list to match llama.cpp:\n";
            for gpu in self.analysis['gpus']: log_msg += f"  - Device {gpu['id']}: {gpu['name']}\n"
            yield {'action': 'log', 'message': log_msg.strip()}
        else:
            yield {'action': 'log', 'message': "[ERROR] GPU list re-ordering failed. Tensor split may be incorrect."}

    def _calculate_primary_first_tensor_split(self, gpus, model_size_gb, primary_gpu_id):
        """
        Calculates a tensor split that prioritizes filling the primary GPU first
        before distributing the remainder to secondary GPUs.
        """
        if not gpus or len(gpus) < 2 or not isinstance(model_size_gb, (int, float)) or model_size_gb <= 0:
            return None

        VRAM_SAFETY_BUFFER_GB = 1.5

        # 1. Separate primary and secondary GPUs
        try:
            primary_gpu = next(gpu for gpu in gpus if gpu['id'] == primary_gpu_id)
        except StopIteration:
            primary_gpu = gpus[0]  # Fallback if the ID isn't found

        secondary_gpus = [gpu for gpu in gpus if gpu['id'] != primary_gpu['id']]

        # 2. Calculate allocations in GB
        allocations_gb = {gpu['id']: 0.0 for gpu in gpus}

        # 3. Allocate to primary GPU first
        primary_usable_vram = max(0, primary_gpu.get('vram', {}).get('free_gb', 0) - VRAM_SAFETY_BUFFER_GB)
        primary_allocation = min(model_size_gb, primary_usable_vram)
        allocations_gb[primary_gpu['id']] = primary_allocation

        # 4. Calculate remaining model size to be distributed
        remaining_model_gb = model_size_gb - primary_allocation

        # 5. Distribute remainder to secondary GPUs
        if remaining_model_gb > 0 and secondary_gpus:
            secondary_usable_vram = {
                gpu['id']: max(0, gpu.get('vram', {}).get('free_gb', 0) - VRAM_SAFETY_BUFFER_GB)
                for gpu in secondary_gpus
            }
            total_secondary_usable_vram = sum(secondary_usable_vram.values())

            if total_secondary_usable_vram > 0:
                for gpu in secondary_gpus:
                    gpu_id = gpu['id']
                    proportion_of_secondary_pool = secondary_usable_vram[gpu_id] / total_secondary_usable_vram
                    secondary_allocation = remaining_model_gb * proportion_of_secondary_pool
                    allocations_gb[gpu_id] += secondary_allocation

        # 6. Convert GB allocations to final proportions
        final_proportions = {gpu_id: alloc_gb / model_size_gb for gpu_id, alloc_gb in allocations_gb.items()}

        # 7. Normalize proportions to ensure they sum to 1.0
        total_proportion = sum(final_proportions.values())
        if total_proportion > 0:
            final_proportions = {gpu_id: p / total_proportion for gpu_id, p in final_proportions.items()}
        else:
            return [1.0 / len(gpus)] * len(gpus)  # Fallback to even split

        # 8. Order the results by GPU ID
        ordered_proportions = [final_proportions[gpu['id']] for gpu in sorted(gpus, key=lambda g: g['id'])]

        return ordered_proportions

    def run_api_benchmark_requests(self):
        for i in range(3):
            try:
                requests.post("http://127.0.0.1:8080/v1/chat/completions",
                              json={"messages": [{"role": "user", "content": BENCHMARK_PROMPT}], "n_predict": 512,
                                    "temperature": 0.1, "seed": 1}, timeout=120)
                if i < 2: time.sleep(2)
            except requests.RequestException as e:
                print(f"[DIAGNOSTICS] API request {i + 1} failed: {e}");
                pass

    def run_stability_api_request(self):
        try:
            requests.post("http://127.0.0.1:8080/v1/chat/completions",
                          json={"messages": [{"role": "user", "content": BENCHMARK_PROMPT}], "n_predict": 50,
                                "temperature": 0.1, "seed": 1}, timeout=300)
        except requests.RequestException as e:
            print(f"[DIAGNOSTICS] Stability API request failed: {e}");
            pass