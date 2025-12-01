# Llamacpp_Model_launcher/tuning_wizard.py

import time
import requests
import re
import math
from Llamacpp_Model_launcher.parameters_db import BENCHMARK_PROMPT

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class TuningWizard:
    """Acts as the 'brain' for the tuning process. It decides what to test and yields high-level commands to the UI."""

    # --- CONFIGURATION ---
    MATH_ESTIMATION_SAFETY_MARGIN = 0.35
    SYSTEM_SAFETY_BUFFER_GB = 0.5

    def __init__(self, analysis_results, initial_params):
        self.analysis = analysis_results
        self.initial_params = initial_params
        self.best_config = {'params': {}, 'tps': 0.0}
        self.primary_gpu_id = 0  # Will be updated by user choice
        self.base_params = {}  # Will be built dynamically

    def _calculate_dynamic_timeout(self, test_type='benchmark'):
        """Calculates a dynamic timeout in milliseconds based on model size."""
        if test_type in ['metadata', 'probe']:
            return 60 * 1000

        model_size_gb = self.analysis.get('model_size_gb', 15.0)
        if not isinstance(model_size_gb, (int, float)) or model_size_gb <= 0:
            model_size_gb = 15.0

        if test_type == 'benchmark':
            base_ms = 60 * 1000
        else:
            base_ms = 45 * 1000

        per_gb_ms = 10 * 1000
        calculated_timeout = base_ms + (model_size_gb * per_gb_ms)
        min_timeout_ms = 60 * 1000
        max_timeout_ms = 20 * 60 * 1000
        return int(max(min_timeout_ms, min(calculated_timeout, max_timeout_ms)))

    # --- CORE REUSABLE LOGIC GENERATOR ---
    def _run_test_with_ts_balancing(self, params_to_test, timeout_ms, max_retries=50):
        """
        Runs a test cycle with built-in Tensor Split (-ts) balancing logic.
        Handles OOM, Resource Guard, and Saturation (Ping-Pong) detection with Midpoint Refinement.
        Returns dict: {success: bool, params: dict, reason: str, error_details: dict}
        """
        current_params = params_to_test.copy()
        last_failing_device = -1
        last_ts_vals = None  # Store previous split for midpoint calculation

        for attempt in range(max_retries):
            # 1. Update and Test
            yield {'action': 'update_params', 'params': {**self.base_params, **current_params}}
            result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout_ms}

            if result['success']:
                return {'success': True, 'params': current_params, 'reason': 'success', 'error_details': None}

            # 2. Analyze Failure
            error_details = result.get('error_details', {})

            if error_details.get('type') == 'resource_guard':
                return {'success': False, 'params': current_params, 'reason': 'resource_guard',
                        'error_details': error_details}

            failing_device = error_details.get('device_id', -1)
            if failing_device == -1 or '-ts' not in current_params:
                return {'success': False, 'params': current_params, 'reason': 'oom_unbalanceable',
                        'error_details': error_details}

            # 3. TS Balancing Logic
            try:
                ts_vals = [float(x) for x in current_params['-ts'].split(',')]
                if len(ts_vals) < 2:
                    return {'success': False, 'params': current_params, 'reason': 'oom_single_gpu_ts',
                            'error_details': error_details}

                primary_idx = self.primary_gpu_id
                sec_idx = next((i for i in range(len(ts_vals)) if i != primary_idx), -1)
                if sec_idx == -1:
                    return {'success': False, 'params': current_params, 'reason': 'oom_no_secondary',
                            'error_details': error_details}

                ts_step = 0.02
                min_split = 0.005
                adjusted = False

                # Check for Saturation (Ping-Pong)
                is_ping_pong = False
                if failing_device == primary_idx and last_failing_device != -1 and last_failing_device != primary_idx:
                    is_ping_pong = True
                elif failing_device != primary_idx and last_failing_device == primary_idx:
                    is_ping_pong = True

                if is_ping_pong:
                    if last_ts_vals:
                        yield {'action': 'log',
                               'message': "  > Saturation (Ping-Pong). Attempting Midpoint Refinement..."}
                        mid_ts = [(a + b) / 2.0 for a, b in zip(ts_vals, last_ts_vals)]
                        mid_ts_str = ",".join([f"{x:.3f}" for x in mid_ts])
                        current_params['-ts'] = mid_ts_str

                        # One-shot midpoint test
                        yield {'action': 'update_params', 'params': {**self.base_params, **current_params}}
                        mid_result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout_ms}

                        if mid_result['success']:
                            yield {'action': 'log', 'message': "  > Midpoint Refinement Successful!"}
                            return {'success': True, 'params': current_params, 'reason': 'success',
                                    'error_details': None}

                    return {'success': False, 'params': current_params, 'reason': 'saturation',
                            'error_details': error_details}

                # Save state before modification
                last_ts_vals = list(ts_vals)
                last_failing_device = failing_device

                # Apply Standard Adjustment
                if failing_device == primary_idx:
                    if ts_vals[primary_idx] > min_split:
                        diff = min(ts_step, ts_vals[primary_idx] - min_split)
                        ts_vals[primary_idx] -= diff
                        ts_vals[sec_idx] += diff
                        adjusted = True
                        yield {'action': 'log', 'message': f"  > Primary OOM. Shifting {diff:.3f} load to Secondary."}
                else:
                    if ts_vals[failing_device] > min_split:
                        diff = min(ts_step, ts_vals[failing_device] - min_split)
                        ts_vals[failing_device] -= diff
                        ts_vals[primary_idx] += diff
                        adjusted = True
                        yield {'action': 'log',
                               'message': f"  > Device {failing_device} OOM. Shifting {diff:.3f} load to Primary."}

                if adjusted:
                    current_params['-ts'] = ",".join([f"{x:.3f}" for x in ts_vals])
                    continue
                else:
                    return {'success': False, 'params': current_params, 'reason': 'ts_limit_reached',
                            'error_details': error_details}

            except ValueError:
                return {'success': False, 'params': current_params, 'reason': 'ts_parse_error',
                        'error_details': error_details}

        return {'success': False, 'params': current_params, 'reason': 'retries_exhausted', 'error_details': None}

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

        # Check for gpt-oss and VRAM fit
        model_path = self.initial_params.get('-m', self.initial_params.get('--model', '')).lower()
        if 'gpt-oss' in model_path:
            gpus = self.analysis.get('gpus', [])
            total_free_vram = sum(gpu.get('vram', {}).get('free_gb', 0) for gpu in gpus)
            model_size = self.analysis.get('model_size_gb', 0)
            if total_free_vram > (model_size + 1.5):
                for opt in proposed_optimizations:
                    if opt['id'] == 'kv_cache_q8':
                        opt['checked'] = False
                        yield {'action': 'log', 'message': "> GPT-OSS fits in VRAM: Unchecking 8-bit KV cache."}
                        break

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
        try:
            metadata_result = yield {'action': 'extract_layer_count', 'timeout_ms': metadata_timeout}
        except Exception as e:
            yield {'action': 'log', 'message': f"[CRITICAL ERROR] Exception during Phase 1 yield: {e}"}
            return

        if not metadata_result.get('success'):
            yield {'action': 'log', 'message': "[CRITICAL] Could not determine all model metadata. Halting."}
            return

        # Defensive assignment
        try:
            self.analysis['model_layers'] = metadata_result.get('layers', 0)
            self.analysis['model_max_context'] = metadata_result.get('max_context', 32768)
            self.analysis['proposed_optimizations'] = proposed_optimizations

            # Reorder GPU list (with error handling)
            ground_truth_gpus = metadata_result.get('gpus', [])
            yield from self._reorder_gpu_list(ground_truth_gpus)

        except Exception as e:
            yield {'action': 'log', 'message': f"[CRITICAL ERROR] Processing Phase 1 results failed: {e}"}
            return

        # --- PROBE LOGIC (Moved before UI) ---
        yield {'action': 'log', 'message': "\n[PHASE 2] Probing KV Cache Cost..."}
        probe_ngl = self._calculate_safe_probe_ngl()
        # Force f16 to get a clean baseline for the dynamic UI logic
        params_probe = {'-ngl': probe_ngl, '-c': '4096', '-ctk': 'f16', '-ctv': 'f16'}
        yield {'action': 'update_params', 'params': params_probe}
        timeout = self._calculate_dynamic_timeout('probe')
        yield {'action': 'probe_kv_stats', 'timeout_ms': timeout}

        kv_mb_per_token = self.analysis.get('kv_mb_per_token', 0.0)
        if kv_mb_per_token > 0:
            yield {'action': 'log',
                   'message': f"> Probe successful. Baseline (f16) KV Cost: {kv_mb_per_token:.4f} MB/token."}
        else:
            yield {'action': 'log', 'message': "> Probe failed to capture KV stats. Estimation will be less accurate."}

        # --- SHOW UI ---
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

        if 'gpt-oss' in model_path:
            self.base_params['--chat-template-kwargs'] = '{"reasoning_effort": "medium"}'

        # --- SAFETY CLAMPING & RESOLUTION (Internal Global Ceiling Check) ---
        user_target_context = user_choices.get('target_context', -1)
        model_max_ctx = int(self.analysis.get('model_max_context', 32768))

        # 1. Resolve "Auto / Max" setting (-1) to a concrete number
        if user_target_context == -1:
            user_target_context = model_max_ctx

        if kv_mb_per_token > 0:
            # Determine cost based on selected optimization
            is_q8 = self.base_params.get('-ctk') == 'q8_0'
            current_kv_cost = kv_mb_per_token * (0.55 if is_q8 else 1.0)

            # --- REVISED BUFFER LOGIC ---
            SAFETY_BUFFER_GB = 0.1
            is_draft = 'draft_offload' in user_choices.get('selected_optimizations', {}) or '-md' in self.initial_params
            if is_draft:
                SAFETY_BUFFER_GB += 0.5

            MODEL_SIZE_GB = self.analysis.get('model_size_gb', 0)
            strategy = user_choices.get('offload_strategy')

            # Re-calculate available memory based on the STRATEGY CHOSEN
            total_available_mem_gb = 0
            gpus = self.analysis.get('gpus', [])
            ram_free_gb = self.analysis.get('ram', {}).get('free_gb', 0)

            if strategy == 'single_gpu':
                for gpu in gpus:
                    if gpu['id'] == self.primary_gpu_id:
                        total_available_mem_gb = gpu.get('vram', {}).get('free_gb', 0)
                        break
            elif strategy == 'multi_vram':
                total_available_mem_gb = sum(g.get('vram', {}).get('free_gb', 0) for g in gpus)
            else:  # multi_cpu
                vram_free_gb = sum(g.get('vram', {}).get('free_gb', 0) for g in gpus)
                total_available_mem_gb = vram_free_gb + ram_free_gb

            required_mem_gb = MODEL_SIZE_GB + ((user_target_context * current_kv_cost) / 1024)

            # Check fit
            if MODEL_SIZE_GB > (total_available_mem_gb - SAFETY_BUFFER_GB):
                yield {'action': 'log',
                       'message': f"[WARNING] Model size ({MODEL_SIZE_GB} GB) exceeds available memory for strategy '{strategy}' ({total_available_mem_gb:.2f} GB)."}

            # Clamping logic removed by user request.
            # elif required_mem_gb > (total_available_mem_gb - SAFETY_BUFFER_GB): pass

        # 2. IMPORTANT: Update the dictionary so downstream strategies don't see -1
        user_choices['target_context'] = user_target_context

        yield {'action': 'log', 'message': "\n[PHASE 3] Finding Optimal Layer Offload..."}
        best_offload_params = None
        strategy = user_choices.get('offload_strategy')

        if strategy == 'single_gpu':
            best_offload_params = yield from self._tune_single_gpu()
        elif strategy == 'multi_vram':
            best_offload_params = yield from self._tune_multi_vram()
        elif strategy == 'multi_cpu':
            best_offload_params = yield from self._tune_multi_cpu(user_choices)

        if not best_offload_params:
            yield {'action': 'log',
                   'message': "[CRITICAL] Could not find a working offload configuration. Tuning aborted."}
            return

        yield {'action': 'log', 'message': f"> Optimal offload found: {best_offload_params}"}
        final_params = best_offload_params.copy()

        if user_choices.get('maximize_context'):
            # Check if Phase 3 already reached the target (Common for Dense models)
            current_c = int(final_params.get('-c', 0))
            user_target = user_choices.get('target_context', 0)

            if current_c >= user_target and user_target > 0:
                yield {'action': 'log',
                       'message': f"> Phase 3 already reached target context ({current_c}). Skipping Phase 4."}
                best_context_params = final_params
            else:
                yield {'action': 'log', 'message': "\n[PHASE 4] Maximizing Context Size (Adaptive Search)..."}
                best_context_params = yield from self._tune_context_size_adaptive(final_params, strategy, user_target)
                final_params = best_context_params
        yield {'action': 'log', 'message': "\n[PHASE 5] Final Performance Benchmark..."}

        benchmark_result = yield from self._run_final_benchmark(final_params)

        if not benchmark_result['success']:
            yield {'action': 'log', 'message': "[CRITICAL] Final configuration was unstable. Tuning aborted."}
            return

        yield {'action': 'log', 'message': "\n" + "=" * 27 + " Tuning Complete " + "=" * 28}
        yield {'action': 'log', 'message': f"Best Performance Found: {benchmark_result['tps']:.2f} t/s"}
        self.best_config = {'params': final_params, 'tps': benchmark_result['tps']}
        yield {'action': 'save_best_params'}

    # --- HELPER: CALCULATE SAFE PROBE NGL ---
    def _calculate_safe_probe_ngl(self):
        """Returns 1 to force CPU-heavy load for safe probing."""
        return '1'

    # --- STRATEGY HELPERS ---
    def _tune_single_gpu(self):
        yield {'action': 'log', 'message': "> Strategy: Single GPU Only"}
        params = {'-ngl': '99', '--split-mode': 'none', '-mg': str(self.primary_gpu_id)}
        timeout = self._calculate_dynamic_timeout('ngl_test')

        # Use helper for robustness (even if single GPU, it handles retries/logging)
        result = yield from self._run_test_with_ts_balancing(params, timeout)

        if result['success']:
            return result['params']

        yield {'action': 'log', 'message': "> Single GPU load failed."}
        user_decision = yield {'action': 'confirm_single_gpu_failure'}
        if user_decision == 'try_multi':
            return (yield from self._tune_multi_cpu())
        else:
            return None

    def _tune_multi_vram(self):
        yield {'action': 'log', 'message': "> Strategy: Multi-GPU (VRAM Only)"}
        ts_proportions = self._calculate_primary_first_tensor_split(
            self.analysis['gpus'], self.analysis['model_size_gb'], self.primary_gpu_id
        )
        if not ts_proportions:
            yield {'action': 'log', 'message': "[ERROR] Could not calculate tensor split. Aborting."}
            return None
        ts_string = ",".join([f"{p:.3f}" for p in ts_proportions])
        yield {'action': 'log', 'message': f'> Using "Primary-First" tensor split: {ts_string}'}

        params = {'-ngl': '99', '-ts': ts_string, '-ncmoe': 'REMOVE'}
        timeout = self._calculate_dynamic_timeout('ngl_test')

        result = yield from self._run_test_with_ts_balancing(params, timeout)

        if result['success']:
            return result['params']

        yield {'action': 'log', 'message': "> Full VRAM offload failed. Automatically transitioning to CPU offload."}
        return (yield from self._tune_multi_cpu())

    def _tune_multi_cpu(self, user_choices=None):
        yield {'action': 'log', 'message': "> Strategy: Multi-GPU with CPU Offload"}
        is_moe = self.analysis.get('model_architecture') == 'Mixture of Experts (MoE)'
        if is_moe:
            return (yield from self._tune_moe_multi_cpu(user_choices))
        else:
            return (yield from self._tune_dense_multi_cpu(user_choices))

    def _tune_context_size_adaptive(self, base_offload_params, strategy, target_limit):
        yield {'action': 'log',
               'message': f"> Starting Bottom-Up Context Search (Doubling Strategy). Target: {target_limit}"}

        # 1. Establish Baseline (Skip re-testing 4096)
        current_ctx = 4096
        best_known_params = base_offload_params.copy()
        best_known_params['-c'] = str(current_ctx)
        timeout = self._calculate_dynamic_timeout('ngl_test')
        strategy_allows_cpu = strategy == 'multi_cpu'

        # 2. Doubling Loop
        while current_ctx < target_limit:
            next_ctx = current_ctx * 2
            if next_ctx > target_limit: next_ctx = target_limit
            if (next_ctx - current_ctx) < 1024 and next_ctx != target_limit: next_ctx = target_limit

            yield {'action': 'log', 'message': f"> Testing context size: {next_ctx}"}
            temp_params = best_known_params.copy()
            temp_params['-c'] = str(next_ctx)

            # --- Predictive Adjustment ---
            if strategy_allows_cpu:
                kv_mb = self.analysis.get('kv_mb_per_token', 0.0)
                is_q8 = temp_params.get('-ctk') == 'q8_0'
                effective_kv_cost = kv_mb * (0.55 if is_q8 else 1.0)

                if effective_kv_cost > 0:
                    added_tokens = next_ctx - current_ctx
                    added_vram_cost_mib = added_tokens * effective_kv_cost
                    model_size_gb = self.analysis.get('model_size_gb', 0)
                    total_layers = self.analysis.get('model_layers', 1)
                    avg_layer_mib = (model_size_gb * 1024) / total_layers if total_layers > 0 else 0

                    if avg_layer_mib > 0:
                        layers_to_evict = math.ceil(added_vram_cost_mib / avg_layer_mib)
                        if layers_to_evict > 0:
                            if '-ncmoe' in temp_params:
                                new_ncmoe = int(temp_params['-ncmoe']) + layers_to_evict
                                temp_params['-ncmoe'] = str(new_ncmoe)
                                yield {'action': 'log',
                                       'message': f"  > Prediction: Increasing -ncmoe to {new_ncmoe} to fit context."}
                            elif '-ngl' in temp_params:
                                predicted_ngl = max(0, int(temp_params['-ngl']) - layers_to_evict)
                                temp_params['-ngl'] = str(predicted_ngl)
                                yield {'action': 'log',
                                       'message': f"  > Prediction: Reducing -ngl to {predicted_ngl} to fit context."}

            # Test this level using Helper (Up to 20 retries for TS balancing)
            # Use a slightly complex loop to handle CPU offload layer dropping *if* TS fails
            level_success = False
            for attempt in range(20):
                result = yield from self._run_test_with_ts_balancing(temp_params, timeout, max_retries=50)

                # PERSISTENCE FIX: Keep the best TS found even if this attempt failed (for next layer drop)
                if result.get('params') and '-ts' in result['params']:
                    temp_params['-ts'] = result['params']['-ts']

                if result['success']:
                    level_success = True
                    temp_params = result['params']  # Update with balanced TS
                    break

                # Handle Failure Logic
                if result['reason'] == 'resource_guard':
                    yield {'action': 'log', 'message': "  > RAM Limit Reached."}
                    break  # Stop expanding

                # If TS balancing failed but we can offload to CPU, drop layers and retry
                if strategy_allows_cpu and result['reason'] in ['saturation', 'retries_exhausted', 'ts_limit_reached']:
                    yield {'action': 'log', 'message': "  > VRAM Saturated. Moving layers to RAM..."}
                    if '-ncmoe' in temp_params:
                        temp_params['-ncmoe'] = str(int(temp_params['-ncmoe']) + 1)
                    elif '-ngl' in temp_params:
                        temp_params['-ngl'] = str(max(0, int(temp_params['-ngl']) - 1))
                    else:
                        break  # Cannot adjust
                else:
                    break  # Cannot adjust

            if level_success:
                best_known_params = temp_params.copy()
                current_ctx = next_ctx
                yield {'action': 'log', 'message': "  > Success. Saving configuration."}
                if current_ctx == target_limit: break
            else:
                yield {'action': 'log', 'message': "  > Doubling failed. Switching to Binary Search Refinement."}

                # --- Binary Search Refinement ---
                low_ctx, high_ctx = current_ctx, next_ctx
                while (high_ctx - low_ctx) >= 1024:
                    mid_ctx = (low_ctx + high_ctx) // 2
                    mid_ctx = (mid_ctx // 512) * 512
                    if mid_ctx <= low_ctx: break

                    yield {'action': 'log', 'message': f"> Refinement: Testing context {mid_ctx}..."}
                    temp_params = best_known_params.copy()
                    temp_params['-c'] = str(mid_ctx)

                    # Use helper for the binary check
                    result = yield from self._run_test_with_ts_balancing(temp_params, timeout, max_retries=50)

                    if result['success']:
                        yield {'action': 'log', 'message': "  > Success. Searching higher..."}
                        best_known_params = result['params'].copy()
                        low_ctx = mid_ctx
                    else:
                        yield {'action': 'log', 'message': "  > Failed. Searching lower..."}
                        high_ctx = mid_ctx
                break

        # --- PHASE 4.5: VRAM Back-Fill (MoE Only) ---
        if strategy_allows_cpu and '-ncmoe' in best_known_params and int(best_known_params.get('-ncmoe', 0)) > 0:
            yield {'action': 'log', 'message': "\\n[PHASE 4.5] Optimizing VRAM usage (Back-Fill)..."}
            while int(best_known_params['-ncmoe']) > 0:
                target_ncmoe = int(best_known_params['-ncmoe']) - 1
                yield {'action': 'log',
                       'message': f"> Attempting to reduce -ncmoe to {target_ncmoe} to use free VRAM..."}

                temp_params = best_known_params.copy()
                temp_params['-ncmoe'] = str(target_ncmoe)

                result = yield from self._run_test_with_ts_balancing(temp_params, timeout, max_retries=50)

                if result['success']:
                    best_known_params = result['params'].copy()
                    yield {'action': 'log', 'message': "  > Success. Keeping optimized configuration."}
                else:
                    yield {'action': 'log', 'message': "  > VRAM saturated. Finalizing configuration."}
                    break

        return best_known_params

    def _tune_dense_multi_cpu(self, user_choices=None):
        total_layers = self.analysis['model_layers'] + 1
        ts_proportions = self._calculate_primary_first_tensor_split(
            self.analysis['gpus'], self.analysis['model_size_gb'], self.primary_gpu_id
        )
        if not ts_proportions: return None
        initial_ts_string = ",".join([f"{p:.3f}" for p in ts_proportions])
        yield {'action': 'log', 'message': f'> Using "Primary-First" tensor split: {initial_ts_string}'}

        base_kv_cost = self.analysis.get('kv_mb_per_token', 0.0)
        is_q8 = self.base_params.get('-ctk') == 'q8_0'
        kv_mb_per_token = base_kv_cost * (0.55 if is_q8 else 1.0)
        timeout = self._calculate_dynamic_timeout('ngl_test')

        # Track definitively failed configurations to avoid redundancy during climbs
        hard_failed_ngls = set()

        if kv_mb_per_token > 0 and user_choices and user_choices.get('maximize_context'):
            target_context = user_choices.get('target_context', 4096)
            if target_context > 4096:
                yield {'action': 'log', 'message': "> Maximize Context enabled: Predicting optimal NGL."}

                # Predictive logic
                gpus = self.analysis.get('gpus', [])
                total_vram_mib = sum(g.get('vram', {}).get('free_gb', 0) for g in gpus) * 1024
                overhead_mib = 1024
                model_size_gb = self.analysis.get('model_size_gb', 0)

                if model_size_gb > 0:
                    avg_layer_size_mib = (model_size_gb * 1024) / total_layers
                    predicted_ctx_cost_mib = target_context * kv_mb_per_token
                    vram_for_weights = total_vram_mib - overhead_mib - predicted_ctx_cost_mib

                    if vram_for_weights > 0:
                        predicted_ngl = int(vram_for_weights / avg_layer_size_mib)
                        predicted_ngl = max(0, min(predicted_ngl, total_layers) - 2)

                        yield {'action': 'log', 'message': f"> Prediction: Estimated Safe NGL: {predicted_ngl}."}
                        params_for_test = {**self.base_params, '-ts': initial_ts_string, '-ngl': str(predicted_ngl),
                                           '-c': str(target_context)}

                        result = yield from self._run_test_with_ts_balancing(params_for_test, timeout)

                        if result['success']:
                            yield {'action': 'log', 'message': "> Prediction successful! Entering Greedy Fill."}
                            # --- Greedy Fill (No complex TS balancing needed per step, just check success) ---
                            current_ngl = predicted_ngl
                            best_greedy_params = result['params'].copy()

                            while current_ngl < total_layers:
                                next_ngl = min(total_layers, current_ngl + 2)
                                if next_ngl == current_ngl: break

                                params_for_test['-ngl'] = str(next_ngl)
                                yield {'action': 'log', 'message': f"  > Greedy Step: Testing -ngl {next_ngl}"}

                                # Use helper but with low retries as we want speed
                                fill_result = yield from self._run_test_with_ts_balancing(params_for_test, timeout,
                                                                                          max_retries=5)
                                if fill_result['success']:
                                    current_ngl = next_ngl
                                    best_greedy_params = fill_result['params'].copy()
                                    params_for_test = best_greedy_params  # Carry over TS
                                else:
                                    # Record failure
                                    if fill_result['reason'] in ['saturation', 'resource_guard', 'ts_limit_reached']:
                                        hard_failed_ngls.add(next_ngl)

                                    # Refine +1
                                    if next_ngl == current_ngl + 2:
                                        refine_ngl = current_ngl + 1
                                        if refine_ngl < total_layers and refine_ngl not in hard_failed_ngls:
                                            params_for_test['-ngl'] = str(refine_ngl)
                                            yield {'action': 'log',
                                                   'message': f"  > Greedy Refinement: Testing -ngl {refine_ngl}"}
                                            refine_result = yield from self._run_test_with_ts_balancing(params_for_test,
                                                                                                        timeout,
                                                                                                        max_retries=5)
                                            if refine_result['success']:
                                                best_greedy_params = refine_result['params'].copy()
                                            elif refine_result['reason'] in ['saturation', 'resource_guard',
                                                                             'ts_limit_reached']:
                                                hard_failed_ngls.add(refine_ngl)

                                    yield {'action': 'log', 'message': "> Greedy fill hit limit."}
                                    break
                            return best_greedy_params

                        else:
                            # Attempt TS balancing via helper failed or prediction failed
                            yield {'action': 'log',
                                   'message': "> Prediction failed or OOM. Falling back to Layer Drop."}
                            # Logic: Reduce layers, retry using helper to balance TS
                            current_ngl = predicted_ngl
                            current_ts = result['params'].get('-ts', initial_ts_string)  # Use last best TS guess

                            # Record initial failure if hard
                            if result['reason'] in ['saturation', 'resource_guard', 'ts_limit_reached']:
                                hard_failed_ngls.add(current_ngl)

                            for retry in range(20):
                                error_details = result.get('error_details', {})
                                oom_size_mib = error_details.get('size_mib', 0)
                                layers_to_drop = max(1, math.ceil(
                                    oom_size_mib / avg_layer_size_mib) if oom_size_mib > 0 else 1)

                                current_ngl = max(0, current_ngl - layers_to_drop)
                                yield {'action': 'log', 'message': f"  > Retry {retry + 1}: Testing -ngl {current_ngl}"}

                                params_for_test['-ngl'] = str(current_ngl)
                                params_for_test['-ts'] = current_ts  # Keep evolving TS

                                result = yield from self._run_test_with_ts_balancing(params_for_test, timeout)
                                if result['success']:
                                    yield {'action': 'log',
                                           'message': "> Retry successful. Checking if we can squeeze any layers back..."}

                                    # --- RECOVERY CLIMB LOGIC START ---
                                    best_recovered_params = result['params'].copy()
                                    recovery_params = best_recovered_params.copy()

                                    while current_ngl < total_layers:
                                        next_ngl = current_ngl + 1

                                        # Optimization: Skip known failures
                                        if next_ngl in hard_failed_ngls:
                                            yield {'action': 'log',
                                                   'message': f"  > Skipping -ngl {next_ngl} (previously confirmed unstable)."}
                                            break

                                        recovery_params['-ngl'] = str(next_ngl)
                                        yield {'action': 'log', 'message': f"  > Recovery Climb: Testing -ngl {next_ngl}"}

                                        # Low retries for climbing
                                        climb_result = yield from self._run_test_with_ts_balancing(recovery_params,
                                                                                                   timeout,
                                                                                                   max_retries=5)

                                        if climb_result['success']:
                                            current_ngl = next_ngl
                                            best_recovered_params = climb_result['params'].copy()
                                            recovery_params = best_recovered_params  # Keep optimized TS
                                        else:
                                            yield {'action': 'log',
                                                   'message': "> Climb hit limit. Returning best recovered config."}
                                            break
                                    # --- RECOVERY CLIMB LOGIC END ---

                                    return best_recovered_params

                                # Failure in retry loop: Record it
                                current_ts = result['params'].get('-ts', current_ts)
                                if result['reason'] in ['saturation', 'resource_guard', 'ts_limit_reached']:
                                    hard_failed_ngls.add(current_ngl)

        # Fallback to Binary Search
        yield {'action': 'log', 'message': "> Finding a safe baseline NGL via binary search..."}
        low, high, best_known_ngl = 0, total_layers, 0
        while low <= high:
            mid = (low + high) // 2
            if mid == 0: low = 1; continue

            params_for_test = {**self.base_params, '-ts': initial_ts_string, '-ngl': str(mid)}
            if '-c' in params_for_test: del params_for_test['-c']

            yield {'action': 'log', 'message': f"> Binary Search: Testing -ngl {mid}"}
            result = yield from self._run_test_with_ts_balancing(params_for_test, timeout)

            if result['success']:
                best_known_ngl = mid
                initial_ts_string = result['params']['-ts']  # Carry forward optimized split
                low = mid + 1
            else:
                high = mid - 1

        if best_known_ngl == 0:
            yield {'action': 'log', 'message': "[CRITICAL] Could not find any viable NGL value."}
            return None

        return {'-ngl': str(best_known_ngl), '-ts': initial_ts_string}

    def _tune_moe_multi_cpu(self, user_choices=None):
        yield {'action': 'log', 'message': "\n[PHASE 3] Activating MoE multi-GPU tuning strategy (with CPU offload)."}
        total_layers = self.analysis.get('model_layers', 0) + 1
        ctx_param = {'-c': '4096'}
        if user_choices and user_choices.get('maximize_context'):
            yield {'action': 'log', 'message': "> Maximize Context enabled: Tuning offload at baseline (4096) first."}

        # Stage 1: Coarse search
        yield {'action': 'update_params', 'params': {**self.base_params, '-ngl': '99', '-ts': 'REMOVE', **ctx_param}}
        crossover_ncmoe = -1
        timeout = self._calculate_dynamic_timeout('ngl_test')

        for ncmoe_to_test in list(range(0, total_layers, 5)) + [total_layers - 1]:
            yield {'action': 'log', 'message': f"> Coarse Test: -ncmoe {ncmoe_to_test}"}
            yield {'action': 'update_params', 'params': {'-ncmoe': str(ncmoe_to_test)}}

            result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout}
            if result['success']:
                crossover_ncmoe = ncmoe_to_test
                yield {'action': 'log', 'message': f"  > SUCCESS."}
                break

            # Simple resource guard check logic (keep local as it involves context reduction logic specific to MoE)
            error_details = result.get('error_details', {})
            if error_details and error_details.get('type') == 'resource_guard':
                new_ctx = max(512, int(ctx_param.get('-c', 4096)) - 2048)
                ctx_param['-c'] = str(new_ctx)
                yield {'action': 'log', 'message': f"  > FAILURE: RAM. Reducing context to {new_ctx} and retrying."}
                yield {'action': 'update_params',
                       'params': {**self.base_params, '-ngl': '99', '-ts': 'REMOVE', **ctx_param,
                                  '-ncmoe': str(ncmoe_to_test)}}
                result = yield {'action': 'test_ngl_value', 'timeout_ms': timeout}
                if result['success']:
                    crossover_ncmoe = ncmoe_to_test
                    yield {'action': 'log', 'message': f"  > SUCCESS (Reduced Context)."}
                    break

            if error_details and error_details.get('device_id') != self.primary_gpu_id:
                crossover_ncmoe = ncmoe_to_test
                yield {'action': 'log',
                       'message': f"  > Crossover found. GPU {error_details['device_id']} is bottleneck."}
                break

        if crossover_ncmoe == -1: return None

        # Stage 2: Fine-tuning using Helper
        yield {'action': 'log', 'message': "\n> Stage 2: Fine-tuning -ncmoe and -ts..."}
        current_ncmoe = max(0, crossover_ncmoe - 5)
        ts_proportions = self._calculate_primary_first_tensor_split(self.analysis['gpus'],
                                                                    self.analysis['model_size_gb'], self.primary_gpu_id)
        current_ts_string = ",".join([f"{p:.3f}" for p in ts_proportions]) if ts_proportions else ""

        # Using a specialized loop here because we increment -ncmoe on failure rather than just stopping
        max_attempts = 200
        for attempt in range(max_attempts):
            yield {'action': 'log', 'message': f"\n> Attempt {attempt + 1}: Testing -ncmoe {current_ncmoe}"}
            params_to_test = {'-ngl': '99', '-ncmoe': str(current_ncmoe), '-ts': current_ts_string, **ctx_param}

            # Use Helper for Robust TS Balancing on *this specific ncmoe*
            result = yield from self._run_test_with_ts_balancing(params_to_test, timeout)

            # OPTIMIZATION: Persist the tuned TS value for the next iteration so we don't reset to default
            if result.get('params') and '-ts' in result['params']:
                current_ts_string = result['params']['-ts']

            if result['success']:
                yield {'action': 'log', 'message': f"  > SUCCESS! Optimal configuration found."}
                return result['params']

            # Logic if Helper fails even after TS balancing
            if result['reason'] == 'resource_guard':
                # RAM Limit -> Reduce Context, Retry same ncmoe
                new_ctx = max(512, int(ctx_param.get('-c', 4096)) - 2048)
                ctx_param['-c'] = str(new_ctx)
                yield {'action': 'log', 'message': f"  > RAM Saturated. Reducing context to {new_ctx}."}
                if current_ncmoe > 0: current_ncmoe -= 1  # Retreat to GPU to re-evaluate
                continue

            # If we OOMed on GPU (saturation/limit), increment ncmoe (move to CPU)
            yield {'action': 'log', 'message': "  > VRAM Limit/Saturation. Incrementing -ncmoe."}
            current_ncmoe += 1
            if current_ncmoe >= total_layers: break

        return None

    # --- RESTORED UTILITY METHODS ---
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
            if not name: return ""
            return re.sub(r'[^a-zA-Z0-9]', '', name.lower().replace("nvidia", "").replace("geforce", ""))

        original_gpus = self.analysis.get('gpus', []);
        reordered_gpus = [];
        unmatched_gpus = list(original_gpus)

        if not original_gpus: return

        original_map = {clean_name(gpu.get('name', '')): gpu for gpu in original_gpus}

        for truth_gpu in sorted(ground_truth_gpus, key=lambda x: x['id']):
            truth_name_clean = clean_name(truth_gpu.get('name', ''))
            if truth_name_clean in original_map:
                matched_gpu = original_map[truth_name_clean];
                matched_gpu['id'] = truth_gpu['id']
                reordered_gpus.append(matched_gpu)
                unmatched_gpus = [g for g in unmatched_gpus if clean_name(g.get('name', '')) != truth_name_clean]
            else:
                yield {'action': 'log',
                       'message': f"[WARNING] Could not match ground truth GPU: {truth_gpu.get('name', 'unknown')}"}

        if unmatched_gpus: reordered_gpus.extend(unmatched_gpus)

        if len(reordered_gpus) == len(original_gpus):
            self.analysis['gpus'] = reordered_gpus
            log_msg = "> Successfully re-ordered GPU list to match llama.cpp:\n";
            for gpu in self.analysis['gpus']:
                log_msg += f"  - Device {gpu['id']}: {gpu.get('name', 'Unknown')}\n"
            yield {'action': 'log', 'message': log_msg.strip()}
        else:
            yield {'action': 'log', 'message': "[ERROR] GPU list re-ordering failed. Tensor split may be incorrect."}

    def _calculate_primary_first_tensor_split(self, gpus, model_size_gb, primary_gpu_id):
        if not gpus or len(gpus) < 2 or not isinstance(model_size_gb, (int, float)) or model_size_gb <= 0:
            return None

        VRAM_SAFETY_BUFFER_GB = 1.0

        try:
            primary_gpu = next(gpu for gpu in gpus if gpu['id'] == primary_gpu_id)
        except StopIteration:
            primary_gpu = gpus[0]

        secondary_gpus = [gpu for gpu in gpus if gpu['id'] != primary_gpu['id']]
        allocations_gb = {gpu['id']: 0.0 for gpu in gpus}

        primary_usable_vram = max(0, primary_gpu.get('vram', {}).get('free_gb', 0) - VRAM_SAFETY_BUFFER_GB)
        primary_allocation = min(model_size_gb, primary_usable_vram)
        allocations_gb[primary_gpu['id']] = primary_allocation

        remaining_model_gb = model_size_gb - primary_allocation

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

        final_proportions = {gpu_id: alloc_gb / model_size_gb for gpu_id, alloc_gb in allocations_gb.items()}
        total_proportion = sum(final_proportions.values())
        if total_proportion > 0:
            final_proportions = {gpu_id: p / total_proportion for gpu_id, p in final_proportions.items()}
        else:
            return [1.0 / len(gpus)] * len(gpus)

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