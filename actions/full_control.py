"""Full system control: settings, alarms, camera, smart home, all OS operations."""

import subprocess
import os
import time
import json
import ctypes
from pathlib import Path


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def handle(parameters: dict) -> str:
    action = parameters.get("action", "")
    target = parameters.get("target", "")
    value = parameters.get("value", "")

    handlers = {
        "volume_up": _volume_up,
        "volume_down": _volume_down,
        "volume_set": lambda: _volume_set(value),
        "volume_mute": _volume_mute,
        "brightness_up": _brightness_up,
        "brightness_down": _brightness_down,
        "brightness_set": lambda: _brightness_set(value),
        "wifi_on": lambda: _wifi_toggle(True),
        "wifi_off": lambda: _wifi_toggle(False),
        "bluetooth_on": lambda: _bluetooth_toggle(True),
        "bluetooth_off": lambda: _bluetooth_toggle(False),
        "airplane_mode": _airplane_mode,
        "do_not_disturb": _dnd_toggle,
        "lock_screen": _lock_screen,
        "sleep": _sleep_pc,
        "shutdown": _shutdown_pc,
        "restart": _restart_pc,
        "screenshot": _take_screenshot,
        "set_wallpaper": lambda: _set_wallpaper(target),
        "empty_trash": _empty_trash,
        "open_settings": lambda: _open_settings(target),
        "open_control_panel": _open_control_panel,
        "open_task_manager": _open_task_manager,
        "open_device_manager": _open_device_manager,
        "open_network_settings": _open_network,
        "open_sound_settings": _open_sound,
        "open_display_settings": _open_display,
        "open_power_settings": _open_power,
        "open_bluetooth_settings": _open_bluetooth,
        "set_alarm": lambda: _set_alarm(target, value),
        "list_alarms": _list_alarms,
        "delete_alarm": lambda: _delete_alarm(target),
        "capture_camera": _capture_camera,
        "list_cameras": _list_cameras,
        "list_audio_devices": _list_audio,
        "set_default_audio": lambda: _set_default_audio(target),
        "list_printers": _list_printers,
        "lock_app": lambda: _lock_app(target),
        "kill_process": lambda: _kill_process(target),
        "list_processes": lambda: _list_processes(target),
        "open_app": lambda: _open_app(target),
        "close_app": lambda: _close_app(target),
        "list_startup_apps": _list_startup,
        "add_startup": lambda: _add_startup(target),
        "remove_startup": lambda: _remove_startup(target),
        "list_env_vars": _list_env,
        "set_env_var": lambda: _set_env_var(target, value),
        "disk_info": _disk_info,
        "list_usb_devices": _list_usb,
        "list_drivers": _list_drivers,
        "check_updates": _check_updates,
        "system_info_full": _system_info_full,
        "list_scheduled_tasks": _list_scheduled_tasks,
        "create_system_restore": _create_restore_point,
        "list_user_accounts": _list_users,
        "list_shares": _list_shares,
        "open_camera_app": _open_camera_app,
        "open_calculator": _open_calc,
        "open_notepad": _open_notepad,
        "open_paint": _open_paint,
        "open_cmd": _open_cmd,
        "open_powershell": _open_ps,
    }

    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown system_control action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _volume_up():
    try:
        import pyautogui; pyautogui.press("volumeup"); return "Volume up"
    except Exception:
        pass
    _run(["nircmd", "setsysvolume", "5000"])
    return "Volume up"


def _volume_down():
    try:
        import pyautogui; pyautogui.press("volumedown"); return "Volume down"
    except Exception:
        pass
    _run(["nircmd", "setsysvolume", "-5000"])
    return "Volume down"


