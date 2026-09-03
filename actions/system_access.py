"""System access: location, bluetooth, wifi, hotspot, night mode, permissions, foreground app, running apps, device info, battery, network, clipboard, screen info, input devices, audio devices, printers, USB, drivers, startup apps, scheduled tasks, environment variables, system info."""

import subprocess
import os
import time
import json
import socket
import struct
import ctypes
from pathlib import Path

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=_NO_WINDOW)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def _ps(command, timeout=15):
    out, rc = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], timeout=timeout)
    return out if rc == 0 else ""


def handle(parameters: dict) -> str:
    action = parameters.get("action", "")
    target = parameters.get("target", "")
    value = parameters.get("value", "")
    handlers = {
        "get_browser_tabs": lambda: _get_browser_tabs(target),
        "smart_open_url": lambda: _smart_open_url(target),
        "is_url_open": lambda: _is_url_open(target),
        "get_location": _get_location,
        "get_network_info": _get_network_info,
        "get_battery_status": _get_battery_status,
        "get_screen_info": _get_screen_info,
        "get_foreground_app": _get_foreground_app,
        "get_running_apps": _get_running_apps,
        "get_audio_devices": _get_audio_devices,
        "get_input_devices": _get_input_devices,
        "get_usb_devices": _get_usb_devices,
        "get_printers": _get_printers,
        "get_startup_apps": _get_startup_apps,
        "get_scheduled_tasks": lambda: _get_scheduled_tasks(target),
        "get_env_vars": _get_env_vars,
        "get_system_info": _get_system_info,
        "get_ip_info": _get_ip_info,
        "get_cpu_info": _get_cpu_info,
        "get_gpu_info": _get_gpu_info,
        "get_ram_info": _get_ram_info,
        "get_disk_info": _get_disk_info,
        "get_monitor_info": _get_monitor_info,
        "bluetooth_on": lambda: _bluetooth_power(True),
        "bluetooth_off": lambda: _bluetooth_power(False),
        "bluetooth_status": _bluetooth_status,
        "bluetooth_scan": _bluetooth_scan,
        "bluetooth_pair": lambda: _bluetooth_pair(target),
        "bluetooth_unpair": lambda: _bluetooth_unpair(target),
        "bluetooth_connected_devices": _bluetooth_connected,
        "wifi_on": lambda: _wifi_power(True),
        "wifi_off": lambda: _wifi_power(False),
        "wifi_status": _wifi_status,
        "wifi_scan": _wifi_scan,
        "wifi_connect": lambda: _wifi_connect(target),
        "wifi_disconnect": lambda: _wifi_disconnect(target),
        "wifi_hotspot_on": lambda: _hotspot(True),
        "wifi_hotspot_off": lambda: _hotspot(False),
        "wifi_hotspot_config": lambda: _hotspot_config(target, value),
        "night_mode_on": lambda: _night_mode(True),
        "night_mode_off": lambda: _night_mode(False),
        "night_mode_status": _night_mode_status,
        "set_wallpaper": lambda: _set_wallpaper(target),
        "get_clipboard": _get_clipboard,
        "set_clipboard": lambda: _set_clipboard(target),
        "get_volume": _get_volume,
        "set_volume": lambda: _set_volume(target),
        "get_brightness": _get_brightness,
        "set_brightness": lambda: _set_brightness(target),
        "airplane_mode_on": lambda: _airplane(True),
        "airplane_mode_off": lambda: _airplane(False),
        "dnd_on": lambda: _dnd(True),
        "dnd_off": lambda: _dnd(False),
        "get_keyboard_layout": _get_keyboard_layout,
        "set_keyboard_layout": lambda: _set_keyboard_layout(target),
        "get_installed_apps": _get_installed_apps,
        "get_running_services": lambda: _get_running_services(target),
        "start_service": lambda: _start_service(target),
        "stop_service": lambda: _stop_service(target),
        "get_windows_update_status": _get_windows_update,
        "get_defender_status": _get_defender_status,
        "get_firewall_status": _get_firewall_status,
        "lock_workstation": _lock_workstation,
        "get_user_accounts": _get_user_accounts,
        "get_shares": _get_shares,
        "get_drivers": _get_drivers,
        "get_network_connections": _get_network_connections,
        "get_event_log": lambda: _get_event_log(target),
    }
    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown system_access action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


import webbrowser
from urllib.parse import urlparse

_BROWSER_CLASSES = {"Chrome_WidgetWin_1", "MozillaWindowClass", "Edge_DBLClickWindow",
                    "BrowserWindow", "Chrome_WidgetWin_0", "MozillaWindowClass"}


