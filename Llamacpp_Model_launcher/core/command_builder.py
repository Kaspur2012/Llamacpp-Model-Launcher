# core/command_builder.py

import shlex
import re
import subprocess
from collections import namedtuple

Parameter = namedtuple('Parameter', ['key', 'value'])


class CommandBuilder:
    """Parses command strings into structured data and builds them back."""

    @staticmethod
    def parse(command_str: str) -> list[Parameter]:
        """
        Parses a full command string into a list of Parameter tuples.
        Handles complex paths by identifying the .gguf file.
        """
        if not command_str:
            return []

        parts = []
        prefix_str, suffix_str = "", command_str

        # Special handling for Windows paths in GGUF files which may contain spaces
        # and break shlex parsing if not handled separately.
        path_matches = list(re.finditer(r'\S+\.gguf', command_str, re.IGNORECASE))
        if path_matches:
            # Find the last match, which is most likely the main model path
            last_match = path_matches[-1]
            split_point = last_match.end()
            prefix_str = command_str[:split_point]
            suffix_str = command_str[split_point:]

        try:
            # Use windows-style parsing for the part that might contain unquoted paths
            prefix_tokens = shlex.split(prefix_str, posix=False)
        except ValueError:
            prefix_tokens = prefix_str.split()  # Fallback for safety

        try:
            # Use POSIX-style parsing for regular flags and arguments
            suffix_tokens = shlex.split(suffix_str, posix=True)
        except ValueError:
            suffix_tokens = suffix_str.split()  # Fallback

        all_tokens = prefix_tokens + suffix_tokens
        if not all_tokens:
            return []

        # The first token is always the executable
        parts.append(Parameter("Executable", all_tokens[0]))

        i = 1
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
    def build(parameters: list[Parameter]) -> str:
        """
        Reconstructs a command string from a list of Parameter tuples.
        """
        args_list = []
        executable = ""
        for param in parameters:
            if param.key == "Executable":
                executable = param.value
                continue

            args_list.append(param.key)
            if param.value is not None:
                args_list.append(param.value)

        # Prepend the executable to the argument list for proper command line generation
        if executable:
            args_list.insert(0, executable)

        return subprocess.list2cmdline(args_list) if args_list else ""