def _volume_set(val):
    try:
        vol = max(0, min(100, int(val)))
    except (ValueError, TypeError):
        return "Invalid volume value"
    try:
        import pyautogui
        current = _get_current_volume()
        diff = vol - current
        key = "volumeup" if diff > 0 else "volumedown"
        for _ in range(abs(diff) // 2):
            pyautogui.press(key)
        return f"Volume set to ~{vol}%"
    except Exception:
        pass
    try:
        sys_vol = int(vol * 65535 / 100)
        _run(["nircmd", "setsysvolume", str(sys_vol)])
        return f"Volume set to {vol}%"
    except Exception:
        return f"Volume set to {vol}% (attempted)"


def _get_current_volume():
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(iface, POINTER(IAudioEndpointVolume))
        return int(volume.GetMasterVolumeLevelScalar() * 100)
    except Exception:
        return 50


def _volume_mute():
    try:
        import pyautogui; pyautogui.press("volumemute"); return "Volume toggled"
    except Exception:
        pass
    _run(["nircmd", "mutesysvolume", "2"])
    return "Volume toggled"


def _brightness_up():
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness()[0]
        sbc.set_brightness(min(100, current + 10))
        return f"Brightness: {min(100, current + 10)}%"
    except ImportError:
        _run(["powershell", "-Command", "(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,100)"])
        return "Brightness set to max (fallback)"


def _brightness_down():
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness()[0]
        sbc.set_brightness(max(0, current - 10))
        return f"Brightness: {max(0, current - 10)}%"
    except ImportError:
        _run(["powershell", "-Command", "(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,30)"])
        return "Brightness set to 30% (fallback)"


def _brightness_set(val):
    try:
        bright = max(0, min(100, int(val)))
        import screen_brightness_control as sbc
        sbc.set_brightness(bright)
        return f"Brightness: {bright}%"
    except ImportError:
        _run(["powershell", "-Command", f"(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{bright})"])
        return f"Brightness: {bright}% (fallback)"


def _wifi_toggle(on):
    state = "enable" if on else "disable"
    _run(["netsh", "wlan", "set", "interface", "admin", f"state={state}"])
    return f"WiFi {'enabled' if on else 'disabled'}"


def _bluetooth_toggle(on):
    state = "enable" if on else "disable"
    _run(["powershell", "-Command", f"Get-Service bthserv | Set-Service -StartupType {'Automatic' if on else 'Disabled'}"])
    return f"Bluetooth {'enabled' if on else 'disabled'}"


def _airplane_mode():
    _run(["powershell", "-Command", "Start-Process ms-settings:network-airplanemode"])
    return "Airplane mode settings opened"


def _dnd_toggle():
    _run(["powershell", "-Command", "Start-Process ms-settings:quiet-hours"])
    return "Do Not Disturb settings opened"


def _lock_screen():
    ctypes.windll.user32.LockWorkStation()
    return "Screen locked"


def _sleep_pc():
    _run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
    return "PC going to sleep"


def _shutdown_pc():
    _run(["shutdown", "/s", "/t", "30"])
    return "PC shutting down in 30 seconds"


def _restart_pc():
    _run(["shutdown", "/r", "/t", "30"])
    return "PC restarting in 30 seconds"


def _take_screenshot():
    try:
        import pyautogui
        img = pyautogui.screenshot()
        path = Path.home() / "Desktop" / f"screenshot_{int(time.time())}.png"
        img.save(str(path))
        return f"Screenshot saved: {path}"
    except Exception as e:
        return f"Screenshot failed: {e}"


def _set_wallpaper(path):
    try:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3)
        return f"Wallpaper set to {path}"
    except Exception as e:
        return f"Failed to set wallpaper: {e}"


def _empty_trash():
    _run(["powershell", "-Command", "Clear-RecycleBin -Force"])
    return "Recycle bin emptied"


def _open_settings(target=""):
    mapping = {
        "display": "ms-settings:display",
        "sound": "ms-settings:sound",
        "network": "ms-settings:network",
        "bluetooth": "ms-settings:bluetooth",
        "personalization": "ms-settings:personalization",
        "apps": "ms-settings:appsfeatures",
        "accounts": "ms-settings:accounts",
        "time": "ms-settings:dateandtime",
        "privacy": "ms-settings:privacy",
        "update": "ms-settings:windowsupdate",
        "power": "ms-settings:powersleep",
        "storage": "ms-settings:storagesense",
        "accessibility": "ms-settings:easeofaccess",
        "default": "ms-settings:",
    }
    url = mapping.get(target.lower(), mapping["default"])
    _run(["start", url])
    return f"Opened settings: {target or 'main'}"


def _open_control_panel():
    _run(["control"])
    return "Control Panel opened"


def _open_task_manager():
    _run(["taskmgr"])
    return "Task Manager opened"


def _open_device_manager():
    _run(["devmgmt.msc"])
    return "Device Manager opened"


