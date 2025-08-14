"""
ezenviron - A Python module for managing Windows environment variables safely.

This module provides CRUD operations for Windows user environment variables,
particularly useful for API development where sensitive configuration needs
to be managed securely.

Windows user environment variable utilities.

Functions:
- get(key): read from os.environ
- set(key, value): set a User env var via PowerShell (subprocess) and update os.environ
- load_dotenv(path): load key/value pairs from a .env file using set()

Notes:
- Requires Windows. Uses PowerShell to persist values (User scope) and broadcasts
  WM_SETTINGCHANGE so other processes may learn about the update.
"""

from __future__ import annotations

import base64
import os
import platform
import subprocess
import sys
import re
import winreg
from typing import Dict, Optional, Tuple

__version__ = "0.1.0"
__author__ = "ltanedo"
__email__ = "lloydtan@buffalo.edu"

__all__ = ["get", "set", "load_dotenv", "reload", "get_username"]


def _ensure_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("environ.py only supports Windows for persistent user env vars")


def _to_ps_encoded_command(script: str) -> str:
    """Return Base64-encoded UTF-16LE string for PowerShell -EncodedCommand."""
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def _run_powershell(script: str) -> subprocess.CompletedProcess:
    """Run a PowerShell script using -EncodedCommand. Tries Windows PowerShell then pwsh.

    Raises subprocess.CalledProcessError on failure.
    """
    encoded = _to_ps_encoded_command(script)
    candidates = [
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        ["pwsh", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
    ]
    last_err: Optional[Exception] = None
    for cmd in candidates:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=True)
        except FileNotFoundError as e:
            last_err = e
            continue
        except subprocess.CalledProcessError as e:
            # Propagate the first tool that exists (powershell or pwsh)
            last_err = e
            break
    if isinstance(last_err, subprocess.CalledProcessError):
        raise last_err
    raise FileNotFoundError("Neither 'powershell' nor 'pwsh' was found on PATH")


def _broadcast_environment_change_ps() -> str:
    """PowerShell snippet to broadcast WM_SETTINGCHANGE for 'Environment'."""
    return (
        "$sig = @'\n"
        "using System;\n"
        "using System.Runtime.InteropServices;\n"
        "public static class NativeMethods {\n"
        "  [DllImport(\"user32.dll\", SetLastError=true, CharSet=CharSet.Auto)]\n"
        "  public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);\n"
        "}\n"
        "'@;\n"
        "Add-Type -TypeDefinition $sig -ErrorAction SilentlyContinue | Out-Null;\n"
        "[UIntPtr]$out = [UIntPtr]::Zero;\n"
        "[void][NativeMethods]::SendMessageTimeout([IntPtr]0xffff, 0x1A, [UIntPtr]0, 'Environment', 2, 5000, [ref]$out);\n"
    )


def get(key: str, power_shell: bool = False) -> Optional[str]:
    """Get a single environment variable using os.environ."""
    if power_shell:
        return subprocess.run([
                "powershell",
                "-NoProfile",
                "-Command","[Environment]::GetEnvironmentVariable('MY_VAR','User')"
            ],
            capture_output=True, text=True
        ).stdout.strip()

    return os.environ.get(key)




def get_username(prefix: str = "", postfix: str = "") -> str:
    """Retrieve the current Windows username via PowerShell.

    Attempts to read `$env:USERNAME` using a PowerShell subprocess.
    If that yields no result, falls back to an alternate PowerShell expression
    and finally to common Python methods.

    Args:
        prefix: Text to prepend to the username.
        postfix: Text to append to the username.

    Returns:
        The username with optional prefix and postfix applied.
    """
    _ensure_windows()

    username: str = ""

    # Primary approach: PowerShell environment variable
    try:
        result = _run_powershell("$env:USERNAME")
        username = (result.stdout or "").strip()
    except Exception:
        # We'll try fallbacks below
        pass

    # Fallback 1: .NET API via PowerShell
    if not username:
        try:
            alt = _run_powershell("[System.Environment]::UserName")
            username = (alt.stdout or "").strip()
        except Exception:
            pass

    # Fallback 2: Python environment / getpass
    if not username:
        username = os.environ.get("USERNAME", "")
        if not username:
            try:
                import getpass
                username = getpass.getuser()
            except Exception:
                username = ""

    if not username:
        raise RuntimeError("Unable to determine the current Windows username")

    return f"{prefix}{username}{postfix}"

