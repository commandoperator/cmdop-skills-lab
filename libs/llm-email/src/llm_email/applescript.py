"""AppleScript helpers for macOS Mail.app integration."""

import subprocess


def escape_applescript(text: str) -> str:
    """Escape a string for embedding in AppleScript double-quoted literals."""
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\r")
    text = text.replace("\t", "\\t")
    return text


def run_osascript(script: str, timeout: int = 30) -> tuple[bool, str]:
    """Execute an AppleScript and return (success, output)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "osascript timed out"
    except FileNotFoundError:
        return False, "osascript not found — macOS required"


def split_addrs(s: str) -> list[str]:
    """Split comma-separated email addresses, filtering blanks."""
    if not s:
        return []
    return [a.strip() for a in s.split(",") if a.strip()]
