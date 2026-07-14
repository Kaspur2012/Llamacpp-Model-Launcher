# Changelog

All notable changes to this project will be documented in this file.

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
