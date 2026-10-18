# core/command_builder.py

import re
import shlex
import subprocess
from collections import namedtuple

from .platform_utils import IS_WINDOWS

Parameter = namedtuple('Parameter', ['key', 'value'])


def _parse_args(args_str: str) -> list[str]:
    r"""
    Custom argument parser that replaces shlex.split() to avoid backslash mangling.

    shlex.split() on Windows (posix=False) treats \" as an escaped quote, stripping
    the backslash. This corrupts JSON values like "{\"key\": true}" and also
    mangles Windows paths with backslashes.

    This parser:
    - Treats \\ as a literal backslash (preserving Windows paths)
    - Treats \" as an escaped quote ONLY inside double-quoted strings
    - Handles single-quoted strings (no escape processing)
    - Handles unquoted tokens with space separation
    """
    tokens = []
    i = 0
    length = len(args_str)

    while i < length:
        # Skip whitespace
        if args_str[i].isspace():
            i += 1
            continue

        if args_str[i] == '"':
            # Double-quoted string - process escape sequences
            # Handles both \" (shell-style) and "" (Windows list2cmdline-style)
            i += 1  # skip opening quote
            chars = []
            while i < length:
                ch = args_str[i]
                if ch == '\\' and i + 1 < length and args_str[i + 1] == '"':
                    # Shell-style escaped quote: \"
                    chars.append('"')
                    i += 2
                elif ch == '"' and i + 1 < length and args_str[i + 1] == '"':
                    # Windows list2cmdline-style escaped quote: ""
                    chars.append('"')
                    i += 2
                elif ch == '"':
                    # End of quoted string
                    i += 1
                    break
                else:
                    chars.append(ch)
                    i += 1
            tokens.append(''.join(chars))
        elif args_str[i] == "'":
            # Single-quoted string - no escape processing
            i += 1  # skip opening quote
            chars = []
            while i < length and args_str[i] != "'":
                chars.append(args_str[i])
                i += 1
            if i < length:
                i += 1  # skip closing quote
            tokens.append(''.join(chars))
        else:
            # Unquoted token
            chars = []
            while i < length and not args_str[i].isspace():
                chars.append(args_str[i])
                i += 1
            tokens.append(''.join(chars))

    return tokens


def _looks_like_path_start(token: str) -> bool:
    """True for tokens that look like the start of an absolute filesystem path
    (Windows drive letter, UNC, or POSIX absolute path)."""
    if re.match(r'^[A-Za-z]:[\\/]', token):
        return True
    return token.startswith('//') or token.startswith('\\\\') or token.startswith('/')


def _merge_path_tokens(tokens: list[str]) -> list[str]:
    r"""Merges runs of *unquoted* tokens back into a single path.

    When a models file contains an unquoted path with spaces, e.g.
        llama-server.exe -m D:\backup models\Qwen.gguf -c 4096
    _parse_args() splits it into separate tokens (D:\backup / models\Qwen.gguf).
    We rejoin a run of consecutive tokens when the run starts with an absolute
    path, none of the tokens look like a flag or start another absolute path,
    and the final token ends in a .gguf/.ninfer extension.
    """
    model_ext_re = re.compile(r'\.(gguf|ninfer)$', re.IGNORECASE)
    merged = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if _looks_like_path_start(tok) and not model_ext_re.search(tok):
            # Walk forward over consecutive non-flag tokens; stop once a
            # token ending in .gguf/.ninfer is consumed (the full path).
            j = i
            while j + 1 < n:
                next_tok = tokens[j + 1]
                if next_tok.startswith('-'):
                    break  # a flag: the run cannot be part of the path
                if _looks_like_path_start(next_tok):
                    break  # a second absolute path starts (e.g. python.exe D:\...\server.py)
                j += 1
                if model_ext_re.search(next_tok):
                    break
            if j > i:
                merged.append(' '.join(tokens[i:j + 1]))
                i = j + 1
                continue
        merged.append(tok)
        i += 1
    return merged


