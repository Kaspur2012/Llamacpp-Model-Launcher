# Changelog — v0.55 (2026-08-18)

> Release EXE: `run_app_v055.exe` (built as a versioned name so the running `run_app.exe` could keep working during the upgrade)

## Critical Bug Fix

### Deleting a profile wiped the environment variables of other profiles 🐛

**Symptom:** After deleting a profile, the environment variables of most of the *other* profiles were gone — you had to go back into each one and re-add/save them.

**Root cause:** `ModelManager.delete_model()` walked the models file with a `found` flag:

```python
if stripped == model_name_to_delete:
    skip_next_line = True
    found = True
    continue
# Also skip associated env: and llamacppdir: lines after the command
if found and (stripped.startswith('env:') or stripped.startswith('llamacppdir:')):
    continue
```

`found` was never reset — once the deleted profile's name was hit, it stayed `True` for the **rest of the file**. The skip rule was meant to remove only the deleted profile's own `env:`/`llamacppdir:` lines, but it actually removed every single one of those lines appearing *after* the deleted profile — including lines belonging to completely unrelated profiles below it in the file.

**Fix:** Delete exactly the deleted model's own block — its name line, its command line, and the `env:`/`llamacppdir:` lines that immediately follow that command. No other line in the file is touched:

```python
start = name_idx          # the name line
end = name_idx + 1        # + the command line (if present)
while end < n and (lines[end].strip().lower().startswith('env:')
                   or lines[end].strip().lower().startswith('llamacppdir:')):
    end += 1              # + only this block's own metadata lines
output_lines = lines[:start] + lines[end:]
```

Verified with 5 regression cases: delete a middle profile (with env + directory), the first profile, the last profile, a profile with no env vars, and a nonexistent profile (file left untouched). In every case, all other profiles' env vars and directories survive.

**Note:** env vars that were already wiped by earlier deletes can't be restored by the app — they were physically removed from your models file. Re-type them on the affected profiles (or restore from a backup of the file if you have one).

## New Feature

### NInfer parameter browser: Image Max Tokens (ready for NInfer 0.6.2)

The NInfer parameter editor gained a new **Vision Parameters** section with an `Image Max Tokens` row (`--image-max-tokens`).

NInfer already downscales images server-side, but its pixel cap comes only from the model artifact's embedded settings (16.7M pixels for the Qwen3.8 artifacts — effectively "never downscale"). With several large screenshots in one conversation, that quickly blows through NInfer's 128M "vision attention pairs" budget and the server rejects the request with a 413. llama.cpp solves this with `--image-max-tokens`; this flag will do the same in NInfer once you upgrade to a build that supports it (0.6.2 — see the bug report in your NInfer runtime folder).

Recommended value: **1024** (1M pixels). A 1433×2000 screenshot becomes ~1184×864 (~999 vision tokens, still very readable), and ~8 large screenshots fit in a single request.

⚠️ **Do not add this flag yet** — the current 0.6.1 binary rejects unknown flags and the profile would fail to launch. It's in the browser now so it's one click away the moment the new binary is in place.

## Technical Changes

- `model_manager.py`: `delete_model()` rewritten to remove only the target model's own block (name + command + its immediately-following metadata lines) instead of a global skip of `env:`/`llamacppdir:` lines after the match
- `parameters_db.py`: `NINFER_PARAMETERS` gains a "Vision Parameters" section with the `--image-max-tokens` row
