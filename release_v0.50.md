## v0.50

*   07/11/2026 -
    *   **Optional Environment Variables field for mmproj GPU offloading**
        *   **Motivation**: Discovered `MTMD_BACKEND_DEVICE` env var can route the multimodal projector (`--mmproj`) to a secondary GPU (e.g., RTX 2070 Super / `cuda1`) while keeping the main LLM on the primary GPU (e.g., RTX 3090 / `cuda0`), avoiding CPU offload and boosting image reading speed.
        *   **`right_panel.py`**: Added `QTextEdit` for environment variables above the "Executable" parameter. Styled with dark theme, placeholder `MTMD_BACKEND_DEVICE=cuda1`, max height 60px, monospace font. Changes mark the model as dirty (unsaved).
        *   **`right_panel.py` — `get_env_vars()` / `set_env_vars(text)`**: New getter/setter methods for the env vars field.
        *   **`right_panel.py` — `populate()`**: Now accepts optional `env_vars` parameter to populate the field when loading a model.
        *   **`model_manager.py`**: Parses optional third line prefixed with `env:` in the models file (e.g., `env:MTMD_BACKEND_DEVICE=cuda1`). Stores in `model_env_vars` dict. `save_model()` writes or updates this line on save. Backward compatible — old entries without `env:` lines work fine.
        *   **`model_manager.py` — `_get_model_env_vars()`**: New method to retrieve all env vars for all models (used by `main_window.py` on model switch).
        *   **`main_window.py` — `load_model()`**: Reads env vars from the right panel and injects `set KEY=value` lines into the Windows batch file before the `llama-server.exe` command. Strips leading `set ` if user already typed it (graceful handling).
        *   **`main_window.py` — `save_parameters()`**: Saves env vars to the model file via `model_manager.env_vars_to_save`.
        *   **`main_window.py` — `model_selected()`**: Loads env vars for the selected model into the right panel.
        *   **`main_window.py` — `_reset_current_model()`**: Restores saved env vars after parameter reset.
        *   **`main_window.py` — `add_new_model()`**: Clears env vars for new models.
        *   **`main_window.py` — `duplicate_model()`**: Carries over env vars from the original model.
        *   **`main_window.py` — `populate_model_dropdown()`**: Clears env vars when no models exist.
    *   **Batch file injection**: Generated `.bat` file now includes `set KEY=value` lines before the main command, e.g.:
        ```batch
        @echo off
        set MTMD_BACKEND_DEVICE=cuda1
        llama-server.exe -m D:/backup_models/llm/Qwen3.6-27B-UD-Q5_K_XL.gguf ...
        ```
    *   **PyInstaller build**: Created standalone `run_app.exe` (37 MB, `--onefile --windowed`) with custom `llamacpp.ico` icon.
    
    > 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B UD Q5K XL