class CommandBuilder:
    """Parses command strings into structured data and builds them back."""

    @staticmethod
    def parse(command_str: str) -> list[Parameter]:
        r"""
        Parses a full command string into a list of Parameter tuples.

        Handles paths with spaces both when quoted
        (llama-server.exe -m "D:\backup models\Qwen.gguf") and unquoted
        (llama-server.exe -m D:\backup models\Qwen.gguf — merged back together
        when the run starts with an absolute path and ends in .gguf/.ninfer).
        For NInfer commands, the first token after the executable is the
        positional model path. For Strata commands, a positional token ending
        in 'server.py' right after the executable is kept as 'Serve Script'.
        """
        if not command_str:
            return []

        tokens = _parse_args(command_str)
        tokens = _merge_path_tokens(tokens)
        if not tokens:
            return []

        # The first token is always the executable
        executable = tokens[0]
        parts = [Parameter("Executable", executable)]

        # Detect if this is an NInfer command
        is_ninfer = 'ninfer-serve' in executable.lower()

        i = 1
        if is_ninfer and i < len(tokens):
            # For NInfer, the first token after executable is the positional model path
            parts.append(Parameter('-m', tokens[i]))
            i += 1
        elif i < len(tokens) and tokens[i].lower().endswith('server.py'):
            # Strata wrapper command: python.exe <path>\serve\server.py --engine strata ...
            # The serve script is a positional argument; keep it under a named key
            # so the editor can show/edit it and build_args() can re-emit it in place.
            parts.append(Parameter('Serve Script', tokens[i]))
            i += 1

        while i < len(tokens):
            token = tokens[i]
            if token.startswith('-'):
                # Check if the next token is a value or another flag
                if (i + 1 < len(tokens)) and not tokens[i + 1].startswith('-'):
                    parts.append(Parameter(token, tokens[i + 1]))
                    i += 2  # Consumed both key and value
                else:
                    parts.append(Parameter(token, None))  # It's a flag
                    i += 1
            else:
                # This case handles values that might not have been parsed correctly, ignore them
                i += 1

        return parts

    @staticmethod
    def build_args(parameters: list[Parameter], is_ninfer: bool = False,
                   is_strata: bool = False) -> list[str]:
        """
        Builds the raw argument list (program + arguments) from Parameter tuples.

        For NInfer models, the Model Path (-m) is placed positionally (right
        after the executable, no flag prefix). For Strata, the Serve Script
        (serve\\server.py) is placed positionally in the same way. Callers that
        need a display string can join this list with subprocess.list2cmdline
        (Windows) or shlex.join (elsewhere); callers that start a process should
        pass the list directly to QProcess.start() so no shell quoting is involved.
        """
        args_list = []
        executable = ""
        positional_model_path = None
        serve_script = None
        remaining_params = []

        for param in parameters:
            if param.key == "Executable":
                executable = param.value
                continue
            # For NInfer, extract the model path as positional arg
            # Accept both '-m' and 'Model Path (positional)' for backwards compat
            if is_ninfer and param.key in ('-m', 'Model Path (positional)'):
                positional_model_path = param.value
                continue
            # For Strata, extract the serve script as positional arg
            if is_strata and param.key in ('Serve Script', 'Serve Script (positional)'):
                serve_script = param.value
                continue
            remaining_params.append(param)

        # Build the args list
        if executable:
            args_list.append(executable)

        # For NInfer, model path comes positionally right after executable
        if is_ninfer and positional_model_path is not None:
            args_list.append(positional_model_path)

        # For Strata, the serve script comes positionally right after the python exe
        if is_strata and serve_script is not None:
            args_list.append(serve_script)

        for param in remaining_params:
            args_list.append(param.key)
            if param.value is not None:
                args_list.append(param.value)

        return args_list

    @staticmethod
    def build(parameters: list[Parameter], is_ninfer: bool = False,
              is_strata: bool = False) -> str:
        """Reconstructs a command string from a list of Parameter tuples."""
        args_list = CommandBuilder.build_args(parameters, is_ninfer=is_ninfer,
                                              is_strata=is_strata)
        if not args_list:
            return ""
        if IS_WINDOWS:
            return subprocess.list2cmdline(args_list)
        return shlex.join(args_list)