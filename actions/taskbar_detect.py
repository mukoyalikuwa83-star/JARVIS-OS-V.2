"""Detect taskbar pinned apps and running apps on Windows."""

import subprocess
import os


def get_pinned_taskbar_apps() -> list[str]:
    """Return list of pinned taskbar app names on Windows."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-StartApps).Name"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except Exception:
        pass
    return []


def get_running_apps() -> list[str]:
    """Return list of currently running application window titles."""
    try:
        import pygetwindow as gw
        return [w.title for w in gw.getAllWindows() if w.title and w.title.strip()]
    except ImportError:
        pass
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object -ExpandProperty MainWindowTitle"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except Exception:
        pass
    return []


def is_app_running(app_name: str) -> bool:
    """Check if an app is currently running."""
    running = get_running_apps()
    name_lower = app_name.lower()
    return any(name_lower in title.lower() for title in running)


def focus_app(app_name: str) -> bool:
    """Try to focus/bring an already-running app to foreground."""
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(app_name)
        if not windows:
            windows = [w for w in gw.getAllWindows()
                       if app_name.lower() in w.title.lower()]
        if windows:
            w = windows[0]
            if w.isMinimized:
                w.restore()
            w.activate()
            return True
    except Exception:
        pass
    return False
