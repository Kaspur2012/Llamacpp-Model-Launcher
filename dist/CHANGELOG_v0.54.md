# Changelog — v0.54 (2026-08-16)

## Critical Bug Fix

### Per-model Environment Variables lost on save 🐛

**Symptom:** Typing an environment variable (e.g. `MTMD_BACKEND_DEVICE=cuda1`) into a profile, saving, and exiting — the variable was gone when reopening the app. Affected every profile, not just one.

**Root cause:** `ModelManager.save_model()` decided where to write the `env:` line using:

```python
base_idx = lines.index(new_command + '\n') + 1
```

`list.index()` finds the **first** line in the file matching that command text. Whenever two profiles share the exact same command (which is what happens every time you **Duplicate** a profile and rename it — e.g. `…MTP`, `…MTP_200K-MultiGPU-Tensor`, `…F16_125K-MultiGPU-Tensor`), the env line was silently written into the **other** profile's block. Your profile never received the line, so the field appeared empty on the next launch.

**Fix:** Use the index of the model block that was actually found, instead of re-searching the file for the command text:

```python
base_idx = i + 2
```

Verified end-to-end: duplicate a profile → type env var → rename → save → exit → reopen → the variable is on the right profile.

## Improvements

### Environment variables now work correctly on all platforms

Previously, per-model env vars were injected on Windows only, by writing raw `set KEY=value` lines into a temporary `.bat` file. That silently did nothing on macOS/Linux, and unsanitized user text inside batch-file syntax was also a command-injection risk (a crafted `env:` line in a shared models file could smuggle shell commands).

Env vars are now applied via `QProcessEnvironment` on **both** platforms — each `KEY=value` pair is passed as a real environment variable, not interpreted shell text. A new `_parse_env_vars_text()` validator rejects lines whose key is not a valid environment variable identifier (and logs them to the output panel instead of applying them).

### Tuning Wizard benchmarks the right server

The wizard's API benchmark/stability requests were hardcoded to `http://127.0.0.1:8080`. If a profile uses a custom `--host`/`--port`, benchmark requests silently hit the wrong (or no) server. The wizard now reads the model's actual `--host`/`--port` from its command.

### More robust parameter row reading

`RightPanel.get_parameters()` no longer assumes the input widget is always at layout index 0 of a row. Input widgets are now tagged with an `is_param_input` property, so future layout changes (icons, warning labels, etc.) can't break parameter reading.

## Technical Changes

- `model_manager.py`: `save_model()` uses the located model index (`i + 2`) for env/dir metadata instead of `lines.index(new_command)`
- `main_window.py`: `QProcessEnvironment`-based env var injection on both platforms; `.bat` file no longer contains `set` lines; new `_parse_env_vars_text()` key validation; wizard host/port passed from `get_server_address_from_command()`
- `tuning_wizard.py`: `TuningWizard.__init__` accepts `host`/`port`; `run_api_benchmark_requests()` / `run_stability_api_request()` build the URL from them
- `right_panel.py`: `is_param_input` property tag + `_find_param_input_widget()` helper