def set(key: str, value: str, auto_reload: bool = True) -> bool:
    """Set a single user environment variable.

    - First tries PowerShell (User scope) for persistence
    - Falls back to direct registry write (HKCU\\Environment) if PowerShell is unavailable
    - Always updates os.environ for this process
    - Optionally reloads all environment variables afterwards
    """
    _ensure_windows()

    # Escape single quotes for PowerShell single-quoted literals
    key_ps = key.replace("'", "''")
    value_ps = value.replace("'", "''")

    ps_script = (
        f"[Environment]::SetEnvironmentVariable('{key_ps}', '{value_ps}', 'User');"
    )

    def _post_set_reload():
        if auto_reload:
            try:
                updated = reload()
                if updated and len(updated) > 1:  # More than just the variable we set
                    other_updates = {k: v for k, v in updated.items() if k != key}
                    if other_updates:
                        sys.stderr.write(
                            f"Info: Also updated {len(other_updates)} other environment variables during reload\n"
                        )
            except Exception as reload_err:
                # Don't fail the set operation if reload fails
                sys.stderr.write(
                    f"Warning: Failed to reload environment after setting {key}: {reload_err}\n"
                )

    try:
        # Try PowerShell path first
        _run_powershell(ps_script)
        os.environ[key] = value
        _post_set_reload()
        return True
    except FileNotFoundError:
        # PowerShell not found; fall back to direct registry write for User scope
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Environment") as hkey:
                winreg.SetValueEx(hkey, key, 0, winreg.REG_SZ, value)
            os.environ[key] = value
            _post_set_reload()
            return True
        except Exception as reg_err:
            sys.stderr.write(
                f"Error setting environment variable {key!r} via registry: {reg_err}\n"
            )
            return False
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            f"Error setting environment variable {key!r}: exit {e.returncode}\nSTDERR: {e.stderr}\n"
        )
        return False
    except Exception as e:
        sys.stderr.write(f"Unexpected error setting environment variable {key!r}: {e}\n")
        return False


def reload() -> Dict[str, str]:
    """Reload all environment variables from the Windows registry (User + Machine).

    - Reads from HKCU\\Environment and HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment
    - User values override Machine values when keys collide (matching prior behavior)
    - Updates os.environ for keys that are new or changed in the registry
    - Special-case expansion of %TEMP% and %TMP% to ensure they point to real directories
    - Returns a dict of {key: value} for variables that were updated in this process
    """
    _ensure_windows()

    def _read_registry_env(root, subkey) -> Dict[str, str]:
        values: Dict[str, str] = {}
        try:
            with winreg.OpenKey(root, subkey) as hkey:
                index = 0
                while True:
                    try:
                        name, data, _typ = winreg.EnumValue(hkey, index)
                        # Convert bytes to string if needed; store textual representation
                        if isinstance(data, bytes):
                            try:
                                data = data.decode("utf-16le")
                            except Exception:
                                data = data.decode(errors="ignore")
                        values[str(name)] = str(data)
                        index += 1
                    except OSError:
                        break
        except FileNotFoundError:
            pass
        return values

    def _expand_percent_vars(s: str, mapping: Dict[str, str]) -> str:
        # Expand %NAME% patterns using provided mapping (case-insensitive keys)
        def repl(m):
            name = m.group(1)
            # Windows env names are case-insensitive
            for k, v in mapping.items():
                if k.upper() == name.upper():
                    return v
            return m.group(0)
        return re.sub(r"%([A-Za-z0-9_]+)%", repl, s)

    updated_vars: Dict[str, str] = {}

    current_env = dict(os.environ)

    machine_env = _read_registry_env(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment",
    )
    user_env = _read_registry_env(winreg.HKEY_CURRENT_USER, r"Environment")

    merged: Dict[str, str] = {}
    merged.update(machine_env)
    merged.update(user_env)

    # Expand TEMP/TMP if they contain %...% so that Playwright gets absolute paths
    for var in ("TEMP", "TMP"):
        val = merged.get(var)
        if isinstance(val, str):
            # First, try process-level expansion
            expanded = os.path.expandvars(val)
            # Then, expand using explicit mapping from registry values
            expanded = _expand_percent_vars(expanded, {**machine_env, **user_env, **current_env})
            merged[var] = expanded

    for key, value in merged.items():
        if key not in current_env or current_env.get(key) != value:
            os.environ[key] = value
            updated_vars[key] = value

    return updated_vars


def load_dotenv(path: str) -> Dict[str, bool]:
    """Load variables from a .env file and set each using set().

    - Lines starting with '#' are comments and ignored
    - Leading 'export ' is supported and ignored
    - Keys are case-sensitive on Windows storage, though lookup via os.environ is case-insensitive
    - Values may be quoted with single or double quotes; surrounding quotes are stripped
    - Whitespace around keys and values is trimmed

    Returns a dict of {key: success_boolean} for each assignment processed.
    """
    results: Dict[str, bool] = {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.lower().startswith("export "):
                    line = line[7:].lstrip()
                if "=" not in line:
                    sys.stderr.write(f"Warning: Skipping invalid .env line {line_no}: {raw}")
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if not key:
                    sys.stderr.write(f"Warning: Skipping empty key at line {line_no}\n")
                    continue
                ok = set(key, val)
                results[key] = ok
    except FileNotFoundError:
        sys.stderr.write(f"Error: .env file not found at {path}\n")
    except Exception as e:
        sys.stderr.write(f"Error reading .env file {path}: {e}\n")

    return results


def main(argv: Optional[list[str]] = None) -> None:
    """Entry point that exposes all public functions in this module as CLI commands.

    Examples:
      - python environ.py --help
      - python environ.py get --key=PATH
      - python environ.py set --key=FOO --value=bar
    """
    # Delay import to avoid circular issues and keep startup fast
    try:
        from .cli import import_cli
        # Delegate to the CLI generator, explicitly passing this module
        import_cli(module=sys.modules[__name__], argv=argv)
    except ImportError:
        print("CLI functionality not available. Install required dependencies.")
        sys.exit(1)


if __name__ == "__main__":
    main()