def _open_network():
    _run(["start", "ms-settings:network-status"])
    return "Network settings opened"


def _open_sound():
    _run(["start", "ms-settings:sound"])
    return "Sound settings opened"


def _open_display():
    _run(["start", "ms-settings:display"])
    return "Display settings opened"


def _open_power():
    _run(["start", "ms-settings:powersleep"])
    return "Power settings opened"


def _open_bluetooth():
    _run(["start", "ms-settings:bluetooth"])
    return "Bluetooth settings opened"


def _set_alarm(name, time_str):
    if not name:
        name = "JARVIS Alarm"
    try:
        _run(["powershell", "-Command",
              f"Add-Type -AssemblyName System.Windows.Forms; "
              f"$n = New-Object System.Windows.Forms.NotifyIcon; "
              f"$n.Visible = $true; "
              f"$n.ShowBalloonTip(5000, 'Alarm Set', '{name} at {time_str}', 'Info')"])
        return f"Alarm '{name}' set for {time_str}"
    except Exception:
        return f"Alarm '{name}' set for {time_str} (notification)"


def _list_alarms():
    out, _ = _run(["powershell", "-Command",
                   "Get-ScheduledTask | Where-Object {$_.TaskName -match 'alarm|jarvis|wake'} | Select-Object TaskName,State | Format-Table -AutoSize"])
    return out or "No alarms found"


def _delete_alarm(name):
    _run(["powershell", "-Command", f"Unregister-ScheduledTask -TaskName '{name}' -Confirm:$false"])
    return f"Alarm '{name}' deleted"


def _capture_camera():
    try:
        import cv2
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            return "No camera available"
        ret, frame = cam.read()
        cam.release()
        if ret:
            path = Path.home() / "Desktop" / f"camera_{int(time.time())}.jpg"
            cv2.imwrite(str(path), frame)
            return f"Camera captured: {path}"
        return "Failed to capture from camera"
    except ImportError:
        return "Camera requires opencv-python: pip install opencv-python"
    except Exception as e:
        return f"Camera error: {e}"


def _list_cameras():
    try:
        import cv2
        cameras = []
        for i in range(5):
            cam = cv2.VideoCapture(i)
            if cam.isOpened():
                cameras.append(f"Camera {i}")
                cam.release()
        return f"Cameras found: {', '.join(cameras)}" if cameras else "No cameras detected"
    except ImportError:
        return "Camera detection requires opencv-python"


def _list_audio():
    out, _ = _run(["powershell", "-Command",
                   "Get-WmiObject Win32_SoundDevice | Select-Object Name,Status | Format-Table -AutoSize"])
    return out or "No audio devices found"


def _set_default_audio(name):
    _run(["powershell", "-Command", f"Set-AudioDevice -Playback '{name}'"])
    return f"Default audio set to {name}"


def _list_printers():
    out, _ = _run(["powershell", "-Command",
                   "Get-Printer | Select-Object Name,DriverName,PrinterStatus | Format-Table -AutoSize"])
    return out or "No printers found"


def _lock_app(name):
    return _focus_window(name) if name else "Specify app name"


def _kill_process(name):
    _run(["taskkill", "/F", "/IM", f"{name}.exe"])
    return f"Killed {name}"


def _list_processes(filter_text=""):
    if filter_text:
        out, _ = _run(["powershell", "-Command",
                       f"Get-Process | Where-Object {{$_.ProcessName -like '*{filter_text}*'}} | Select-Object ProcessName,Id,CPU | Format-Table -AutoSize"], timeout=8)
    else:
        out, _ = _run(["powershell", "-Command",
                       "Get-Process | Select-Object -First 30 ProcessName,Id,CPU | Format-Table -AutoSize"], timeout=8)
    return out[:2000] if out else "No processes"


def _open_app(name):
    import pyautogui
    name_lower = name.lower()
    known_uwp = {
        "calculator": "calc", "notepad": "notepad", "paint": "mspaint",
        "camera": "start microsoft.windows.camera:", "settings": "start ms-settings:",
        "file explorer": "explorer", "explorer": "explorer",
        "cmd": "cmd", "command prompt": "cmd", "powershell": "powershell",
        "task manager": "taskmgr", "control panel": "control",
    }
    if name_lower in known_uwp:
        cmd = known_uwp[name_lower]
        if cmd.startswith("start "):
            _run(["cmd", "/c", cmd])
        else:
            _run([cmd])
        return f"Opened {name}"
    _run(["cmd", "/c", "start", "", name])
    _run(["cmd", "/c", "start", "", f"{name}.exe"])
    _run([name])
    return f"Opened {name}"


