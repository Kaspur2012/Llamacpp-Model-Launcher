# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- **Multi-GPU "Maximize Context" early stop**: Binary search refinement no longer resets `-ts` to stale baseline on every iteration; carries a running `-ts` value seeded from the failed doubling attempt and persisted across all refinement iterations
- **Doubling loop premature exit**: After binary search refinement, checks system-wide VRAM surplus before stopping; resumes doubling if headroom remains
- **Ping-pong saturation too aggressive**: Replaced instant "saturation" with real midpoint refinement (up to 8 bisection rounds); only declares saturation when gap < 0.005
- **Adaptive `-ts` step size**: Step size now scales with smaller GPU's VRAM fraction, reducing overshoot on asymmetric setups (e.g., 24+8 GB)
- **VRAM Back-Fill for multi_vram**: Added TS Back-Fill pass that fine-tunes `-ts` at final context to squeeze leftover headroom
- **Env vars / llama.cpp dir wiped during tuning**: `RightPanel.populate()` now uses `None` sentinels instead of `""` defaults; wizard snapshots and threads these values through all `populate()` calls
- **Per-GPU VRAM visibility**: Resting VRAM log now shows all GPUs' free VRAM, not just the primary

### Technical Details
- `tuning_wizard.py` — `_run_test_with_ts_balancing`: Added diagnostic logging (TS values, OOM device, per-GPU VRAM on saturation), midpoint refinement with ping-pong count and gap tolerance, adaptive step size based on GPU asymmetry
- `tuning_wizard.py` — `_tune_context_size_adaptive`: Added `running_ts` persistence across binary-search iterations, surplus check after refinement to resume doubling, TS Back-Fill for `multi_vram` strategy
- `right_panel.py` — `populate()`: Changed `env_vars` and `llamacpp_dir` defaults from `""` to `None`; fields only overwritten when explicit value passed
- `main_window.py` — `start_tuning_wizard()`: Captures `_wizard_env_vars` and `_wizard_llamacpp_dir` before wizard starts
- `main_window.py` — `_update_editor_params()` / `_restore_params_from_snapshot()`: Pass snapped values through to `populate()`
- `main_window.py` — `_finish_tuning_wizard()` / `_cancel_tuning_wizard()`: Clean up snapshot attributes
- `main_window.py` — idle-signal VRAM logging: Logs all GPUs' free VRAM on single line

> 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B UD Q5K XL

## [Unreleased]

### Added
- **Per-model Llama.cpp directory override**: Associate a specific llama.cpp build (CUDA, Vulkan, etc.) with each model via `llamacppdir:` line in `models.txt`
- **Llama.cpp Directory field in Right Panel**: Text input with **Browse...** button and **× clear** button for per-model directory management
- **First-run welcome dialog**: On startup with no models file, offers to create a default template or browse to an existing file
- **Template auto-creation**: Generates a ready-to-edit `models.txt` in Documents folder with real-world examples showcasing all features
- **Missing file detection**: Prompts user to browse to models file if configured path no longer exists
- **Config get/set API**: Added `get_config(key)` and `set_config(key, value)` methods for individual key access

### Fixed
- **Path labels on startup**: "Models File" label now correctly displays the resolved path after template creation
- **PyQt6 ButtonRole**: Fixed `QMessageBox.Role` → `QMessageBox.ButtonRole` for PyQt6 compatibility

### Technical Details
- `model_manager.py`: Added `model_llamacppdirs` dict, `_get_model_llamacppdirs()`, `create_default_template()`, and `DEFAULT_TEMPLATE` constant
- `config_manager.py`: Added `get_config()` and `set_config()` methods
- `right_panel.py`: Added Llama.cpp directory frame with input, browse, and clear buttons; `get_llamacpp_dir()`, `set_llamacpp_dir()`, `_browse_directory()`, `_clear_llamacpp_dir()`; `llamacpp_dir_changed` signal
- `main_window.py`: Added `_handle_startup_models_file()`, `_show_first_run_dialog()`, `_show_missing_file_dialog()`, `_create_and_set_template()`, `_browse_and_set_models_file()`, `_on_llamacpp_dir_changed()`; updated `populate_model_dropdown()` to accept resolved path; updated `load_model()` to use per-model directory

> 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B

## [Unreleased]

### Fixed
- **Windows path handling**: `shlex.split` now uses non-POSIX mode on Windows to properly preserve backslashes in file paths
- **f-string backslash escaping**: Extracted Windows example paths into dedicated variables, avoiding backslash issues in f-strings (Python < 3.12 limitation)

### Added
- **Chat template file browser**: Added "Browse..." button for chat template file parameter with Jinja/text file filter
- **Flexible file filters**: Refactored `_browse_file` helper to accept custom file type filters

### Changed
- Added `.idea/` to `.gitignore` (PyCharm IDE config)

> 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B

## [0.1.0] - 2026-04-03

### Added
- macOS Apple Silicon support
- Platform-specific setup instructions in README

### Changed
- Updated README with cross-platform documentation
