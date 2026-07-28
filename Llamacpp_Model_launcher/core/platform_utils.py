# core/platform_utils.py

import os
import platform
import signal
import subprocess

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"


def get_executable_name():
    """Returns the llama-server executable name for the current platform."""
    return "llama-server.exe" if IS_WINDOWS else "llama-server"


def get_default_model_path_example():
    """Returns a platform-appropriate example model path."""
    if IS_WINDOWS:
        return r"D:\path_to_your_model.gguf"
    return "/path/to/your_model.gguf"


def get_subprocess_kwargs():
    """Returns platform-specific kwargs for subprocess calls (e.g., CREATE_NO_WINDOW on Windows)."""
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def is_ninfer_command(command_str: str) -> bool:
    """Check if a command string uses the NInfer inference engine."""
    if not command_str:
        return False
    return 'ninfer-serve' in command_str.lower()


def is_ninfer_params(params) -> bool:
    """Check if a list of Parameter tuples represents an NInfer command."""
    for param in params:
        if param.key == "Executable" and 'ninfer-serve' in param.value.lower():
            return True
    return False


def kill_process_tree(pid):
    """Terminates a process and its children. Platform-specific implementation."""
    if IS_WINDOWS:
        subprocess.run(
            f'taskkill /F /T /PID {pid}',
            shell=True, capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
