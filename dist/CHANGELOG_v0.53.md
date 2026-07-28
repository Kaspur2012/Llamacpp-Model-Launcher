# Changelog — v0.53 (2026-07-28)

## What's New

### NInfer Inference Engine Support 🚀

Full integration of the **NInfer** inference engine (`ninfer-serve.exe`) alongside standard Llama.cpp models. Users can now manage and launch NInfer models from the same `models.txt` file and UI.

- **Dual-engine support** — The app now recognizes both `llama-server.exe` and `ninfer-serve.exe` as valid executables
- **Positional model path** — NInfer uses a positional model path (no `-m` flag), correctly handled in parse/build round-trips
- **Dedicated NInfer parameter set** — 5 parameter groups with NInfer-specific flags (`--host`, `--port`, `--model-id`, `--max-context`, `--batch-size`, `--kv-dtype`, `--mtp-draft-tokens`, `--lm-head-draft`, `--no-thinking`, `--no-cuda-graph`, `--default-max-tokens`, etc.)
- **Parameter browser auto-switches** — Switches between Llama.cpp and NInfer parameter sets when you select a model
- **Tuning Wizard blocked for NInfer** — The Tuning Wizard is Llama.cpp-specific; NInfer models show an informative message instead
- **`--no-webui` excluded for NInfer** — The auto-append `--no-webui` flag is Llama.cpp-only and no longer breaks NInfer launches
- **Browse button for model path** — NInfer model paths get a "Browse..." button with `.ninfer` file filter
- **Default template includes NInfer example** — First-run template now includes a ready-to-edit NInfer model entry

## Bug Fixes

- **`-m` flag leaking into NInfer commands** — Fixed `get_parameters()` to use the stored original key (`-m`) instead of the display label ("Model Path (positional)"), preventing corruption on save/reload
- **`UnboundLocalError` on model switch** — Moved `import os` to the top of `_is_file_path()` so path detection works on every model load
- **`--no-webui` appended to NInfer commands** — NInfer doesn't support `--no-webui`; the auto-append now checks engine type before modifying the command
- **`delete_model` cleanup** — Now properly removes associated `env:` and `llamacppdir:` lines when deleting a model

## Technical Changes

- `parameters_db.py`: Added `NINFER_PARAMETERS` list (5 groups, 17 parameters)
- `model_manager.py`: Parser accepts `ninfer-serve` prefix; `DEFAULT_TEMPLATE` includes NInfer example; `delete_model` cleans up env/dir lines
- `command_builder.py`: `parse()` detects `.ninfer` files and extracts positional model path; `build()` accepts `is_ninfer` flag for positional output; backwards compat for old `"Model Path (positional)"` keys
- `platform_utils.py`: Added `is_ninfer_command()` and `is_ninfer_params()` helper functions
- `main_window.py`: `_reload_editor_for_model()` passes `is_ninfer` to populate; `start_model()` passes `is_ninfer` to build; `save_parameters()` detects NInfer; `start_tuning_wizard()` blocks NInfer; `duplicate_model()` preserves NInfer mode
- `parameter_browser.py`: `set_mode()` switches between Llama.cpp and NInfer parameter sets dynamically
- `right_panel.py`: `populate()` accepts `is_ninfer` flag; `add_parameter_row()` uses flag for label display; `get_parameters()` reads stored `param_key` property; `_is_file_path()` recognizes `.ninfer` extension; file filters include NInfer models

> 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B
