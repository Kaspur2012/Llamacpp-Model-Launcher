# Changelog — v5.2 (2026-07-18)

## What's New

### Auto Browse Buttons for Path Parameters 📂
Parameters with file or directory paths now automatically get a **Browse...** button — no more hardcoded lists. Works for any path value, including `--spec-draft-model-command` and future parameters.

- Detects Windows paths (`D:\path\to\file`), Unix paths (`/usr/local/bin`), and relative paths with known extensions
- Context-aware file filters (GGUF, JSON, TXT, YAML, etc.) based on file extension
- Non-path parameters remain clean — no unnecessary buttons

### Configurable Safe Resource Overhead ⚙️
The Tuning Assistant's safety margins are now user-adjustable instead of hardcoded.

- New **Min VRAM (MB)** input (default: `600`) — minimum VRAM kept free during tuning
- New **Min RAM (MB)** input (default: `1024`) — minimum RAM kept free during tuning
- Inputs toggle on/off with the **"Ensure Safe Resource Overhead"** checkbox under *Additional Optimization*
- Allows power users to tighten or relax safety floors based on their system

## Technical Changes
- `right_panel.py`: Added `_is_file_path()` static method, `_browse_file_param()`, `_browse_directory_param()`; refactored `add_parameter_row()` to auto-detect paths and attach Browse buttons dynamically
- `summary_panel.py`: Added `vram_floor_input` and `ram_floor_input` fields; updated `_on_run_tuning()` to collect and pass floor values
- `tuning_wizard.py`: Replaced hardcoded `VRAM_FLOOR_GB` / `RAM_FLOOR_GB` with user-configured `vram_floor_mb` / `ram_floor_mb` values

> 🤖 All changes implemented by [pi](https://github.com/earendil-works/pi-coding-agent) with Qwen 3.6 27B
