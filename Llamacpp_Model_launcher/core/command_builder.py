# core/command_builder.py

import re
import shlex
import subprocess
from collections import namedtuple

from .platform_utils import IS_WINDOWS

Parameter = namedtuple('Parameter', ['key', 'value'])


def _parse_args(args_str: str) -> list[str]:
    """
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


class CommandBuilder:
    """Parses command strings into structured data and builds them back."""

    @staticmethod
    def parse(command_str: str) -> list[Parameter]:
        """
        Parses a full command string into a list of Parameter tuples.
        Handles complex paths by identifying the .gguf or .ninfer file.
        For NInfer commands, detects the positional model path (token after executable).
        """
        if not command_str:
            return []

        parts = []
        prefix_str, suffix_str = "", command_str

        # Special handling for Windows paths in GGUF/NInfer files which may contain spaces
        path_matches = list(re.finditer(r'\S+\.(gguf|ninfer)', command_str, re.IGNORECASE))
        if path_matches:
            # Find the last match, which is most likely the main model path
            last_match = path_matches[-1]
            split_point = last_match.end()
            prefix_str = command_str[:split_point]
            suffix_str = command_str[split_point:]

        prefix_tokens = _parse_args(prefix_str)
        suffix_tokens = _parse_args(suffix_str)

        all_tokens = prefix_tokens + suffix_tokens
        if not all_tokens:
            return []

        # The first token is always the executable
        executable = all_tokens[0]
        parts.append(Parameter("Executable", executable))

        # Detect if this is an NInfer command
        is_ninfer = 'ninfer-serve' in executable.lower()

        i = 1
        if is_ninfer and i < len(all_tokens):
            # For NInfer, the first token after executable is the positional model path
            parts.append(Parameter('-m', all_tokens[i]))
            i += 1

        while i < len(all_tokens):
            token = all_tokens[i]
            if token.startswith('-'):
                # Check if the next token is a value or another flag
                if (i + 1 < len(all_tokens)) and not all_tokens[i + 1].startswith('-'):
                    parts.append(Parameter(token, all_tokens[i + 1]))
                    i += 2  # Consumed both key and value
                else:
                    parts.append(Parameter(token, None))  # It's a flag
                    i += 1
            else:
                # This case handles values that might not have been parsed correctly, ignore them
                i += 1

        return parts

    @staticmethod
    def build(parameters: list[Parameter], is_ninfer: bool = False) -> str:
        """
        Reconstructs a command string from a list of Parameter tuples.
        
        For NInfer models, the Model Path (-m) is placed positionally (right after
        the executable, no flag prefix). For Llama.cpp models, -m is used normally.
        """
        args_list = []
        executable = ""
        positional_model_path = None
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
            remaining_params.append(param)

        # Build the args list
        if executable:
            args_list.append(executable)
        
        # For NInfer, model path comes positionally right after executable
        if is_ninfer and positional_model_path is not None:
            args_list.append(positional_model_path)
        
        for param in remaining_params:
            args_list.append(param.key)
            if param.value is not None:
                args_list.append(param.value)

        if not args_list:
            return ""
        if IS_WINDOWS:
            return subprocess.list2cmdline(args_list)
        return shlex.join(args_list)