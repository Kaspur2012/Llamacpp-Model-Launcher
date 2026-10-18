# core/strata_config.py
"""Read/edit/write the Strata JSON config so the parameter editor can expose
its settings (engine args, sampling, vision, env...) as real rows.

The panel always mirrors the exact contents of the profile's own --config
file; Save writes that same file (a .bak copy of the previous version is
written first). Greedy configs are only regenerated from the live one when
the greedy file is missing (see main_window preflight), so direct edits to
any config file are never silently overwritten.
"""

import json
import os
import shutil
from collections import namedtuple

Row = namedtuple('Row', 'key value')  # value None = flag-only (args) ; bool = checkbox
ConfigSections = namedtuple('ConfigSections', 'args sampling settings vision env')

# Keys handled by their own section, not the generic Settings list
SPECIAL_KEYS = ('args', 'sampling', 'vision', 'env')


def load_config(path):
    """Returns (dict, None) or (None, error_message). utf-8-sig like server.py."""
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            return json.load(f), None
    except (OSError, ValueError) as e:
        return None, str(e)


def save_config(path, data):
    """Writes the config (indent=1 like setup.py/make-greedy-config.py) after a
    .bak backup. Returns (ok, message)."""
    try:
        text = json.dumps(data, indent=1, ensure_ascii=False)
        json.loads(text)  # round-trip sanity before touching the file
        if os.path.exists(path):
            try:
                shutil.copy2(path, path + '.bak')
            except OSError:
                pass  # backup is best-effort; the write itself is what matters
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
        return True, path
    except (OSError, ValueError) as e:
        return False, str(e)


def split_args(args_list):
    """Flattens the engine args array into (flag, value|None) rows."""
    rows = []
    i = 0
    n = len(args_list)
    while i < n:
        tok = str(args_list[i])
        if tok.startswith('-'):
            if i + 1 < n and not str(args_list[i + 1]).startswith('-'):
                rows.append(Row(tok, str(args_list[i + 1])))
                i += 2
            else:
                rows.append(Row(tok, None))
                i += 1
        else:
            # Orphan value (malformed config): keep it as a valueless-named row
            # so a round-trip never silently drops data.
            rows.append(Row('', tok))
            i += 1
    return rows


def merge_args(rows):
    """Rebuilds the flat args array from (flag, value|None) rows."""
    out = []
    for r in rows:
        if r.key:
            out.append(r.key)
            if r.value is not None and str(r.value) != '':
                out.append(str(r.value))
        elif r.value is not None:
            out.append(str(r.value))
    return out


def _render_value(value):
    """JSON value -> editor text (lists become comma-separated)."""
    if isinstance(value, bool):
        return value  # checkbox
    if isinstance(value, list):
        return ', '.join(str(v) for v in value)
    return str(value)


def _coerce(text, old):
    """Editor text -> JSON value, keeping the old value's type when known."""
    if isinstance(old, bool):
        if isinstance(text, bool):
            return text
        return str(text).strip().lower() in ('1', 'true', 'yes', 'on')
    if isinstance(old, int):
        try:
            return int(str(text).strip())
        except ValueError:
            return str(text).strip()
    if isinstance(old, float):
        try:
            return float(str(text).strip())
        except ValueError:
            return str(text).strip()
    if isinstance(old, list):
        items = [p.strip() for p in str(text).split(',') if p.strip()]
        # Keep the element type of the original list (gpu: [1] stays int)
        if old and isinstance(old[0], bool):
            return [i.lower() in ('1', 'true', 'yes', 'on') for i in items]
        if old and isinstance(old[0], (int, float)):
            try:
                return [type(old[0])(i) for i in items]
            except ValueError:
                return items
        return items
    if isinstance(old, str):
        # Existing string keys (env values, paths...) stay strings
        return str(text)
    # New key (no old value): infer the type from the text
    t = str(text).strip()
    low = t.lower()
    if low in ('true', 'false'):
        return low == 'true'
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def split_config(data):
    """Splits a config dict into editor sections (lists of Row)."""
    args_rows = split_args(data.get('args', []))
    sampling_rows = [Row(k, _render_value(v)) for k, v in (data.get('sampling') or {}).items()]
    vision_rows = [Row(k, _render_value(v)) for k, v in (data.get('vision') or {}).items()]
    env_rows = [Row(k, _render_value(v)) for k, v in (data.get('env') or {}).items()]
    settings_rows = [Row(k, _render_value(v))
                     for k, v in data.items() if k not in SPECIAL_KEYS]
    return ConfigSections(args_rows, sampling_rows, settings_rows, vision_rows, env_rows)


def merge_config(original, sections):
    """Rebuilds the config dict from editor sections, preserving key order."""
    result = {}

    def section_dict(rows, old_block):
        out = {}
        for r in rows:
            if not r.key:
                continue
            out[r.key] = _coerce(r.value, (old_block or {}).get(r.key))
        return out

    old_sampling = original.get('sampling') or {}
    old_vision = original.get('vision') or {}
    old_env = original.get('env') or {}
    old_settings = {k: v for k, v in original.items() if k not in SPECIAL_KEYS}

    # Preserve the original key order for keys that still exist
    for key in original:
        if key == 'args':
            result['args'] = merge_args(sections.args)
        elif key == 'sampling':
            block = section_dict(sections.sampling, old_sampling)
            if block:
                result['sampling'] = block
        elif key == 'vision':
            block = section_dict(sections.vision, old_vision)
            if block:
                result['vision'] = block
        elif key == 'env':
            block = section_dict(sections.env, old_env)
            if block:
                result['env'] = block
        else:
            for r in sections.settings:
                if r.key == key:
                    result[key] = _coerce(r.value, old_settings.get(key))
                    break

    # Keys added by the user (not in the original file)
    for r in sections.settings:
        if r.key and r.key not in result and r.key not in SPECIAL_KEYS:
            result[r.key] = _coerce(r.value, None)
    for block_name, rows, old_block in (('sampling', sections.sampling, old_sampling),
                                        ('vision', sections.vision, old_vision),
                                        ('env', sections.env, old_env)):
        block = section_dict(rows, old_block)
        if block and block_name not in result:
            result[block_name] = block
    if 'args' not in result:
        result['args'] = merge_args(sections.args)
    return result
