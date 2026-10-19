# Changelog — v0.56 (2026-10-18)

> Release EXE: `run_app.exe` (rebuilt in `dist\` with the standard name)

## New Feature

### Strata inference engine support 🚀

The launcher now supports **Strata** (`serve/server.py` wrapper + `strata.exe` engine) alongside Llama.cpp and NInfer. Two example profiles ship in the default template and `model_file_examples.txt`:

- `Strata-Qwen3-IQ3_S` — normal (sampling-config) launch
- `Strata-Qwen3-IQ3_S-Greedy` — greedy launch (config without the sampling block)

Both run the venv Python + `serve\server.py --engine strata --config <json> --port 8081` directly — no .bat files, no elevation prompt.

**Launch (mirrors the Strata run scripts):**

- **Large pages without UAC** — before starting Strata, the launcher enables `SeLockMemoryPrivilege` + `SeIncreaseWorkingSetPrivilege` in its own token so the engine gets 2 MB pages. One-time setup: run `grant-large-pages.ps1` **as administrator once**, then log off/on. Until then Strata still runs, falling back to 4 KB pages with a warning in the output log.
- **Greedy config auto-heal** — if the greedy JSON is *missing*, the launcher regenerates it from the live config via `make-greedy-config.py` before launch (and aborts the launch if that fails). If the file exists it is used as-is — your direct edits are never overwritten.
- **Port conflict guard** — refuses to launch when the `--port` is already listening (the Strata wrapper auto-restarts its engine, so a second instance against a busy port leaves traces).
- **Ready detection** — the wrapper's `ready: http://...` line flips the status to LOADED and triggers Auto-Open of the Strata web app.

**Stop = full STOP-STRATA.bat replication.** The Stop button kills the wrapper tree first, then sweeps any leftover `strata.exe` / `strata-vision.exe` processes, then polls the port until it is free (up to 20 s), killing Strata/python holders and warning about unrelated ones — no auto-restart survivors, no port left busy.

**Strata Config (JSON) editor.** Selecting a Strata profile shows a **Strata Config (JSON)** section under the parameter editor that mirrors the profile's own config file exactly, as real editable rows in five groups:

- **Engine Args** — the `strata.exe` command line inside the JSON (`--max-context`, `--kv`, `--kv-grow`, `--vision`, `--spec`, `--adapt-*`, `--ple-io`...) with add/remove per row
- **Sampling** — `temperature`, `top_p`, `top_k`, `min_p`, `presence_penalty`, `repetition_penalty` (delete all rows = greedy decoding)
- **Config Settings** — `exe`, `cwd`, `gpu`, `port`, `reasoning_effort`, `layer_split`, `log`, `tokenizer`, `lib_dirs`... every top-level key
- **Vision** — the `strata-vision` block (`mmproj`, `model`, `cuda_device`, `max_tokens`...)
- **Engine Environment** — the `env` dict (`STRATA_PF_FUSED`...)

**Save to File** writes both targets: the JSON config (validated before writing; the previous version is kept as `<name>.json.bak`) and the models.txt plumbing. If the JSON write fails, nothing is saved — the two files never disagree. Types are preserved: booleans stay booleans, `port` stays a number, `gpu: [1]` stays an int list, env values stay strings.

**Unsaved config edits are live at launch.** Like llama.cpp profiles (which launch from the editor, not from the saved file), clicking **Load** on a Strata profile first writes any unsaved edits in the config editor to the JSON file — previous version kept as `.bak`, launch aborted if the write fails — so the engine starts with exactly what the launcher shows. **Reset still undoes those edits**: the panel keeps an in-memory snapshot of the config as it was when the profile was selected (or last explicitly saved), and Reset restores from that — even though the launch wrote the edits to disk. The next Load then re-applies the restored values to the file.

**Parameter browser for Strata** — a dedicated Strata flag set for `serve/server.py` (Engine & Config, Server, GPU & Memory, Advanced) plus five click-to-add groups of `strata.exe` engine flags condensed from its `--help` (Context & KV, Model & PLE, Speculative (MTP), Expert Cache & Adaptive, Prefill/Cache/GPU). Engine-arg additions land in the config's args section, not the command line.

**Notes**

- The Tuning Wizard is disabled for Strata profiles (its tuning lives in the JSON config).
- `--no-webui` is never injected into Strata commands.
- The command's `--port` is the real listening port; the JSON's `port` key is metadata for Strata's own setup/MCP tools — keep both in sync or delete the JSON one.

## Fixes & Improvements

### Unquoted model paths with spaces now parse correctly

A models-file line like `llama-server.exe -m D:\backup models\Qwen.gguf -c 4096` used to split the path into separate tokens. The parser now merges a run of unquoted tokens back into one path when the run starts with an absolute path and ends in `.gguf`/`.ninfer`. Quoted paths keep working as before.

### Duplicate profile names keep their own env/dir blocks

When two profiles shared an identical command (Duplicate + rename), each occurrence now keeps its own `env:`/`llamacppdir:` lines instead of the metadata being merged or landing in the wrong block. Command lines are recognized structurally (executable token / explicit path) rather than by name matching.

### GPU names containing commas no longer break detection

The `nvidia-smi` fallback parser took the *first* comma-separated field as the GPU name, so names containing commas (e.g. some NVIDIA RTX A-series readings) shifted the VRAM columns and produced malformed rows. The last two fields are now always the memory numbers and the name is everything before them; malformed lines are skipped with a log line instead of crashing detection.

### Tuning Wizard: honors your Min VRAM floor and stops thrashing

- The context-size search's safety stops used a hardcoded 600 MB free-VRAM floor; they now use the **Min VRAM (MB)** value you set in the summary panel.
- Fallback strategies (single-GPU failure → multi-CPU) now honor your target-context / Maximize selections instead of forgetting them.
- The per-level layer-drop loop was cut from 20 to 5 rounds — the inner `-ts` balancing already retries up to 50 times, and 20×50 full model loads per level could thrash the machine for hours on large models.

### Web UI checkbox fixes

- The **Enable Web UI** / **Auto-Open** checkboxes are restored to their previous state after the Tuning Wizard finishes (they were force-cleared and stayed off).
- Checkbox signal wiring switched from `stateChanged` (whose int value differs between Qt builds) to `toggled(bool)` in the left and summary panels — the "state == 2" checks silently misfired on some builds.
- Removed a broken `Resources/check.png` reference from the summary panel stylesheet.

### Output log stays fast on long runs

The server output viewer is now bounded (~200 K characters, trimmed on a line boundary down to ~100 K). Long server sessions no longer grow the document without limit and slow the UI.

## Technical Changes

- **New** `core/strata_config.py` — load/save the Strata JSON (utf-8-sig read, `indent=1` write, `.bak` backup, round-trip validation), split/merge between the JSON and editor sections with type-preserving coercion
- **New** `ui/strata_config_panel.py` — the five-section JSON config editor widget (rows, checkboxes for booleans, add/remove per section, unsaved-changes tracking)
- **New** `grant-large-pages.ps1` — one-time elevated setup that grants `SeLockMemoryPrivilege` + `SeIncreaseWorkingSetPrivilege` to your account via the LSA policy API (`-Revoke` to undo); log off/on afterwards
- `platform_utils.py`: `is_strata_command`/`is_strata_params` detection, `port_in_use`, `enable_large_page_privileges` (ctypes `AdjustTokenPrivileges`), `strata_full_stop` (STOP-STRATA replication), `regenerate_greedy_config`
- `command_builder.py`: `Serve Script` positional parameter preserved through parse→build; `_merge_path_tokens` for unquoted paths with spaces
- `model_manager.py`: `_is_command_line` structural detection; per-occurrence `env:`/`llamacppdir:` lists; Strata examples in `DEFAULT_TEMPLATE`
- `parameters_db.py`: `STRATA_PARAMETERS` (serve/server.py flags) + `STRATA_ENGINE_ARGS` (strata.exe flags, `target: strata_args`)
- `parameter_browser.py`: `set_mode('llama'|'ninfer'|'strata')`; Strata mode shows both Strata groups
- `right_panel.py`: embeds the Strata config panel (visible only for Strata profiles, mirrors the profile's own `--config` file); `.py` added to browse-able extensions
- `main_window.py`: Strata launch preflight (port guard, greedy regen-if-missing, privilege enable + log lines, unsaved config edits written to the JSON before launch), `ready:` line → LOADED, full-stop on unload, config saved before models.txt, wizard gate, engine-arg browser routing
- `system_analyzer.py`, `tuning_wizard.py`, `left_panel.py`, `summary_panel.py`: the fixes listed above
