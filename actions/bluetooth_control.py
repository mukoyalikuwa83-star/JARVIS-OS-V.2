"""Bluetooth control: scan, pair, connect, disconnect, list devices, toggle on/off."""

import json
import subprocess
import sys
import time

_OS = sys.platform


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def bt_status(params=None):
    if _OS == "win32":
        out, rc = _run(["powershell", "-Command",
                         "Get-PnpDevice -Class Bluetooth | Select-Object Status,FriendlyName | ConvertTo-Json"])
        if out:
            try:
                devices = json.loads(out)
                if isinstance(devices, dict):
                    devices = [devices]
                online = any(d.get("Status") == "OK" for d in devices)
                return json.dumps({"enabled": online, "device_count": len(devices),
                                   "devices": [{"name": d.get("FriendlyName", "?"), "status": d.get("Status", "?")} for d in devices[:15]]})
            except Exception:
                pass
        return json.dumps({"enabled": None, "raw": out[:300]})
    elif _OS == "darwin":
        out, _ = _run(["blueutil", "--power"])
        return json.dumps({"enabled": out.strip() == "1"})
    else:
        out, _ = _run(["bluetoothctl", "show"])
        enabled = "Powered: yes" in out
        return json.dumps({"enabled": enabled, "raw": out[:400]})


def bt_scan(params=None):
    duration = int(params.get("duration", 8)) if params else 8
    if _OS == "win32":
        out, _ = _run(["powershell", "-Command",
                        "Get-PnpDevice -Class Bluetooth -Status OK | "
                        "Select-Object FriendlyName,InstanceId | ConvertTo-Json"])
        devices = []
        if out:
            try:
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]
                devices = [{"name": d.get("FriendlyName", "?"), "id": d.get("InstanceId", "?")} for d in data]
            except Exception:
                pass
        return json.dumps({"devices": devices, "note": "Windows shows currently paired/visible devices"})
    elif _OS == "darwin":
        out, _ = _run(["system_profiler", "SPBluetoothDataType", "-json"], timeout=duration + 5)
        if out:
            try:
                data = json.loads(out)
                bt = data.get("SPBluetoothDataType", [])
                devices = []
                for item in bt:
                    for key in ("device_name", "name"):
                        if key in item:
                            devices.append({"name": item[key], "address": item.get("MAC Address", "unknown")})
                return json.dumps({"devices": devices[:20]})
            except Exception:
                pass
        return json.dumps({"devices": [], "raw": out[:300]})
    else:
        proc_out, _ = _run(["timeout", str(duration), "bluetoothctl", "scan", "on"], timeout=duration + 3)
        out2, _ = _run(["bluetoothctl", "devices"])
        devices = []
        if out2:
            for line in out2.split("\n"):
                if line.startswith("Device "):
                    parts = line.split(" ", 2)
                    if len(parts) >= 3:
                        devices.append({"address": parts[1], "name": parts[2]})
        return json.dumps({"devices": devices[:20]})


def bt_connect(params=None):
    address = (params or {}).get("address", "")
    name = (params or {}).get("name", "")
    if not address and not name:
        return json.dumps({"error": "Provide 'address' (MAC) or 'name' of the device to connect."})
    if _OS == "win32":
        if name and not address:
            out, _ = _run(["powershell", "-Command",
                           f"Get-PnpDevice -Class Bluetooth | Where-Object {{$_.FriendlyName -like '*{name}*'}} | "
                           "Select-Object -First 1 InstanceId | ConvertTo-Json"])
            if out:
                try:
                    d = json.loads(out)
                    address = d.get("InstanceId", name)
                except Exception:
                    address = name
        return json.dumps({"result": f"Connecting to {address or name}...",
                           "note": "Windows Bluetooth connection is managed by the OS. The device should appear in Settings > Bluetooth."})
    elif _OS == "darwin":
        out, _ = _run(["blueutil", "--connect", address] if address else ["blueutil", "--connect", name])
        return json.dumps({"result": f"Connection {'succeeded' if not out else 'attempted'}: {address or name}", "raw": out})
    else:
        out, _ = _run(["bluetoothctl", "connect", address] if address else ["bluetoothctl", "connect", name])
        return json.dumps({"result": f"Connected: {address or name}" if "successful" in out.lower() else out[:200]})


def bt_disconnect(params=None):
    address = (params or {}).get("address", "")
    name = (params or {}).get("name", "")
    if not address and not name:
        return json.dumps({"error": "Provide 'address' or 'name'."})
    if _OS == "win32":
        return json.dumps({"result": "Use Windows Settings > Bluetooth to disconnect devices.", "attempted": address or name})
    elif _OS == "darwin":
        out, _ = _run(["blueutil", "--disconnect", address] if address else ["blueutil", "--disconnect", name])
        return json.dumps({"result": "Disconnected" if not out else out[:200]})
    else:
        out, _ = _run(["bluetoothctl", "disconnect", address] if address else ["bluetoothctl", "disconnect", name])
        return json.dumps({"result": "Disconnected" if "successful" in out.lower() else out[:200]})


def bt_toggle(params=None):
    enable = (params or {}).get("enable")
    if _OS == "win32":
        if enable is None:
            status = json.loads(bt_status())
            enable = not status.get("enabled", True)
        action = "Enable" if enable else "Disable"
        out, _ = _run(["powershell", "-Command",
                        f"Get-PnpDevice -Class Bluetooth | "
                        f"{'Enable-PnpDevice' if enable else 'Disable-PnpDevice'} -Confirm:$false"])
        return json.dumps({"enabled": enable, "result": f"Bluetooth {action.lower()}d"})
    elif _OS == "darwin":
        state = "1" if enable else "0"
        if enable is None:
            current = _run(["blueutil", "--power"])[0].strip()
            state = "0" if current == "1" else "1"
        _run(["blueutil", "--power", state])
        return json.dumps({"enabled": state == "1"})
    else:
        state = "on" if enable else "off"
        if enable is None:
            current = _run(["bluetoothctl", "show"])[0]
            state = "off" if "Powered: yes" in current else "on"
        _run(["bluetoothctl", "power", state])
        return json.dumps({"enabled": state == "on"})


def bt_pair(params=None):
    address = (params or {}).get("address", "")
    if not address:
        return json.dumps({"error": "Provide device 'address' (MAC) to pair."})
    if _OS == "win32":
        return json.dumps({"result": f"Pairing initiated for {address}. Accept any OS pairing prompt.",
                           "note": "Windows will show a pairing dialog if the device requests PIN confirmation."})
    elif _OS == "darwin":
        out, _ = _run(["blueutil", "--pair", address])
        return json.dumps({"result": "Pairing initiated" if not out else out[:200], "address": address})
    else:
        out, _ = _run(["bluetoothctl", "pair", address])
        return json.dumps({"result": "Paired" if "successful" in out.lower() else out[:200], "address": address})


ACTIONS = {
    "status": bt_status,
    "scan": bt_scan,
    "connect": bt_connect,
    "disconnect": bt_disconnect,
    "toggle": bt_toggle,
    "pair": bt_pair,
}


def handle(parameters=None, **_kwargs):
    action = str((parameters or {}).get("action", "status")).lower()
    fn = ACTIONS.get(action)
    if fn:
        return fn(parameters)
    return json.dumps({"error": f"Unknown action: {action}. Valid: {', '.join(ACTIONS)}"})
