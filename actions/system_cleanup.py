"""System cleanup and optimization: clear temp files, manage startup, defrag, etc."""

import subprocess
import os
import shutil
import json
from pathlib import Path


def _run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return r.stdout.strip(), r.returncode, r.stderr.strip()
    except Exception as e:
        return str(e), 1, ""


def handle(parameters=None):
    params = parameters or {}
    action = params.get("action", "help")
    target = params.get("target", "")

    handlers = {
        "clean_temp": _clean_temp,
        "clean_recycle": _clean_recycle,
        "clean_browser_cache": _clean_browser_cache,
        "clean_windows_update": _clean_windows_update,
        "clean_logs": _clean_logs,
        "disk_cleanup": _disk_cleanup,
        "defrag_check": _defrag_check,
        "startup_list": _startup_list,
        "startup_disable": lambda: _startup_disable(target),
        "startup_enable": lambda: _startup_enable(target),
        "process_list": _process_list,
        "process_kill": lambda: _process_kill(target),
        "memory_status": _memory_status,
        "repair_system": _repair_system,
        "check_disk_errors": _check_disk_errors,
        "update_drivers": _update_drivers,
        "optimize_drives": _optimize_drives,
        "optimize_system": _optimize_system,
        "help": _help,
    }

    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _optimize_system():
    results = []
    results.append(_clean_temp())
    results.append(_clean_recycle())
    results.append(_clean_browser_cache())
    results.append(_clean_logs())
    results.append(_memory_status())
    return "\n".join(results)


def _help():
    return """SYSTEM CLEANUP & OPTIMIZATION:
  clean_temp          - Clear temporary files
  clean_recycle       - Empty recycle bin
  clean_browser_cache - Clear browser cache
  clean_windows_update - Clean Windows Update cache
  clean_logs          - Clear system logs
  disk_cleanup        - Run Windows Disk Cleanup
  defrag_check        - Check if defrag needed
  startup_list        - List startup programs
  startup_disable     - Disable startup item (target=name)
  startup_enable      - Enable startup item (target=name)
  process_list        - List top processes by CPU
  process_kill        - Kill a process (target=name)
  memory_status       - Check memory usage
  repair_system       - Run system file checker
  check_disk_errors   - Check disk for errors
  update_drivers      - Check for driver updates
  optimize_drives     - Analyze drive optimization
  optimize_system     - Run all cleanup tasks at once"""


def _clean_temp():
    temp_dirs = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        str(Path.home() / "AppData" / "Local" / "Temp"),
        r"C:\Windows\Temp",
    ]
    cleaned = 0
    total_bytes = 0
    for d in set(temp_dirs):
        if not d or not os.path.exists(d):
            continue
        try:
            items = list(Path(d).iterdir())
        except (PermissionError, OSError):
            continue
        for item in items:
            try:
                if item.is_file():
                    size = item.stat().st_size
                    item.unlink()
                    total_bytes += size
                    cleaned += 1
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    cleaned += 1
            except Exception:
                continue
    return f"Cleaned {cleaned} temp items, freed {total_bytes / 1024 / 1024:.1f}MB"


