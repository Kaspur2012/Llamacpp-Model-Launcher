# core/platform_utils.py

import os
import platform
import re
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


def is_strata_command(command_str: str) -> bool:
    """Check if a command string launches the Strata serve wrapper
    (python ...\\serve\\server.py --engine strata --config <json>) or the
    Strata engine directly."""
    if not command_str:
        return False
    lowered = command_str.lower()
    return ('serve\\server.py' in lowered or 'serve/server.py' in lowered
            or 'strata.exe' in lowered)


def is_strata_params(params) -> bool:
    """Check if a list of Parameter tuples represents a Strata command.

    The 'Serve Script' key is the marker set by CommandBuilder.parse() for the
    positional serve\\server.py argument of the Strata wrapper command.
    """
    for param in params:
        if param.key == "Serve Script":
            return True
        if param.key == "Executable" and param.value and 'strata.exe' in param.value.lower():
            return True
    return False


def port_in_use(port, host: str = '127.0.0.1', timeout: float = 0.5) -> bool:
    """True when something is already listening on host:port.

    A plain TCP connect test: connecting succeeds only against a live
    listener, so TIME_WAIT sockets and free ports both report False.
    """
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def enable_large_page_privileges(privileges=('SeLockMemoryPrivilege',
                                             'SeIncreaseWorkingSetPrivilege')) -> dict:
    """Enable Windows privileges in the current process token (no-op elsewhere).

    Strata uses 2 MB large pages, which need SeLockMemoryPrivilege. The
    privilege is disabled by default even when assigned, so it must be enabled
    in the token before the engine inherits it. This succeeds WITHOUT elevation
    once the account has the rights assigned (grant-large-pages.ps1, run once
    as admin, then log off/on). Returns {privilege: bool}; a False result just
    means Strata falls back to 4 KB pages (slower, still works).
    """
    if not IS_WINDOWS:
        return {}
    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    TOKEN_ADJUST_PRIVILEGES = 0x0020
    TOKEN_QUERY = 0x0008
    SE_PRIVILEGE_ENABLED = 0x0002

    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [("PrivilegeCount", wintypes.DWORD),
                    ("Privileges", LUID_AND_ATTRIBUTES)]

    result = {}
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return {p: False for p in privileges}
    try:
        for priv in privileges:
            luid = LUID()
            if not advapi32.LookupPrivilegeValueW(None, priv, ctypes.byref(luid)):
                result[priv] = False
                continue
            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges.Luid = luid
            tp.Privileges.Attributes = SE_PRIVILEGE_ENABLED
            advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp),
                                           ctypes.sizeof(tp), None, None)
            # AdjustTokenPrivileges returns TRUE even when the privilege is not
            # assigned to the token; ERROR_SUCCESS is the real success signal.
            result[priv] = (ctypes.get_last_error() == 0)
    finally:
        kernel32.CloseHandle(token)
    return result


def _find_listening_pids(port):
    """PIDs of processes LISTENing on the given TCP port (best effort)."""
    pids = set()
    try:
        import psutil
        for conn in psutil.net_connections(kind='inet'):
            if (conn.status == psutil.CONN_LISTEN and conn.laddr
                    and conn.laddr.port == port and conn.pid):
                pids.add(conn.pid)
        return pids
    except Exception:
        pass
    # Fallback without psutil: parse netstat -ano (Windows) / netstat -tlnp (POSIX)
    try:
        if IS_WINDOWS:
            out = subprocess.run(f'netstat -ano -p tcp', capture_output=True, text=True,
                                 **get_subprocess_kwargs()).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0].upper() == 'TCP' and parts[3].upper() == 'LISTENING':
                    if parts[1].rsplit(':', 1)[-1] == str(port):
                        try:
                            pids.add(int(parts[4]))
                        except ValueError:
                            pass
        else:
            out = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 7 and parts[3].rsplit(':', 1)[-1] == str(port):
                    pid = parts[6].split('/')[0]
                    if pid.isdigit():
                        pids.add(int(pid))
    except Exception:
        pass
    return pids


def strata_full_stop(port, log=None, pump=None, timeout_s=20.0) -> bool:
    """Replicate STOP-STRATA.bat after the wrapper's process tree was killed.

    The serve wrapper auto-restarts its engine (restart(tries=3)), so killing
    only the engine leaves traces; the full stop sweeps any strata.exe /
    strata-vision.exe leftovers and then waits for the port to stop listening,
    killing holders that are clearly Strata/python processes and warning about
    unrelated ones. Returns True once the port is free.

    log/pump are optional callbacks: log(str) for progress lines, pump() to
    keep a GUI event loop responsive during the wait.
    """
    import time
    if log is None:
        log = lambda msg: None
    if pump is None:
        pump = lambda: None

    # 1. Sweep Strata engine processes (leftovers from this or a previous run).
    if IS_WINDOWS:
        for image in ('strata.exe', 'strata-vision.exe'):
            subprocess.run(f'taskkill /F /IM {image}', shell=True, capture_output=True,
                           **get_subprocess_kwargs())
    else:
        for name in ('strata', 'strata-vision'):
            subprocess.run(['pkill', '-9', '-x', name], capture_output=True)
    time.sleep(2.0)
    pump()

    # 2. Wait for the port to free; kill Strata-ish holders, warn about others.
    deadline = time.monotonic() + timeout_s
    warned_unrelated = False
    while True:
        if not port_in_use(port):
            return True
        if time.monotonic() >= deadline:
            break
        for pid in _find_listening_pids(port):
            name = ''
            try:
                import psutil
                name = psutil.Process(pid).name()
            except Exception:
                try:
                    if IS_WINDOWS:
                        name = subprocess.run(
                            f'tasklist /FI "PID eq {pid}" /NH', shell=True,
                            capture_output=True, text=True,
                            **get_subprocess_kwargs()).stdout.strip()
                except Exception:
                    pass
            if not name or re.search(r'(?i)python|strata', name):
                log(f"[STRATA] Port {port} still held by PID {pid} ({name or 'unknown'}) — killing it.")
                kill_process_tree(pid)
            elif not warned_unrelated:
                log(f"[STRATA] WARNING: port {port} is held by an unrelated process "
                    f"'{name}' (PID {pid}) — not killing it.")
                warned_unrelated = True
        time.sleep(2.0)
        pump()
    return not port_in_use(port)


def regenerate_greedy_config(python_exe: str, config_path: str):
    """Run Strata's make-greedy-config.py from the config's own folder.

    Mirrors run-iq3_s_greedy.bat: the greedy JSON is regenerated from the live
    strata-iq3_s.json at every greedy launch, so tuning added to the live
    config carries over automatically. Returns (ok, message).
    """
    import os
    cfg_dir = os.path.dirname(os.path.abspath(config_path))
    script = os.path.join(cfg_dir, 'make-greedy-config.py')
    if not os.path.exists(script):
        return False, f"make-greedy-config.py not found next to {config_path}"
    try:
        proc = subprocess.run([python_exe, script], capture_output=True,
                              text=True, cwd=cfg_dir, **get_subprocess_kwargs())
    except OSError as e:
        return False, f"Could not run make-greedy-config.py: {e}"
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or '').strip()
        return False, f"make-greedy-config.py failed (exit {proc.returncode}): {detail}"
    return True, (proc.stdout or '').strip()


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
