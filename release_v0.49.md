## v0.49

*   07/07/2026 -
    *   **llama.cpp b9870 compatibility — Tuning Wizard log parsing fix**
        *   **Root cause**: llama.cpp build 9870 hides critical model metadata (layer count, context length, GPU info, KV cache stats) at default verbosity (`-lv 3`). Trace verbosity (`-lv 4`) is now required.
        *   **`tuning_wizard.py`**: Added `-lv 4` flag to Phase 1 (metadata extraction) and Phase 2 (KV cache probe) parameter sets.
        *   **`main_window.py` — `cuda_device_regex` rewrite**: Old format `Device 0: NVIDIA GeForce RTX 3090,` → New format `CUDA0   : NVIDIA GeForce RTX 3090 (24575 MiB, ...)`. Regex updated with backward compatibility for older builds.
        *   **`main_window.py` — New `kv_memory_table_regex`**: The old `llama_kv_cache: size = X MiB (Y cells)` line was removed in b9870. Added fallback parser for the new `| memory breakdown [MiB] |` table, extracting context (KV cache) MiB per GPU. MB/token derived from `context_mib / (n_ctx_slot × n_slots)`.
        *   **`main_window.py` — `n_expert` regex fix**: Adjusted `\s+` → `\s*` to handle extra whitespace in `print_info: n_expert              = 32`.
        *   **`main_window.py` — GPU parsing loop**: Updated to handle both old (2 capture groups) and new (3 capture groups) CUDA device regex formats.
        *   **`main_window.py` — KV cache `handle_stdout`**: New section 1b parses memory table rows as fallback when old-format KV line is absent.
        *   **`command_builder.py`**: Custom `_parse_args()` replaces `shlex.split()` to avoid backslash mangling on Windows (preserves paths and JSON values).
    *   **Windows path handling fix**: `shlex.split` now uses non-POSIX mode on Windows to properly preserve backslashes in file paths
    *   **f-string backslash fix**: Extracted Windows example paths into dedicated variables (avoids backslash escaping issues in f-strings on Python < 3.12)
    *   **Chat template file browser**: Added "Browse..." button for `--chat-template-file` parameter with Jinja/text file filter
    *   **Refactored `_browse_file`**: Now accepts custom file type filters for flexible reuse
    *   **Added `.idea/` to `.gitignore`** (PyCharm IDE config)
    *   **Initialized `CHANGELOG.md`**
    
    > 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B