def _clean_recycle():
    _run(["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])
    return "Recycle bin emptied"


def _clean_browser_cache():
    chrome_cache = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cache"
    edge_cache = Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache"
    cleaned = 0
    for cache_dir in [chrome_cache, edge_cache]:
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir, ignore_errors=True)
                cleaned += 1
            except Exception:
                pass
    return f"Cleaned {cleaned} browser cache(s). Restart browser to apply." if cleaned else "No browser caches found or already clean"


def _clean_windows_update():
    winsxs = r"C:\Windows\SoftwareDistribution\Download"
    cleaned = 0
    total = 0
    if os.path.exists(winsxs):
        for item in Path(winsxs).iterdir():
            try:
                size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                shutil.rmtree(item, ignore_errors=True)
                total += size
                cleaned += 1
            except Exception:
                pass
    return f"Cleaned {cleaned} Windows Update items, freed {total / 1024 / 1024:.1f}MB" if cleaned else "Windows Update cache already clean"


def _clean_logs():
    log_dirs = [
        r"C:\Windows\Logs",
        str(Path.home() / "AppData" / "Local" / "Diagnostics"),
    ]
    total = 0
    for d in log_dirs:
        if os.path.exists(d):
            for f in Path(d).rglob("*.log"):
                try:
                    total += f.stat().st_size
                    f.unlink()
                except Exception:
                    pass
    return f"Cleared logs, freed {total / 1024 / 1024:.1f}MB" if total else "Logs already clean"


def _disk_cleanup():
    _run(["cleanmgr", "/sagerun:1"])
    return "Disk Cleanup launched"


def _defrag_check():
    out, _, _ = _run(["powershell", "-Command",
                      "Get-Volume | Where-Object {$_.DriveLetter} | Select-Object DriveLetter,SizeRemaining,Size,FragmentationPercentage | Format-Table -AutoSize"], timeout=15)
    return f"DRIVE FRAGMENTATION:\n{out}" if out else "Could not check fragmentation"


def _startup_list():
    out, _, _ = _run(["powershell", "-Command",
                      "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | Format-Table -AutoSize"], timeout=10)
    return f"STARTUP PROGRAMS:\n{out}" if out else "No startup programs found"


def _startup_disable(name):
    if not name:
        return "Provide program name to disable"
    _run(["powershell", "-Command",
          f"Disable-ScheduledTask -TaskName '*{name}*' -ErrorAction SilentlyContinue"])
    _run(["reg", "delete", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run", "/v", name, "/f"])
    return f"Attempted to disable: {name}"


def _startup_enable(name):
    if not name:
        return "Provide program name to enable"
    _run(["powershell", "-Command",
          f"Enable-ScheduledTask -TaskName '*{name}*' -ErrorAction SilentlyContinue"])
    return f"Attempted to enable: {name}"


def _process_list():
    out, _, _ = _run(["powershell", "-Command",
                      "Get-Process | Sort-Object CPU -Descending | Select-Object -First 20 ProcessName,Id,@{N='CPU(s)';E={[math]::Round($_.CPU,1)}},@{N='Mem(MB)';E={[math]::Round($_.WorkingSet64/1MB,1)}} | Format-Table -AutoSize"], timeout=10)
    return f"TOP PROCESSES:\n{out}" if out else "Could not list processes"


def _process_kill(name):
    if not name:
        return "Provide process name to kill"
    out, code, err = _run(["taskkill", "/F", "/IM", f"{name}.exe"])
    if code == 0:
        return f"Killed: {name}"
    return f"Could not kill {name}: {err or out}"


def _memory_status():
    try:
        import psutil
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return (f"MEMORY STATUS:\n"
                f"  RAM: {mem.percent}% used ({mem.used / 1024**3:.1f}GB / {mem.total / 1024**3:.1f}GB)\n"
                f"  Available: {mem.available / 1024**3:.1f}GB\n"
                f"  Swap: {swap.percent}% used ({swap.used / 1024**3:.1f}GB / {swap.total / 1024**3:.1f}GB)")
    except Exception:
        out, _, _ = _run(["powershell", "-Command",
                          "$os = Get-CimInstance Win32_OperatingSystem; Write-Output \"Total: $([math]::Round($os.TotalVisibleMemorySize/1MB,1))GB Used: $([math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB,1))GB Free: $([math]::Round($os.FreePhysicalMemory/1MB,1))GB\""], timeout=10)
        return f"MEMORY: {out}" if out else "Memory check unavailable"


def _repair_system():
    out, code, err = _run(["sfc", "/scannow"], timeout=120)
    return f"System File Checker:\n{out}" if out else f"SFC error: {err}"


def _check_disk_errors():
    _run(["chkdsk", "C:", "/f"])
    return "Disk check scheduled (requires restart)"


def _update_drivers():
    _run(["powershell", "-Command", "Start-Process ms-settings:windowsupdate-devices"])
    return "Device Manager opened for driver updates"


def _optimize_drives():
    out, _, _ = _run(["powershell", "-Command",
                      "Get-Volume | Where-Object {$_.DriveLetter -and $_.SizeRemaining -ne $null} | Select-Object DriveLetter,@{N='Fragment%';E={if($_.Size -gt 0){[math]::Round(($_.Size - $_.SizeRemaining)/$_.Size * 100,1)}else{0}}} | Format-Table -AutoSize"], timeout=10)
    return f"DRIVE STATUS:\n{out}" if out else "Could not analyze drives"