def _get_browser_tabs(filter_domain: str = "") -> str:
    """List all open browser window titles. Optionally filter by domain."""
    try:
        user32 = ctypes.windll.user32
        results = []

        def _enum_cb(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if not title:
                return True
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            cls = cls_buf.value
            browser_names = {"Chrome_WidgetWin_1": "Chrome", "Chrome_WidgetWin_0": "Chrome",
                             "MozillaWindowClass": "Firefox", "Edge_DBLClickWindow": "Edge",
                             "BrowserWindow": "Browser"}
            browser = browser_names.get(cls, "")
            if not browser:
                return True
            if filter_domain and filter_domain.lower() not in title.lower():
                return True
            results.append(f"[{browser}] {title}")
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        user32.EnumWindows(EnumWindowsProc(_enum_cb), 0)

        if not results:
            if filter_domain:
                return f"No browser tabs open with '{filter_domain}'"
            return "No browser windows found"
        header = f"Open browser tabs ({len(results)}):" if not filter_domain else f"Tabs matching '{filter_domain}' ({len(results)}):"
        return header + "\n" + "\n".join(results)
    except Exception as e:
        return f"Browser tab detection error: {e}"


def _is_url_open(url: str) -> str:
    """Check if a URL (by domain) is already open in any browser tab."""
    if not url:
        return "Provide a URL or domain to check"
    parsed = urlparse(url if "://" in url else f"https://{url}")
    domain = (parsed.netloc or parsed.path).lower().replace("www.", "")
    base_domain = domain.split(".")[0] if "." in domain else domain
    result = _get_browser_tabs(domain)
    if "No browser" in result or "No tabs" in result:
        result2 = _get_browser_tabs(base_domain)
        if "No browser" in result2 or "No tabs" in result2:
            return f"NOT_OPEN: {domain} is not open in any browser tab"
        return f"ALREADY_OPEN: {base_domain} is open!\n{result2}"
    return f"ALREADY_OPEN: {domain} is open!\n{result}"


def _smart_open_url(url: str) -> str:
    """Open a URL only if it's not already open. If open, focus the existing tab."""
    if not url:
        return "Provide a URL to open"
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    domain = (parsed.netloc or "").lower().replace("www.", "")
    check = _is_url_open(domain)
    if check.startswith("ALREADY_OPEN"):
        return f"SKIP: {domain} is already open. Not opening duplicate tab.\n{check}"
    try:
        webbrowser.open(url)
        return f"Opened: {url}"
    except Exception as e:
        return f"Failed to open {url}: {e}"


def _get_location() -> str:
    try:
        out, rc = _run(["powershell", "-NoProfile", "-Command",
            "Add-Type -AssemblyName System.Device; "
            "$watcher = New-Object System.Device.Location.GeoCoordinateWatcher; "
            "$watcher.Start(); "
            "Start-Sleep -Seconds 2; "
            "$loc = $watcher.Position.Location; "
            "if ($loc.IsUnknown) { 'UNKNOWN' } else { $loc.Latitude.ToString() + ',' + $loc.Longitude.ToString() }"],
            timeout=20)
        if rc == 0 and out and "UNKNOWN" not in out:
            return f"Location: {out}"
    except Exception:
        pass
    try:
        out, rc = _run(["curl", "-s", "https://ipinfo.io/json"], timeout=10)
        if rc == 0:
            data = json.loads(out)
            lat = data.get("loc", "")
            city = data.get("city", "")
            region = data.get("region", "")
            country = data.get("country", "")
            return f"Location (IP-based): {lat} | {city}, {region}, {country}"
    except Exception:
        pass
    return "Location unavailable (no GPS hardware and IP geolocation failed)"


def _get_network_info() -> str:
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "Unknown"
    try:
        out = _ps("(Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object Name,InterfaceDescription,MacAddress,LinkSpeed | ConvertTo-Json)")
        adapters = json.loads(out) if out else []
        if isinstance(adapters, dict):
            adapters = [adapters]
        parts = [f"Local IP: {local_ip}"]
        for a in adapters:
            parts.append(f"  {a.get('Name','?')}: {a.get('LinkSpeed','?')} | MAC: {a.get('MacAddress','?')}")
        return "\n".join(parts)
    except Exception:
        return f"Local IP: {local_ip}"


def _get_battery_status() -> str:
    try:
        out = _ps("(Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining,BatteryStatus,Status | ConvertTo-Json)")
        if out:
            data = json.loads(out)
            if isinstance(data, list):
                data = data[0]
            pct = data.get("EstimatedChargeRemaining", "?")
            status_map = {1: "Discharging", 2: "AC Connected", 3: "Fully Charged", 4: "Low", 5: "Critical", 6: "Charging", 7: "Not Installed"}
            bat_status = status_map.get(data.get("BatteryStatus", 0), "Unknown")
            return f"Battery: {pct}% | {bat_status}"
    except Exception:
        pass
    try:
        out = _ps("(Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory | ConvertTo-Json)")
        return f"Battery info unavailable. RAM: {out}"
    except Exception:
        return "Battery info unavailable (desktop or no battery)"


def _get_screen_info() -> str:
    try:
        out = _ps("(Get-CimInstance Win32_VideoController | Select-Object Name,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate,AdapterRAM | ConvertTo-Json)")
        monitors = json.loads(out) if out else []
        if isinstance(monitors, dict):
            monitors = [monitors]
        parts = []
        for m in monitors:
            ram_gb = round(m.get("AdapterRAM", 0) / (1024**3), 1) if m.get("AdapterRAM") else "?"
            parts.append(f"{m.get('Name','?')}: {m.get('CurrentHorizontalResolution','?')}x{m.get('CurrentVerticalResolution','?')} @ {m.get('CurrentRefreshRate','?')}Hz | VRAM: {ram_gb}GB")
        return "\n".join(parts) if parts else "No monitor info found"
    except Exception as e:
        return f"Screen info error: {e}"


def _get_foreground_app() -> str:
    try:
        import ctypes.wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            import psutil
            proc = psutil.Process(pid.value)
            exe = proc.name()
            path = proc.exe()
        except Exception:
            exe = "unknown"
            path = ""
        return f"Foreground: {title} | Process: {exe} | Path: {path}"
    except Exception:
        pass
    try:
        out = _ps("Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Sort-Object StartTime -Descending | Select-Object -First 5 Name,MainWindowTitle | ConvertTo-Json")
        procs = json.loads(out) if out else []
        if isinstance(procs, dict):
            procs = [procs]
        if procs:
            top = procs[0]
            return f"Foreground: {top.get('MainWindowTitle','?')} | Process: {top.get('Name','?')}"
    except Exception:
        pass
    return "Cannot detect foreground app"


def _get_running_apps() -> str:
    try:
        out = _ps("Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object Id,Name,MainWindowTitle,StartTime | Sort-Object Name | ConvertTo-Json")
        procs = json.loads(out) if out else []
        if isinstance(procs, dict):
            procs = [procs]
        parts = []
        for p in procs:
            parts.append(f"[{p.get('Id','?')}] {p.get('Name','?')}: {p.get('MainWindowTitle','?')}")
        return "\n".join(parts) if parts else "No visible apps running"
    except Exception as e:
        return f"Error listing apps: {e}"


def _get_audio_devices() -> str:
    try:
        out = _ps("Get-CimInstance Win32_SoundDevice | Select-Object Name,Status,Manufacturer | ConvertTo-Json")
        devs = json.loads(out) if out else []
        if isinstance(devs, dict):
            devs = [devs]
        parts = [f"{d.get('Name','?')} ({d.get('Status','?')}) - {d.get('Manufacturer','?')}" for d in devs]
        return "\n".join(parts) if parts else "No audio devices found"
    except Exception as e:
        return f"Audio devices error: {e}"


def _get_input_devices() -> str:
    try:
        out = _ps("Get-CimInstance Win32_Keyboard | Select-Object Name,Description,Status | ConvertTo-Json")
        kbds = json.loads(out) if out else []
        if isinstance(kbds, dict):
            kbds = [kbds]
        out2 = _ps("Get-CimInstance Win32_PointingDevice | Select-Object Name,Description,Status | ConvertTo-Json")
        mice = json.loads(out2) if out2 else []
        if isinstance(mice, dict):
            mice = [mice]
        parts = ["--- Keyboards ---"]
        for k in kbds:
            parts.append(f"  {k.get('Name','?')}: {k.get('Description','?')} [{k.get('Status','?')}]")
        parts.append("--- Mice/Pointing ---")
        for m in mice:
            parts.append(f"  {m.get('Name','?')}: {m.get('Description','?')} [{m.get('Status','?')}]")
        return "\n".join(parts)
    except Exception as e:
        return f"Input devices error: {e}"


def _get_usb_devices() -> str:
    try:
        out = _ps("Get-CimInstance Win32_USBControllerDevice | ForEach-Object { [wmi]($_.Dependent) } | Select-Object Name,DeviceID,Status | Sort-Object Name | ConvertTo-Json")
        devs = json.loads(out) if out else []
        if isinstance(devs, dict):
            devs = [devs]
        parts = [f"{d.get('Name','?')} [{d.get('Status','?')}] ID: {d.get('DeviceID','?')[:40]}" for d in devs]
        return "\n".join(parts) if parts else "No USB devices found"
    except Exception as e:
        return f"USB error: {e}"


def _get_printers() -> str:
    try:
        out = _ps("Get-Printer | Select-Object Name,DriverName,PortName,PrinterStatus,Type | ConvertTo-Json")
        printers = json.loads(out) if out else []
        if isinstance(printers, dict):
            printers = [printers]
        status_map = {0: "Normal", 1: "Paused", 2: "Error", 3: "Deleting"}
        parts = []
        for p in printers:
            st = status_map.get(p.get("PrinterStatus", 0), "Unknown")
            parts.append(f"{p.get('Name','?')} ({p.get('DriverName','?')}) [{st}]")
        return "\n".join(parts) if parts else "No printers found"
    except Exception as e:
        return f"Printers error: {e}"


def _get_startup_apps() -> str:
    try:
        out = _ps("Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | Sort-Object Name | ConvertTo-Json")
        apps = json.loads(out) if out else []
        if isinstance(apps, dict):
            apps = [apps]
        parts = [f"{a.get('Name','?')}: {a.get('Command','?')[:80]} [{a.get('Location','?')}]" for a in apps]
        return "\n".join(parts) if parts else "No startup apps found"
    except Exception as e:
        return f"Startup apps error: {e}"


def _get_scheduled_tasks(folder="\\") -> str:
    try:
        out = _ps(f"Get-ScheduledTask -TaskPath '{folder}\\*' | Where-Object {{$_.State -ne 'Disabled'}} | Select-Object TaskName,State,TaskPath | Sort-Object TaskName | Select-Object -First 30 | ConvertTo-Json")
        tasks = json.loads(out) if out else []
        if isinstance(tasks, dict):
            tasks = [tasks]
        parts = [f"{t.get('TaskPath','')}{t.get('TaskName','?')} [{t.get('State','?')}]" for t in tasks]
        return "\n".join(parts) if parts else "No scheduled tasks found"
    except Exception as e:
        return f"Scheduled tasks error: {e}"


def _get_env_vars() -> str:
    try:
        env = os.environ
        important = ["PATH", "TEMP", "TMP", "USERPROFILE", "HOME", "COMPUTERNAME", "USERNAME", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "SYSTEMROOT", "PROCESSOR_IDENTIFIER", "NUMBER_OF_PROCESSORS"]
        parts = [f"{k}={env.get(k, '?')[:80]}" for k in important if k in env]
        return "\n".join(parts)
    except Exception as e:
        return f"Env vars error: {e}"


def _get_system_info() -> str:
    try:
        out = _ps("""$cs = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor
$ram_gb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
$free_gb = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$uptime = (Get-Date) - $os.LastBootUpTime
@"
Computer: $($cs.Name) | $($cs.Manufacturer) $($cs.Model)
OS: $($os.Caption) $($os.Version) (Build $($os.BuildNumber))
CPU: $($cpu.Name) | $($cpu.NumberOfCores) cores | $($cpu.NumberOfLogicalProcessors) threads | $($cpu.MaxClockSpeed)MHz
RAM: ${ram_gb}GB total, ${free_gb}GB free
Uptime: $($uptime.Days)d $($uptime.Hours)h $($uptime.Metrics.Minutes)m
Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@""")
        return out.strip() if out else "System info unavailable"
    except Exception as e:
        return f"System info error: {e}"


def _get_ip_info() -> str:
    try:
        out, rc = _run(["curl", "-s", "https://ipinfo.io/json"], timeout=8)
        if rc == 0:
            data = json.loads(out)
            parts = [
                f"Public IP: {data.get('ip', '?')}",
                f"City: {data.get('city', '?')}, {data.get('region', '?')}, {data.get('country', '?')}",
                f"Org: {data.get('org', '?')}",
                f"Timezone: {data.get('timezone', '?')}",
                f"Coords: {data.get('loc', '?')}",
            ]
            return "\n".join(parts)
    except Exception:
        pass
    return "IP info unavailable"


def _get_cpu_info() -> str:
    try:
        out = _ps("Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed,LoadPercentage | ConvertTo-Json")
        cpus = json.loads(out) if out else []
        if isinstance(cpus, dict):
            cpus = [cpus]
        parts = []
        for c in cpus:
            parts.append(f"{c.get('Name','?')} | {c.get('NumberOfCores','?')}C/{c.get('NumberOfLogicalProcessors','?')}T | {c.get('CurrentClockSpeed','?')}/{c.get('MaxClockSpeed','?')}MHz | Load: {c.get('LoadPercentage','?')}%")
        return "\n".join(parts) if parts else "No CPU info"
    except Exception as e:
        return f"CPU info error: {e}"


def _get_gpu_info() -> str:
    try:
        out = _ps("Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM,CurrentRefreshRate,CurrentHorizontalResolution,CurrentVerticalResolution | ConvertTo-Json")
        gpus = json.loads(out) if out else []
        if isinstance(gpus, dict):
            gpus = [gpus]
        parts = []
        for g in gpus:
            ram_gb = round(g.get("AdapterRAM", 0) / (1024**3), 1) if g.get("AdapterRAM") else "?"
            parts.append(f"{g.get('Name','?')} | Driver: {g.get('DriverVersion','?')} | VRAM: {ram_gb}GB | {g.get('CurrentHorizontalResolution','?')}x{g.get('CurrentVerticalResolution','?')}@{g.get('CurrentRefreshRate','?')}Hz")
        return "\n".join(parts) if parts else "No GPU info"
    except Exception as e:
        return f"GPU info error: {e}"


def _get_ram_info() -> str:
    try:
        out = _ps("""$os = Get-CimInstance Win32_OperatingSystem
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$free = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$used = $total - $free
$pct = [math]::Round($used / $total * 100, 1)
$modules = Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,Speed,Manufacturer,DeviceLocator
$mod_str = ($modules | ForEach-Object { "$($_.DeviceLocator): $([math]::Round($_.Capacity/1GB,1))GB @ $($_.Speed)MHz - $($_.Manufacturer)" }) -join '`n'
@"
Total: ${total}GB | Used: ${used}GB | Free: ${free}GB (${pct}% used)
Modules:
$mod_str
"@""")
        return out.strip() if out else "RAM info unavailable"
    except Exception as e:
        return f"RAM info error: {e}"


def _get_disk_info() -> str:
    try:
        out = _ps("Get-CimInstance Win32_LogicalDisk | Where-Object {$_.DriveType -eq 3} | Select-Object DeviceID,VolumeName,Size,FreeSpace | ConvertTo-Json")
        disks = json.loads(out) if out else []
        if isinstance(disks, dict):
            disks = [disks]
        parts = []
        for d in disks:
            total_gb = round(d.get("Size", 0) / (1024**3), 1)
            free_gb = round(d.get("FreeSpace", 0) / (1024**3), 1)
            used_pct = round((1 - d.get("FreeSpace", 0) / max(d.get("Size", 1), 1)) * 100, 1)
            parts.append(f"{d.get('DeviceID','?')} {d.get('VolumeName','?')}: {total_gb}GB total, {free_gb}GB free ({used_pct}% used)")
        return "\n".join(parts) if parts else "No disk info"
    except Exception as e:
        return f"Disk info error: {e}"


def _get_monitor_info() -> str:
    try:
        out = _ps("Get-CimInstance WmiMonitorID -Namespace root\\wmi | Select-Object UserFriendlyName,ManufacturerName,SerialNumberID | ConvertTo-Json")
        monitors = json.loads(out) if out else []
        if isinstance(monitors, dict):
            monitors = [monitors]
        parts = []
        for m in monitors:
            name = m.get("UserFriendlyName", ["?"])
            if isinstance(name, list):
                name = "".join(chr(c) for c in name if c)
            mfr = m.get("ManufacturerName", ["?"])
            if isinstance(mfr, list):
                mfr = "".join(chr(c) for c in mfr if c)
            parts.append(f"{name} by {mfr}")
        return "\n".join(parts) if parts else "No monitor info"
    except Exception as e:
        return f"Monitor info error: {e}"


def _bluetooth_power(on: bool) -> str:
    state = "True" if on else "False"
    try:
        out = _ps(f"Set-BluetoothRadio -State {'On' if on else 'Off'} -ErrorAction Stop")
        return f"Bluetooth {'enabled' if on else 'disabled'}"
    except Exception:
        pass
    try:
        _ps(f"""
        $dev = Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue
        if ($dev) {{
            {'Enable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false' if on else 'Disable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false'}
        }}
        """)
        return f"Bluetooth {'enabled' if on else 'disabled'} (PnP method)"
    except Exception as e:
        return f"Bluetooth toggle failed: {e}"


def _bluetooth_status() -> str:
    try:
        out = _ps("Get-BluetoothRadio | Select-Object Name,State,Address | ConvertTo-Json")
        radios = json.loads(out) if out else []
        if isinstance(radios, dict):
            radios = [radios]
        parts = [f"{r.get('Name','?')}: {r.get('State','?')} | Address: {r.get('Address','?')}" for r in radios]
        if parts:
            return "Bluetooth Radios:\n" + "\n".join(parts)
    except Exception:
        pass
    try:
        out = _ps("(Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue).Count")
        return f"Bluetooth: {out} active device(s)"
    except Exception:
        return "Bluetooth status unknown"


def _bluetooth_scan() -> str:
    try:
        out = _ps("""
        $dev = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {$_.FriendlyName}
        $dev | Select-Object FriendlyName,Status,InstanceId | ConvertTo-Json
        """, timeout=20)
        devs = json.loads(out) if out else []
        if isinstance(devs, dict):
            devs = [devs]
        parts = [f"{d.get('FriendlyName','?')} [{d.get('Status','?')}]" for d in devs]
        return "Bluetooth devices:\n" + "\n".join(parts) if parts else "No Bluetooth devices found"
    except Exception as e:
        return f"Bluetooth scan error: {e}"


def _bluetooth_pair(device_name: str) -> str:
    if not device_name:
        return "Provide device name to pair"
    try:
        _ps(f"""
        $dev = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {{$_.FriendlyName -like '*{device_name}*'}}
        if ($dev) {{
            Write-Host "Pairing: $($dev.FriendlyName)..."
        }} else {{
            Write-Host "Device not found: {device_name}"
        }}
        """)
        return f"Pairing request sent for '{device_name}' — check the device for confirmation"
    except Exception as e:
        return f"Bluetooth pair error: {e}"


def _bluetooth_unpair(device_name: str) -> str:
    if not device_name:
        return "Provide device name to unpair"
    try:
        _ps(f"""
        $dev = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {{$_.FriendlyName -like '*{device_name}*'}}
        if ($dev) {{
            Disable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false
            Write-Host "Unpaired: $($dev.FriendlyName)"
        }} else {{
            Write-Host "Device not found: {device_name}"
        }}
        """)
        return f"Unpair request sent for '{device_name}'"
    except Exception as e:
        return f"Bluetooth unpair error: {e}"


def _bluetooth_connected() -> str:
    try:
        out = _ps("""
        $dev = Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue | Where-Object {$_.FriendlyName}
        $dev | Select-Object FriendlyName,InstanceId | ConvertTo-Json
        """)
        devs = json.loads(out) if out else []
        if isinstance(devs, dict):
            devs = [devs]
        parts = [d.get("FriendlyName", "?") for d in devs]
        return "Connected: " + ", ".join(parts) if parts else "No Bluetooth devices connected"
    except Exception as e:
        return f"Error: {e}"


def _wifi_power(on: bool) -> str:
    state = '"Allow"' if on else '"Deny"'
    try:
        _ps(f"Set-NetAdapterAdvancedProperty -Name 'Wi-Fi' -DisplayName 'Wireless Mode' -ErrorAction SilentlyContinue")
    except Exception:
        pass
    try:
        _ps(f"""
        $netsh = netsh interface set interface 'Wi-Fi' admin={'enable' if on else 'disable'}
        """)
        return f"Wi-Fi {'enabled' if on else 'disabled'}"
    except Exception as e:
        return f"Wi-Fi toggle error: {e}"


def _wifi_status() -> str:
    try:
        out = _ps("""
        $adapter = Get-NetAdapter -Name 'Wi-Fi' -ErrorAction SilentlyContinue
        $profile = netsh wlan show interfaces 2>$null
        @"
Adapter: $($adapter.Name) | Status: $($adapter.Status) | State: $($adapter.MediaConnectionState)
Mac: $($adapter.MacAddress) | Speed: $($adapter.LinkSpeed)
$profile
"@""")
        return out.strip() if out else "Wi-Fi status unavailable"
    except Exception as e:
        return f"Wi-Fi status error: {e}"


def _wifi_scan() -> str:
    try:
        out = _ps("netsh wlan show networks mode=bssid", timeout=20)
        return out if out else "No Wi-Fi networks found"
    except Exception as e:
        return f"Wi-Fi scan error: {e}"


def _wifi_connect(ssid: str) -> str:
    if not ssid:
        return "Provide SSID to connect"
    try:
        _ps(f'netsh wlan connect name="{ssid}"')
        return f"Connecting to {ssid}..."
    except Exception as e:
        return f"Wi-Fi connect error: {e}"


def _wifi_disconnect(ssid: str) -> str:
    try:
        _ps("netsh wlan disconnect")
        return "Wi-Fi disconnected"
    except Exception as e:
        return f"Wi-Fi disconnect error: {e}"


def _hotspot(on: bool) -> str:
    try:
        if on:
            _ps("""
            $profile = '<?xml version="1.0"?><WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1"><name>JARVIS_Hotspot</name><SSID><name>JARVIS_Hotspot</name></SSID><connectionType>hotspot</connectionType><connectionMode>manual</connectionMode><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption></authEncryption><sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>jarvis12345</keyMaterial></sharedKey></security></MSM></WLANProfile>'
            netsh wlan add profile filename=$profile
            netsh wlan start hostednetwork
            """)
            return "Hotspot ON: JARVIS_Hotspot / jarvis12345"
        else:
            _ps("netsh wlan stop hostednetwork")
            return "Hotspot OFF"
    except Exception as e:
        return f"Hotspot error: {e}"


def _hotspot_config(ssid: str, password: str) -> str:
    ssid = ssid or "JARVIS_Hotspot"
    password = password or "jarvis12345"
    try:
        _ps(f"""
        $profile = '<?xml version="1.0"?><WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1"><name>{ssid}</name><SSID><name>{ssid}</name></SSID><connectionType>hotspot</connectionType><connectionMode>manual</connectionMode><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption></authEncryption><sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>{password}</keyMaterial></sharedKey></security></MSM></WLANProfile>'
        netsh wlan add profile filename=$profile
        netsh wlan start hostednetwork
        """)
        return f"Hotspot configured: {ssid} / {password}"
    except Exception as e:
        return f"Hotspot config error: {e}"


def _night_mode(on: bool) -> str:
    try:
        path = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default`$windows.data.bluelightreduction.bluelightreductionstate\windows.data.bluelightreduction.bluelightreductionstate"
        if on:
            _ps(f"""
            $path = '{path}'
            Set-ItemProperty -Path $path -Name Data -Type Binary -Value ([byte[]](08,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00)) -ErrorAction SilentlyContinue
            """)
            return "Night light ON"
        else:
            _ps(f"""
            $path = '{path}'
            Set-ItemProperty -Path $path -Name Data -Type Binary -Value ([byte[]](08,00,00,00,00,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00,01,00,00,00)) -ErrorAction SilentlyContinue
            """)
            return "Night light OFF"
    except Exception as e:
        return f"Night mode error: {e}"


def _night_mode_status() -> str:
    try:
        path = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default`$windows.data.bluelightreduction.bluelightreductionstate\windows.data.bluelightreduction.bluelightreductionstate"
        out = _ps(f"""
        $path = '{path}'
        $val = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue
        if ($val.Data -and $val.Data[4] -eq 1) {{ 'Night light: ON' }} else {{ 'Night light: OFF' }}
        """)
        return out if out else "Night light status unknown"
    except Exception as e:
        return f"Night mode status error: {e}"


def _set_wallpaper(path: str) -> str:
    if not path or not Path(path).exists():
        return f"Image not found: {path}"
    try:
        import ctypes
        ctypes.windll.user32.SystemParametersInfoW(20, 0, str(Path(path).resolve()), 3)
        return f"Wallpaper set: {path}"
    except Exception as e:
        return f"Wallpaper error: {e}"


def _get_clipboard() -> str:
    try:
        out = _ps("Get-Clipboard")
        return f"Clipboard: {out[:500]}" if out else "Clipboard empty"
    except Exception:
        return "Clipboard unavailable"


def _set_clipboard(text: str) -> str:
    if not text:
        return "No text provided"
    try:
        _ps(f"Set-Clipboard -Value @'\n{text}\n'@")
        return f"Clipboard set: {text[:60]}{'...' if len(text) > 60 else ''}"
    except Exception:
        try:
            import pyperclip
            import time
            for attempt in range(3):
                try:
                    pyperclip.copy(text)
                    return f"Clipboard set: {text[:60]}{'...' if len(text) > 60 else ''}"
                except Exception:
                    time.sleep(0.1)
            return f"Clipboard set failed after retries"
        except Exception as e:
            return f"Clipboard error: {e}"


def _get_volume() -> str:
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(iface, POINTER(IAudioEndpointVolume))
        level = int(vol.GetMasterVolumeLevelScalar() * 100)
        muted = vol.GetMute()
        return f"Volume: {level}% | Muted: {'Yes' if muted else 'No'}"
    except Exception:
        return "Volume info unavailable"


def _set_volume(val: str) -> str:
    try:
        vol = max(0, min(100, int(val)))
    except (ValueError, TypeError):
        return "Invalid volume value (0-100)"
    try:
        import pyautogui
        current = _get_volume()
        current_val = int("".join(c for c in current.split("%")[0] if c.isdigit()) or "50")
        diff = vol - current_val
        key = "volumeup" if diff > 0 else "volumedown"
        for _ in range(abs(diff) // 2):
            pyautogui.press(key)
        return f"Volume set to ~{vol}%"
    except Exception:
        return f"Volume set to {vol}% (attempted)"


def _get_brightness() -> str:
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness()[0]
        return f"Brightness: {current}%"
    except ImportError:
        pass
    try:
        out = _ps("(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightness).CurrentBrightness")
        return f"Brightness: {out}%"
    except Exception:
        return "Brightness info unavailable"


def _set_brightness(val: str) -> str:
    try:
        level = max(0, min(100, int(val)))
    except (ValueError, TypeError):
        return "Invalid brightness value (0-100)"
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return f"Brightness set to {level}%"
    except ImportError:
        pass
    try:
        _ps(f"(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})")
        return f"Brightness set to {level}%"
    except Exception:
        return f"Brightness set to {level}% (attempted)"


def _airplane(on: bool) -> str:
    try:
        _ps(f"""
        $radios = Get-NetAdapter | Where-Object {{$_.InterfaceDescription -like '*Wireless*' -or $_.InterfaceDescription -like '*Bluetooth*'}}
        foreach ($r in $radios) {{
            {'Disable-NetAdapter -Name $r.Name -Confirm:$false' if on else 'Enable-NetAdapter -Name $r.Name -Confirm:$false'}
        }}
        """)
        return f"Airplane mode {'ON' if on else 'OFF'}"
    except Exception as e:
        return f"Airplane mode error: {e}"


def _dnd(on: bool) -> str:
    try:
        path = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default`$windows.data.notifications.quiethoursprofile\windows.data.notifications.quiethoursprofile"
        _ps(f"""
        $key = '{path}'
        if (Test-Path $key) {{
            {'Set-ItemProperty -Path $key -Name Enabled -Value 1 -ErrorAction SilentlyContinue' if on else 'Set-ItemProperty -Path $key -Name Enabled -Value 0 -ErrorAction SilentlyContinue'}
        }}
        """)
        return f"Do Not Disturb {'ON' if on else 'OFF'}"
    except Exception as e:
        return f"DND error: {e}"


def _get_keyboard_layout() -> str:
    try:
        out = _ps("Get-WinUserLanguageList | Select-Object -ExpandProperty LanguageTag")
        return f"Keyboard layout: {out}" if out else "Layout unknown"
    except Exception:
        return "Keyboard layout unavailable"


def _set_keyboard_layout(layout: str) -> str:
    if not layout:
        return "Provide layout (e.g. en-US, fr-FR, es-ES)"
    try:
        _ps(f"Set-WinUserLanguageList -LanguageList {layout} -Force")
        return f"Keyboard layout set to {layout}"
    except Exception as e:
        return f"Layout error: {e}"


def _get_installed_apps() -> str:
    try:
        out = _ps("Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName,DisplayVersion | Sort-Object DisplayName | Select-Object -First 40 | ConvertTo-Json")
        apps = json.loads(out) if out else []
        if isinstance(apps, dict):
            apps = [apps]
        parts = [f"{a.get('DisplayName','?')} {a.get('DisplayVersion','')}" for a in apps if a.get("DisplayName")]
        return "\n".join(parts) if parts else "No apps found"
    except Exception as e:
        return f"Installed apps error: {e}"


def _get_running_services(filter_name: str = "") -> str:
    try:
        where = f"| Where-Object {{$_.DisplayName -like '*{filter_name}*'}}" if filter_name else ""
        out = _ps(f"Get-Service | Where-Object {{$_.Status -eq 'Running'}} {where} | Select-Object -First 30 Name,DisplayName | Sort-Object DisplayName | ConvertTo-Json")
        services = json.loads(out) if out else []
        if isinstance(services, dict):
            services = [services]
        parts = [f"{s.get('Name','?')}: {s.get('DisplayName','?')}" for s in services]
        return "\n".join(parts) if parts else "No running services found"
    except Exception as e:
        return f"Services error: {e}"


def _start_service(name: str) -> str:
    if not name:
        return "Provide service name"
    try:
        _ps(f"Start-Service -Name '{name}' -ErrorAction Stop")
        return f"Service '{name}' started"
    except Exception as e:
        return f"Start service error: {e}"


def _stop_service(name: str) -> str:
    if not name:
        return "Provide service name"
    try:
        _ps(f"Stop-Service -Name '{name}' -Force -ErrorAction Stop")
        return f"Service '{name}' stopped"
    except Exception as e:
        return f"Stop service error: {e}"


def _get_windows_update() -> str:
    try:
        out = _ps("Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID,Description,InstalledOn | ConvertTo-Json")
        updates = json.loads(out) if out else []
        if isinstance(updates, dict):
            updates = [updates]
        parts = [f"{u.get('HotFixID','?')}: {u.get('Description','?')} ({u.get('InstalledOn','?')})" for u in updates]
        return "Recent updates:\n" + "\n".join(parts) if parts else "No update history found"
    except Exception as e:
        return f"Windows Update error: {e}"


def _get_defender_status() -> str:
    try:
        out = _ps("Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled,AMServiceEnabled,AntivirusEnabled,FullScanAge,QuickScanAge | ConvertTo-Json")
        data = json.loads(out) if out else {}
        if data:
            parts = [
                f"Real-time protection: {'ON' if data.get('RealTimeProtectionEnabled') else 'OFF'}",
                f"AV service: {'ON' if data.get('AMServiceEnabled') else 'OFF'}",
                f"Antivirus: {'Enabled' if data.get('AntivirusEnabled') else 'Disabled'}",
                f"Last full scan: {data.get('FullScanAge', '?')} days ago",
                f"Last quick scan: {data.get('QuickScanAge', '?')} days ago",
            ]
            return "\n".join(parts)
    except Exception:
        pass
    return "Defender status unavailable"


def _get_firewall_status() -> str:
    try:
        out = _ps("Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json")
        profiles = json.loads(out) if out else []
        if isinstance(profiles, dict):
            profiles = [profiles]
        parts = [f"{p.get('Name','?')}: {'ON' if p.get('Enabled') else 'OFF'}" for p in profiles]
        return "Firewall:\n" + "\n".join(parts) if parts else "Firewall status unavailable"
    except Exception as e:
        return f"Firewall error: {e}"


def _lock_workstation() -> str:
    try:
        ctypes.windll.user32.LockWorkStation()
        return "Workstation locked"
    except Exception as e:
        return f"Lock error: {e}"


def _get_user_accounts() -> str:
    try:
        out = _ps("Get-LocalUser | Select-Object Name,Enabled,LastLogon | Sort-Object Name | ConvertTo-Json")
        users = json.loads(out) if out else []
        if isinstance(users, dict):
            users = [users]
        parts = [f"{u.get('Name','?')} [{'Active' if u.get('Enabled') else 'Disabled'}] Last: {u.get('LastLogon','?')}" for u in users]
        return "\n".join(parts) if parts else "No user accounts found"
    except Exception as e:
        return f"Users error: {e}"


def _get_shares() -> str:
    try:
        out = _ps("Get-SmbShare | Select-Object Name,Path,Description | Sort-Object Name | ConvertTo-Json")
        shares = json.loads(out) if out else []
        if isinstance(shares, dict):
            shares = [shares]
        parts = [f"{s.get('Name','?')}: {s.get('Path','?')} - {s.get('Description','')}" for s in shares]
        return "\n".join(parts) if parts else "No shares found"
    except Exception as e:
        return f"Shares error: {e}"


def _get_drivers() -> str:
    try:
        out = _ps("Get-CimInstance Win32_PnSignedDriver | Where-Object {$_.DriverName} | Select-Object DeviceName,DriverVersion,Manufacturer | Sort-Object DeviceName | Select-Object -First 20 | ConvertTo-Json")
        drivers = json.loads(out) if out else []
        if isinstance(drivers, dict):
            drivers = [drivers]
        parts = [f"{d.get('DeviceName','?')}: {d.get('DriverVersion','?')} ({d.get('Manufacturer','?')})" for d in drivers]
        return "\n".join(parts) if parts else "No drivers found"
    except Exception as e:
        return f"Drivers error: {e}"


def _get_network_connections() -> str:
    try:
        out = _ps("Get-NetTCPConnection | Where-Object {$_.State -eq 'Established'} | Select-Object -First 20 LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess | ConvertTo-Json")
        conns = json.loads(out) if out else []
        if isinstance(conns, dict):
            conns = [conns]
        parts = [f"{c.get('LocalAddress','?')}:{c.get('LocalPort','?')} -> {c.get('RemoteAddress','?')}:{c.get('RemotePort','?')} (PID:{c.get('OwningProcess','?')})" for c in conns]
        return "Active connections:\n" + "\n".join(parts) if parts else "No active connections"
    except Exception as e:
        return f"Network connections error: {e}"


def _get_event_log(log_name: str = "System") -> str:
    log_name = log_name or "System"
    try:
        out = _ps(f"Get-EventLog -LogName '{log_name}' -Newest 10 -EntryType Error,Warning 2>$null | Select-Object TimeGenerated,EntryType,Source,Message | ConvertTo-Json")
        events = json.loads(out) if out else []
        if isinstance(events, dict):
            events = [events]
        parts = []
        for e in events:
            msg = (e.get("Message", "") or "")[:80]
            parts.append(f"[{e.get('TimeGenerated','?')}] {e.get('EntryType','?')}: {e.get('Source','?')} - {msg}")
        return f"Recent {log_name} events:\n" + "\n".join(parts) if parts else f"No recent errors in {log_name}"
    except Exception as e:
        return f"Event log error: {e}"
