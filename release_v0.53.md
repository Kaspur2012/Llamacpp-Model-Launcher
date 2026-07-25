## v0.53

*   07/25/2026 -
    *   **Multi-GPU "Maximize Context" early stop fix**
        *   **Motivation**: On asymmetric multi-GPU setups (e.g., RTX 3090 + RTX 2070), the "Maximize Context" phase would stop far too early because the binary search refinement block reset the tensor split (`-ts`) back to a stale baseline on every iteration, and the outer doubling loop broke unconditionally after the first refinement — even when significant VRAM surplus remained.
        *   **`tuning_wizard.py` — `_run_test_with_ts_balancing`**:
            *   Added diagnostic logging: every OOM attempt now logs `-ts` values, attempt number, and failing device. On saturation, logs per-GPU VRAM snapshot.
            *   Implemented real midpoint refinement: ping-pong detection no longer causes instant "saturation". Instead, it computes the midpoint between the last two splits and tries it (up to 8 bisection rounds). Only returns `'saturation'` when the gap is below 0.005 tolerance.
            *   Adaptive `-ts` step size: step is now scaled by the smaller GPU's fraction of total VRAM (`max(0.005, min(0.02, smaller_gpu_frac * 0.15))`). For a 24+8 GB pair, this gives ~0.008 instead of 0.02, reducing overshoot on asymmetric setups.
        *   **`tuning_wizard.py` — `_tune_context_size_adaptive` (doubling loop)**:
            *   After binary search refinement converges, no longer unconditionally `break`s. Instead checks system-wide VRAM surplus. If surplus remains, `continue`s the outer doubling loop to try larger contexts. Only `break`s if safety check confirms no headroom left.
        *   **`tuning_wizard.py` — Binary Search Refinement block**:
            *   Seeds `running_ts` from the failed doubling attempt's converged split (`temp_params['-ts']`) instead of the stale `best_known_params['-ts']` (often `1.000,0.000`).
            *   Persists `running_ts` across all binary-search iterations regardless of success or failure, so each refinement test starts from the last known split instead of resetting to scratch. Reduces `[TS diag]` lines per refinement from dozens down to 0–2 small nudges.
        *   **`tuning_wizard.py` — Phase 4.5 (VRAM Back-Fill)**:
            *   Added TS Back-Fill pass for `multi_vram` strategy. After Phase 4 finishes, does up to 10 small (1%) `-ts` shifts toward the primary GPU to squeeze leftover headroom.
        *   **`main_window.py` — idle-signal VRAM logging**:
            *   Resting VRAM log now prints **all** GPUs' free VRAM on a single line: `[WIZARD] All GPUs: GPU 0: 200 MiB free | GPU 1: 4200 MiB free`
    *   **Environment Variables / llama.cpp dir wipe during tuning fix**
        *   **Motivation**: `RightPanel.populate()` unconditionally overwrote the env vars and llama.cpp dir fields every time it was called. During tuning, wizard-driven `populate()` calls never passed those arguments, so they silently fell back to `""` defaults — wiping the user's input. This caused every test load after the first parameter update to run without the user's environment variables or per-model directory override.
        *   **`right_panel.py` — `populate()`**: Changed `env_vars` and `llamacpp_dir` defaults from `""` to `None`. Fields are only overwritten when an explicit value is passed. Any future caller that forgets these args will leave the current UI value untouched.
        *   **`main_window.py` — `start_tuning_wizard()`**: Captures `_wizard_env_vars` and `_wizard_llamacpp_dir` from the editor before the wizard starts.
        *   **`main_window.py` — `_update_editor_params()` / `_restore_params_from_snapshot()`**: Both now pass the snapped values through to `populate()` via `getattr(self, '_wizard_env_vars', ...)` (falls back to live editor if no snapshot exists).
        *   **`main_window.py` — `_finish_tuning_wizard()` / `_cancel_tuning_wizard()`**: Clean up the snapshot attributes so stale values never leak into an unrelated later run.
    *   **PyInstaller build**: Created standalone `run_app.exe` (~38.6 MB, `--onefile --windowed`) with custom `llamacpp.ico` icon.

    > 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B UD Q5K XL
