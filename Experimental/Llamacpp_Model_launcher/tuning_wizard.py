# tuning_wizard.py

import time
import requests
import re
from Llamacpp_Model_launcher.parameters_db import BENCHMARK_PROMPT  # Import the centralized prompt


class TuningWizard:
    """
    Acts as the 'brain' for the tuning process. It decides what to test and yields
    high-level commands to the UI, which is responsible for execution.
    """

    def __init__(self, analysis_results, initial_params):
        self.analysis = analysis_results
        self.initial_params = initial_params
        self.best_config = {'params': {}, 'tps': 0.0}

    def _reorder_gpu_list(self, ground_truth_gpus):
        """
        Reorders the self.analysis['gpus'] list to match the device order
        reported by llama.cpp itself. This is CRITICAL for correct tensor split.
        """
        yield {'action': 'log', 'message': "> Reconciling GPU device order..."}
        if not ground_truth_gpus or not self.analysis.get('gpus') or len(self.analysis.get('gpus', [])) < 2:
            yield {'action': 'log', 'message': "> Single GPU or no ground truth data. Skipping re-ordering."}
            return

        def clean_name(name):
            return re.sub(r'[^a-zA-Z0-9]', '', name.lower().replace("nvidia", "").replace("geforce", ""))

        original_gpus = self.analysis.get('gpus', [])
        reordered_gpus = []
        unmatched_gpus = list(original_gpus)
        original_map = {clean_name(gpu['name']): gpu for gpu in original_gpus}

        for truth_gpu in sorted(ground_truth_gpus, key=lambda x: x['id']):
            truth_name_clean = clean_name(truth_gpu['name'])
            if truth_name_clean in original_map:
                matched_gpu = original_map[truth_name_clean]
                matched_gpu['id'] = truth_gpu['id']
                reordered_gpus.append(matched_gpu)
                unmatched_gpus = [g for g in unmatched_gpus if clean_name(g['name']) != truth_name_clean]
            else:
                yield {'action': 'log', 'message': f"[WARNING] Could not match ground truth GPU: {truth_gpu['name']}"}

        if unmatched_gpus:
            reordered_gpus.extend(unmatched_gpus)

        if len(reordered_gpus) == len(original_gpus):
            self.analysis['gpus'] = reordered_gpus
            log_msg = "> Successfully re-ordered GPU list to match llama.cpp:\n"
            for gpu in self.analysis['gpus']:
                log_msg += f"  - Device {gpu['id']}: {gpu['name']}\n"
            yield {'action': 'log', 'message': log_msg.strip()}
        else:
            yield {'action': 'log', 'message': "[ERROR] GPU list re-ordering failed. Tensor split may be incorrect."}

    def _calculate_tensor_split_proportions(self, gpus):
        """Calculates tensor split proportions based on total VRAM."""
        if not gpus or len(gpus) < 2:
            return None
        total_vram = sum(gpu['vram'].get('total_gb', 0) for gpu in gpus)
        if total_vram == 0:
            return None
        return [(gpu['vram'].get('total_gb', 0) / total_vram) for gpu in gpus]

    def run_api_benchmark_requests(self):
        """Sends 3 requests to the CHAT endpoint to trigger text generation."""
        for i in range(3):
            try:
                prompt = BENCHMARK_PROMPT
                payload = {
                    "messages": [{"role": "user", "content": prompt}],
                    "n_predict": 512,
                    "temperature": 0.1,
                    "seed": 1
                }
                requests.post("http://127.0.0.1:8080/v1/chat/completions", json=payload, timeout=120)
                if i < 2: time.sleep(2)
            except requests.RequestException as e:
                print(f"[DIAGNOSTICS] API request {i + 1} failed: {e}")
                pass

    def run_stability_api_request(self):
        """Sends a single, small request to the CHAT endpoint for stability."""
        try:
            prompt = BENCHMARK_PROMPT
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "n_predict": 10,
                "temperature": 0.1,
                "seed": 1
            }
            requests.post("http://127.0.0.1:8080/v1/chat/completions", json=payload, timeout=60)
        except requests.RequestException as e:
            print(f"[DIAGNOSTICS] Stability API request failed: {e}")
            pass

    def run_tuning_wizard(self):
        """The main generator that yields actions for the UI to perform."""
        yield {'action': 'log', 'message': "\n" + "=" * 25 + " Starting Tuning Wizard " + "=" * 25}

        has_draft_model = '-md' in self.initial_params or '--model-draft' in self.initial_params
        is_memory_constrained = False

        yield {'action': 'log', 'message': "\n[PHASE 1] Initial Checks & Metadata Extraction..."}
        baseline_flags = {'--no-warmup': None, '--no-mmap': None}
        yield {'action': 'update_params', 'params': baseline_flags}
        yield {'action': 'log', 'message': '> Applied --no-warmup and --no-mmap for consistent benchmarking.'}

        model_size = self.analysis.get('model_size_gb', 0.0)
        gpus = self.analysis.get('gpus', [])
        total_free_vram = sum(gpu.get('vram', {}).get('free_gb', 0) for gpu in gpus)
        total_free_ram = self.analysis.get('ram', {}).get('free_gb', 0.0)
        total_available_memory = total_free_vram + total_free_ram - 0.5

        if model_size > total_available_memory:
            is_memory_constrained = True
            proceed = yield {'action': 'confirm_warning', 'title': "Potential Memory Issue",
                             'message': "The model appears too large for your currently available RAM and VRAM.\n\n"
                                        "Proceeding may cause a crash. Continue anyway?"}
            if not proceed: yield {'action': 'log', 'message': "[INFO] Tuning aborted by user."}; return

        yield {'action': 'log', 'message': "> Attempting a sacrificial load to extract metadata."}
        yield {'action': 'update_params', 'params': {'-ngl': '1', '-ncmoe': 'REMOVE', '-ts': 'REMOVE', '-mg': 'REMOVE'}}
        metadata_result = yield {'action': 'extract_layer_count'}

        if not metadata_result['success']:
            yield {'action': 'log', 'message': f"[CRITICAL] Could not determine layer count. Halting."}
            return

        total_layers = metadata_result['layers'] + 1
        yield {'action': 'log',
               'message': f"> Successfully discovered {metadata_result['layers']} transformer layers (+1 output layer = {total_layers} total offloadable)."}

        yield from self._reorder_gpu_list(metadata_result.get('gpus', []))

        fa_params = {'--flash-attn': 'on', '-ctk': 'q8_0', '-ctv': 'q8_0'}
        if has_draft_model: fa_params.update({'--cache-type-k-draft': 'q8_0', '--cache-type-v-draft': 'q8_0'})
        yield {'action': 'update_params', 'params': fa_params}

        is_moe = self.analysis.get('model_architecture') == 'Mixture of Experts (MoE)'
        is_dense_model = not is_moe
        is_multi_gpu = len(self.analysis.get('gpus', [])) > 1

        best_gpu_id = 0
        if is_multi_gpu:
            try:
                best_gpu = max(self.analysis['gpus'], key=lambda gpu: gpu.get('vram', {}).get('total_gb', 0))
                best_gpu_id = best_gpu['id']
                yield {'action': 'log',
                       'message': f"> Found best GPU (most VRAM) is Device {best_gpu_id}: {best_gpu['name']}."}

                yield {'action': 'update_params', 'params': {'--main-gpu': str(best_gpu_id)}}
                yield {'action': 'log',
                       'message': f"> Setting --main-gpu {best_gpu_id} to ensure it handles primary tasks."}

            except (ValueError, KeyError):
                yield {'action': 'log',
                       'message': "[WARNING] Could not determine the best GPU. Defaulting to device 0."}

        if is_moe:
            model_path = self.initial_params.get('-m', self.initial_params.get('--model', ''))
            if 'gpt-oss' in model_path.lower():
                yield {'action': 'log', 'message': "> Applying gpt-oss specific reasoning parameter."}
                yield {'action': 'update_params',
                       'params': {'--chat-template-kwargs': '{"reasoning_effort": "medium"}'}}

        if is_multi_gpu and is_dense_model and has_draft_model:
            yield {'action': 'log',
                   'message': f"> Multi-GPU dense model with draft detected. Pinning draft model to fastest GPU (Device {best_gpu_id})."}
            yield {'action': 'update_params', 'params': {'--device-draft': f'CUDA{best_gpu_id}'}}

        best_config_params = None
        perform_multi_gpu_tuning = True
        if len(self.analysis.get('gpus', [])) > 0:
            yield {'action': 'log', 'message': "\n[PHASE 2] Attempting to fit entire model on primary GPU..."}

            single_gpu_params = {'-ngl': '99', '-mg': str(best_gpu_id), '-ts': 'REMOVE'}
            if is_moe: single_gpu_params['-ncmoe'] = '0'

            if len(self.analysis.get('gpus', [])) > 1:
                single_gpu_params['--split-mode'] = 'none'

            yield {'action': 'update_params', 'params': single_gpu_params}

            single_gpu_result = yield {'action': 'test_ngl_value'}

            if single_gpu_result['success']:
                yield {'action': 'log',
                       'message': "> SUCCESS! Entire model fits on the primary GPU. This is the optimal configuration."}
                best_config_params = {'-ngl': '99', '-mg': str(best_gpu_id)}
                if is_moe: best_config_params['-ncmoe'] = '0' # Ensure it's explicitly set for MoE
                if len(self.analysis.get('gpus', [])) > 1:
                    yield {'action': 'log',
                           'message': "> Multiple GPUs detected. Forcing single-GPU mode with '--split-mode none'."}
                    best_config_params['--split-mode'] = 'none'
                perform_multi_gpu_tuning = False
            else:
                yield {'action': 'log', 'message': "> FAILED: Model is too large for the primary GPU."}
                if len(self.analysis.get('gpus', [])) > 1:
                    context_size = self.initial_params.get('-c', self.initial_params.get('--ctx-size', 'N/A'))
                    proceed_with_multi_gpu = yield {
                        'action': 'confirm_context_tradeoff',
                        'title': 'Context Size vs. Multi-GPU',
                        'message': f"The model failed to load on your primary GPU with a context of {context_size}. "
                                   "This is likely because the context size requires more VRAM than the GPU has available.\n\n"
                                   "How would you like to proceed?"
                    }
                    if proceed_with_multi_gpu:
                        yield {'action': 'log', 'message': "> User chose to proceed with multi-GPU tuning."}
                        perform_multi_gpu_tuning = True
                        yield {'action': 'update_params',
                               'params': {'-mg': str(best_gpu_id), '-ngl': 'REMOVE', '--split-mode': 'REMOVE'}}
                    else:
                        yield {'action': 'log',
                               'message': "[INFO] Please lower the context size ('-c') in the Parameter Editor and run the wizard again."}
                        return
                else:
                    yield {'action': 'log',
                           'message': "[CRITICAL] Model will not fit on the single available GPU. Tuning cannot proceed."}
                    return

        if perform_multi_gpu_tuning:
            if is_moe and is_multi_gpu:
                vram_buffer_gb = 1.5
                yield {'action': 'log', 'message': "\n[PHASE 3] Checking for full VRAM offload viability..."}
                yield {'action': 'log',
                       'message': f"> Model Size: {model_size:.2f} GB | Total Free VRAM: {total_free_vram:.2f} GB"}

                if model_size < (total_free_vram - vram_buffer_gb):
                    yield {'action': 'log',
                           'message': "> Model may fit in combined VRAM. Attempting full GPU offload as a first step."}

                    ts_proportions = self._calculate_tensor_split_proportions(self.analysis['gpus'])
                    if ts_proportions:
                        ts_string = ",".join([f"{p:.2f}" for p in ts_proportions])
                        params_to_test = {'-ngl': '99', '-ts': ts_string, '-ncmoe': 'REMOVE'}

                        yield {'action': 'update_params', 'params': params_to_test}
                        result = yield {'action': 'test_ngl_value'}

                        if result['success']:
                            yield {'action': 'log',
                                   'message': "> SUCCESS! Full VRAM offload is stable. This is the optimal configuration."}
                            # --- MODIFIED: Explicitly define the successful configuration ---
                            # This ensures -ncmoe is removed, even if it was in the initial user config.
                            best_config_params = {'-ngl': '99', '-ts': ts_string, '-ncmoe': 'REMOVE'}
                        else:
                            yield {'action': 'log',
                                   'message': "> Full VRAM offload failed. Proceeding with CPU expert offload strategy."}
                    else:
                        yield {'action': 'log',
                               'message': "> Could not calculate tensor split. Skipping full VRAM offload test."}
                else:
                    yield {'action': 'log',
                           'message': "> Model is too large for combined VRAM. Proceeding with CPU expert offload strategy."}

            if best_config_params is None:
                if is_moe:
                    yield {'action': 'log',
                           'message': "\n[PHASE 3] Activating MoE multi-GPU tuning strategy (with CPU offload)."}
                    yield {'action': 'update_params', 'params': {'-ngl': '99'}}

                    crossover_ncmoe = -1
                    for ncmoe_to_test in list(range(0, total_layers, 5)) + [total_layers - 1]:
                        yield {'action': 'log', 'message': f"> Coarse Test: -ncmoe {ncmoe_to_test}"}
                        yield {'action': 'update_params', 'params': {'-ncmoe': str(ncmoe_to_test), '-ts': 'REMOVE'}}
                        result = yield {'action': 'test_ngl_value'}
                        if result['success']:
                            crossover_ncmoe = ncmoe_to_test
                            yield {'action': 'log',
                                   'message': f"  > SUCCESS: Model loaded with default tensor split."}
                            break
                        if result['error_details'] and result['error_details']['device_id'] != best_gpu_id:
                            crossover_ncmoe = ncmoe_to_test
                            yield {'action': 'log',
                                   'message': f"  > Crossover found. GPU {result['error_details']['device_id']} is now the bottleneck."}
                            break
                        else:
                            yield {'action': 'log',
                                   'message': f"  > FAILED: GPU {best_gpu_id} remains the bottleneck."}

                    if crossover_ncmoe == -1:
                        yield {'action': 'log',
                               'message': f"[CRITICAL] Could not relieve GPU {best_gpu_id}. Halting."}
                        return

                    current_ncmoe = max(0, crossover_ncmoe - 5)
                    ts_proportions = self._calculate_tensor_split_proportions(self.analysis['gpus'])
                    if not ts_proportions:
                        yield {'action': 'log',
                               'message': "[CRITICAL] Could not calculate VRAM proportions. Halting."}
                        return

                    max_attempts = 40
                    for attempt in range(max_attempts):
                        current_ts_string = ",".join([f"{p:.2f}" for p in ts_proportions])
                        yield {'action': 'log',
                               'message': f"\n> Attempt {attempt + 1}/{max_attempts}: Testing with -ncmoe {current_ncmoe} and -ts {current_ts_string}"}

                        params_to_test = {'-ncmoe': str(current_ncmoe), '-ts': current_ts_string}
                        yield {'action': 'update_params', 'params': params_to_test}
                        result = yield {'action': 'test_ngl_value'}

                        if result['success']:
                            yield {'action': 'log', 'message': f"  > SUCCESS! Optimal configuration found."}
                            best_config_params = params_to_test
                            break

                        if not result['error_details']:
                            yield {'action': 'log', 'message': f"  > FAILED: Unknown error. Halting."}
                            break

                        failing_device = result['error_details']['device_id']
                        yield {'action': 'log', 'message': f"  > FAILED: OOM on Device {failing_device}."}

                        if failing_device == best_gpu_id:
                            yield {'action': 'log',
                                   'message': f"  > Action: Incrementing -ncmoe to relieve GPU {best_gpu_id}."}
                            current_ncmoe += 1
                        else:
                            yield {'action': 'log',
                                   'message': "  > Action: Adjusting -ts to relieve secondary GPU."}
                            ts_step = 0.02
                            if ts_proportions[failing_device] > ts_step:
                                ts_proportions[failing_device] -= ts_step
                                ts_proportions[best_gpu_id] += ts_step
                            else:
                                yield {'action': 'log',
                                       'message': f"[WARNING] Cannot reduce tensor split further for device {failing_device}. Trying ncmoe."}
                                current_ncmoe += 1

                        if current_ncmoe >= total_layers:
                            yield {'action': 'log',
                                   'message': "[CRITICAL] Reached max ncmoe value. Halting."}
                            break

                    if not best_config_params:
                        yield {'action': 'log',
                               'message': f"\n[CRITICAL] Could not find a working MoE configuration after {max_attempts} attempts."}
                        return

                else:  # ADAPTIVE DENSE MODEL MULTI-GPU STRATEGY
                    yield {'action': 'log', 'message': "\n[PHASE 3] Activating Dense multi-GPU tuning strategy."}

                    ts_proportions = self._calculate_tensor_split_proportions(self.analysis['gpus'])
                    if not ts_proportions:
                        yield {'action': 'log',
                               'message': "> No secondary GPU detected for splitting. Cannot proceed."}
                        return

                    yield {'action': 'log',
                           'message': "\n> Stage 1: Finding a safe baseline NGL via binary search..."}
                    initial_ts_string = ",".join([f"{p:.2f}" for p in ts_proportions])
                    yield {'action': 'update_params', 'params': {'-ts': initial_ts_string}}

                    low, high, best_known_ngl = 0, total_layers, 0
                    while low <= high:
                        mid = (low + high) // 2
                        if mid == 0: low = 1; continue
                        yield {'action': 'log', 'message': f"> Binary Search: Testing with -ngl {mid}"}
                        yield {'action': 'update_params', 'params': {'-ngl': str(mid)}}
                        result = yield {'action': 'test_ngl_value'}
                        if result['success']:
                            best_known_ngl = mid
                            low = mid + 1
                        else:
                            high = mid - 1

                    if best_known_ngl > 0:
                        yield {'action': 'log', 'message': f"> Found a safe baseline of -ngl {best_known_ngl}."}
                        best_config_params = {'-ngl': str(best_known_ngl), '-ts': initial_ts_string}
                    else:
                        yield {'action': 'log',
                               'message': "[CRITICAL] Could not find any viable NGL value. The model may be too large for the available VRAM."}
                        return

                    yield {'action': 'log',
                           'message': "\n> Stage 2: Adaptively searching for a higher NGL by adjusting tensor split..."}
                    max_attempts = 30
                    current_ngl_to_test = best_known_ngl + 1

                    tried_ts_configs_for_this_ngl = set()

                    for attempt in range(max_attempts):
                        if current_ngl_to_test > total_layers:
                            yield {'action': 'log',
                                   'message': "> Reached maximum possible layer offload."}
                            break

                        current_ts_string = ",".join([f"{p:.2f}" for p in ts_proportions])
                        tried_ts_configs_for_this_ngl.add(current_ts_string)

                        yield {'action': 'log',
                               'message': f"\n> Attempt {attempt + 1}/{max_attempts}: Trying -ngl {current_ngl_to_test} with -ts {current_ts_string}"}

                        yield {'action': 'update_params',
                               'params': {'-ngl': str(current_ngl_to_test), '-ts': current_ts_string}}
                        result = yield {'action': 'test_ngl_value'}

                        if result['success']:
                            yield {'action': 'log',
                                   'message': f"  > SUCCESS! -ngl {current_ngl_to_test} is viable. Updating optimal config."}
                            best_known_ngl = current_ngl_to_test
                            best_config_params = {'-ngl': str(best_known_ngl), '-ts': current_ts_string}
                            current_ngl_to_test += 1
                            tried_ts_configs_for_this_ngl.clear()
                            continue

                        if not result['error_details']:
                            yield {'action': 'log',
                                   'message': f"  > FAILED: Unknown error. Halting adaptive search."}
                            break

                        failing_device = result['error_details']['device_id']
                        yield {'action': 'log', 'message': f"  > FAILED: OOM on Device {failing_device}."}

                        ts_step = 0.02
                        if failing_device == best_gpu_id:
                            yield {'action': 'log',
                                   'message': "  > Action: Primary GPU failed. Attempting to offload to secondary GPU(s)."}
                            if len(ts_proportions) > 1:
                                if ts_proportions[best_gpu_id] > ts_step:
                                    ts_proportions[best_gpu_id] -= ts_step
                                    secondary_gpu_index = next(
                                        (i for i, p in enumerate(ts_proportions) if i != best_gpu_id), -1)
                                    if secondary_gpu_index != -1:
                                        ts_proportions[secondary_gpu_index] += ts_step
                                else:
                                    yield {'action': 'log',
                                           'message': "  > Cannot reduce tensor split further for primary GPU. Hard ceiling reached."}
                                    break
                            else:
                                break
                        else:
                            yield {'action': 'log',
                                   'message': f"  > Action: Adjusting -ts to relieve secondary GPU {failing_device}."}
                            if ts_proportions[failing_device] > ts_step:
                                ts_proportions[failing_device] -= ts_step
                                ts_proportions[best_gpu_id] += ts_step
                            else:
                                yield {'action': 'log',
                                       'message': f"  > Cannot reduce tensor split further for device {failing_device}. Halting."}
                                break

                        next_ts_string = ",".join([f"{p:.2f}" for p in ts_proportions])
                        if next_ts_string in tried_ts_configs_for_this_ngl:
                            yield {'action': 'log',
                                   'message': f"  > Detected a tensor split cycle trying to stabilize -ngl {current_ngl_to_test}. Reverting to last stable count."}
                            break

                    yield {'action': 'log',
                           'message': f"\n> Optimal multi-GPU layer offload found: -ngl {best_known_ngl}"}

        if not best_config_params:
            yield {'action': 'log', 'message': "[CRITICAL] Tuning phase failed to find a viable configuration."}
            return

        yield {'action': 'log', 'message': "\n[PHASE 4] Final Stability Benchmark & Performance Test..."}

        current_best_params = best_config_params.copy()
        final_benchmark_success = False
        max_benchmark_attempts = 10

        for attempt in range(max_benchmark_attempts):
            yield {'action': 'log', 'message': f"\n> Benchmark Attempt {attempt + 1}/{max_benchmark_attempts}..."}

            final_params = {**self.initial_params, **current_best_params, **baseline_flags, **fa_params}
            if is_moe and perform_multi_gpu_tuning: final_params['-ngl'] = '99'
            final_params.pop('-m', None)
            final_params.pop('--model', None)

            yield {'action': 'update_params', 'params': final_params}

            if attempt == 0:
                proceed = yield {'action': 'confirm_benchmark'}
                if not proceed:
                    yield {'action': 'log', 'message': "[INFO] Tuning aborted by user."}
                    return

            benchmark_result = yield {'action': 'load_and_benchmark'}

            if benchmark_result['success']:
                yield {'action': 'log', 'message': f"  > SUCCESS! Stable configuration found."}
                self.best_config = {
                    'params': current_best_params,
                    'tps': benchmark_result.get('avg_tps', 0.0)
                }
                final_benchmark_success = True
                break
            else:
                yield {'action': 'log',
                       'message': f"  > FAILED: Benchmark was not stable. Reason: {benchmark_result['error']}."}
                yield {'action': 'log', 'message': "  > Action: Adjusting -ts to be more conservative."}

                if is_moe or 'ts' not in current_best_params:
                    yield {'action': 'log',
                           'message': "[CRITICAL] Cannot automatically adjust parameters for this model type. Halting."}
                    break

                ts_proportions = [float(p) for p in current_best_params['ts'].split(',')]
                ts_step = 0.02

                secondary_proportions = sorted([(p, i) for i, p in enumerate(ts_proportions) if i != best_gpu_id])
                if not secondary_proportions or secondary_proportions[0][0] <= ts_step:
                    yield {'action': 'log', 'message': "[CRITICAL] Cannot reduce tensor split further. Halting."}
                    break

                weakest_gpu_index = secondary_proportions[0][1]
                ts_proportions[weakest_gpu_index] -= ts_step
                ts_proportions[best_gpu_id] += ts_step
                current_best_params['ts'] = ",".join([f"{p:.2f}" for p in ts_proportions])
                yield {'action': 'log', 'message': f"  > New tensor split: {current_best_params['ts']}"}

        if not final_benchmark_success:
            yield {'action': 'log',
                   'message': f"\n[CRITICAL] Could not find a stable benchmark configuration after {max_benchmark_attempts} attempts."}
            return

        yield {'action': 'log', 'message': f"\n  > Final Result: {self.best_config['tps']:.2f} t/s"}
        yield {'action': 'save_best_params'}

        yield {'action': 'log', 'message': "\n" + "=" * 27 + " Tuning Complete " + "=" * 28}
        yield {'action': 'log', 'message': f"Best Performance Found: {self.best_config['tps']:.2f} t/s"}
        return self.best_config