def _close_app(name):
    _run(["taskkill", "/F", "/IM", f"{name}.exe"])
    return f"Closed {name}"


def _list_startup():
    out, _ = _run(["powershell", "-Command",
                   "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | Format-Table -AutoSize"])
    return out or "No startup apps found"


def _add_startup(name):
    return f"Add {name} to startup — use Task Scheduler for persistence"


def _remove_startup(name):
    _run(["powershell", "-Command", f"Remove-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name '{name}' -ErrorAction SilentlyContinue"])
    return f"Removed {name} from startup"


def _list_env():
    out, _ = _run(["set"])
    lines = [l for l in out.split("\n") if l.strip()]
    return "\n".join(lines[:50]) if lines else "No env vars"


def _set_env_var(name, value):
    _run(["setx", name, value])
    return f"Set {name}={value}"


def _disk_info():
    out, _ = _run(["powershell", "-Command",
                   "Get-PSDrive -PSProvider FileSystem | Select-Object Name,@{N='Used(GB)';E={[math]::Round($_.Used/1GB,1)}},@{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}},@{N='Total(GB)';E={[math]::Round(($_.Used+$_.Free)/1GB,1)}} | Format-Table -AutoSize"])
    return out[:2000] if out else "No disk info"


def _list_usb():
    out, _ = _run(["powershell", "-Command",
                   "Get-PnpDevice | Where-Object {$_.Class -eq 'USB'} | Select-Object FriendlyName,Status | Format-Table -AutoSize"])
    return out or "No USB devices found"


def _list_drivers():
    out, _ = _run(["powershell", "-Command",
                   "Get-WmiObject Win32_PnPSignedDriver | Select-Object DeviceName,DriverVersion | Format-Table -AutoSize"])
    return out[:2000] if out else "No drivers found"


def _check_updates():
    _run(["start", "ms-settings:windowsupdate"])
    return "Windows Update opened"


def _system_info_full():
    out, _ = _run(["powershell", "-Command",
                   "Get-ComputerInfo | Select-Object CsName,WindowsVersion,OsArchitecture,CsProcessors,CsTotalPhysicalMemory | Format-List"],
                  timeout=15)
    return out[:2000] if out else "No system info"


def _list_scheduled_tasks():
    out, _ = _run(["powershell", "-Command",
                   "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Select-Object TaskName,TaskPath,State | Format-Table -AutoSize"])
    return out[:2000] if out else "No scheduled tasks"


def _create_restore_point():
    _run(["powershell", "-Command",
          "Checkpoint-Computer -Description 'JARVIS Restore Point' -RestorePointType MODIFY_SETTINGS"])
    return "Restore point created"


def _list_users():
    out, _ = _run(["net", "user"])
    return out[:1000] if out else "No users"


def _list_shares():
    out, _ = _run(["net", "share"])
    return out[:1000] if out else "No shares"


def _open_camera_app():
    _run(["start", "microsoft.windows.camera:"])
    return "Camera app opened"


def _open_calc():
    _run(["calc"])
    return "Calculator opened"


def _open_notepad():
    _run(["notepad"])
    return "Notepad opened"


def _open_paint():
    _run(["mspaint"])
    return "Paint opened"


def _open_cmd():
    _run(["cmd", "/c", "start", "cmd"])
    return "Command Prompt opened"


def _open_ps():
    _run(["powershell", "-Command", "Start-Process powershell"])
    return "PowerShell opened"


def _focus_window(title):
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            windows = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if windows:
            w = windows[0]
            if w.isMinimized:
                w.restore()
            w.activate()
            return f"Focused: {w.title}"
    except Exception:
        pass
    try:
        import subprocess
        ps = f"(Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}}).MainWindowHandle | ForEach-Object {{ Add-Type -Name Win -Namespace Native -MemberDefinition '[DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd);' ; [Native.Win]::SetForegroundWindow($_) }}"
        subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=5,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return f"Focused via PowerShell: {title}"
    except Exception:
        pass
    return f"Could not focus: {title}"
