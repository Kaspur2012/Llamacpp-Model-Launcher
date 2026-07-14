# Changelog — v5.1 (2026-07-14)

## What's New

### Per-Model Llama.cpp Directory Override 🎯
Associate a specific llama.cpp build (CUDA, Vulkan, etc.) with each model, so switching models automatically uses the right build without manual directory changes.

- New `llamacppdir:` line in `models.txt` (same pattern as `env:`)
- New **Llama.cpp Directory** field in the Right Panel with **Browse...** and **× clear** buttons
- Falls back to global directory from `config.ini` if not set per-model
- Carried over on duplicate, cleared on new model

**Example `models.txt`:**
```
My CUDA Model
llama-server.exe -m D:\models\model.gguf -c 4096
llamacppdir: D:\llamacpp\cuda-build

My Vulkan Model
llama-server.exe -m D:\models\model2.gguf -c 4096
llamacppdir: D:\llamacpp\vulkan-build
```

### First-Run Welcome Dialog 🚀
On startup with no models file configured, the app now guides you through setup:

- **[Create Template]** — auto-creates a ready-to-edit `models.txt` in your Documents folder with real-world examples (including `llamacppdir:` and `env:` usage)
- **[Browse...]** — pick your own existing models file
- If a template already exists: offers **Open Existing** / **Overwrite** / **Browse**

### Missing File Detection 🔍
If the configured models file is deleted or moved, the app prompts to browse to it on startup instead of showing an empty state.

### Other Improvements
- **Path labels update on startup** — "Models File" label now correctly reflects the resolved path after template creation
- **Config API** — added `get_config()` and `set_config()` methods for individual key access

## Technical Changes
- `model_manager.py`: Added `model_llamacppdirs` dict, `_get_model_llamacppdirs()`, `create_default_template()`, and `DEFAULT_TEMPLATE` constant
- `config_manager.py`: Added `get_config()` and `set_config()` methods
- `right_panel.py`: Added Llama.cpp directory frame with input, browse, and clear buttons; `get_llamacpp_dir()`, `set_llamacpp_dir()`, `_browse_directory()`, `_clear_llamacpp_dir()`; `llamacpp_dir_changed` signal
- `main_window.py`: Added `_handle_startup_models_file()`, `_show_first_run_dialog()`, `_show_missing_file_dialog()`, `_create_and_set_template()`, `_browse_and_set_models_file()`, `_on_llamacpp_dir_changed()`; updated `populate_model_dropdown()` to accept resolved path; updated `load_model()` to use per-model directory

> 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B
