"""WiFi control: scan, connect, disconnect, show profiles, speed test, IP info."""

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


def wifi_status(params=None):
    info = {}
    if _OS == "win32":
        out, _ = _run(["netsh", "wlan", "show", "interfaces"])
        if out:
            for line in out.split("\n"):
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    kl = k.lower().replace(" ", "_")
                    if kl in ("ssid", "state", "signal", "radio_type", "authentication", "channel", "bssid", "receive_rate", "transmit_rate"):
                        info[kl] = v
        out2, _ = _run(["powershell", "-Command",
                         "Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -ne '127.0.0.1'} | "
                         "Select-Object -First 1 IPAddress | ConvertTo-Json"])
        if out2:
            try:
                info["ip_address"] = json.loads(out2).get("IPAddress")
            except Exception:
                pass
        gateway_out, _ = _run(["powershell", "-Command",
                               "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -First 1).NextHop"])
        if gateway_out:
            info["gateway"] = gateway_out
        dns_out, _ = _run(["powershell", "-Command",
                           "Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object -ExpandProperty ServerAddresses | Select-Object -First 3 | ConvertTo-Json"])
        if dns_out:
            try:
                info["dns"] = json.loads(dns_out) if dns_out.startswith("[") else [dns_out]
            except Exception:
                info["dns"] = [dns_out]
    elif _OS == "darwin":
        out, _ = _run(["networksetup", "-getairportnetwork", "en0"])
        info["connected_network"] = out.replace("Current Wi-Fi Network: ", "") if out else "not connected"
        ip_out, _ = _run(["ipconfig", "getifaddr", "en0"])
        info["ip_address"] = ip_out.strip() if ip_out else None
    else:
        out, _ = _run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY,BSSID", "dev", "wifi"])
        if out:
            for line in out.split("\n"):
                parts = line.split(":")
                if len(parts) >= 5 and parts[0] == "yes":
                    info.update({"ssid": parts[1], "signal": parts[2] + "%", "security": parts[3], "bssid": parts[4]})
        ip_out, _ = _run(["hostname", "-I"])
        info["ip_address"] = ip_out.split()[0] if ip_out else None
    return json.dumps(info)


def wifi_scan(params=None):
    networks = []
    if _OS == "win32":
        out, _ = _run(["netsh", "wlan", "show", "networks", "mode=bssid"])
        if out:
            current_ssid = None
            for line in out.split("\n"):
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    current_ssid = line.split(":", 1)[-1].strip()
                elif current_ssid and line.startswith("Signal"):
                    signal = line.split(":", 1)[-1].strip()
                    networks.append({"ssid": current_ssid, "signal": signal})
                    current_ssid = None
    elif _OS == "darwin":
        out, _ = _run(["airport", "-s"], timeout=10)
        if out:
            for line in out.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    networks.append({"ssid": parts[0], "signal": parts[2] + "dB", "security": " ".join(parts[3:]) if len(parts) > 3 else ""})
    else:
        out, _ = _run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"], timeout=15)
        if out:
            seen = set()
            for line in out.split("\n"):
                parts = line.split(":")
                if len(parts) >= 3 and parts[0] and parts[0] not in seen:
                    seen.add(parts[0])
                    networks.append({"ssid": parts[0], "signal": parts[1] + "%", "security": parts[2]})
    return json.dumps({"networks": networks[:30]})


def wifi_connect(params=None):
    ssid = (params or {}).get("ssid", "")
    password = (params or {}).get("password", "")
    if not ssid:
        return json.dumps({"error": "Provide 'ssid' to connect."})
    if _OS == "win32":
        if password:
            profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM><security><authEncryption>
        <authentication>WPA2PSK</authentication>
        <encryption>AES</encryption>
        <useOneX>false</useOneX>
    </authEncryption>
    <sharedKey><keyType>passPhrase</keyType><protected>false</protected>
        <keyMaterial>{password}</keyMaterial>
    </sharedKey></security></MSM>
</WLANProfile>"""
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
                f.write(profile_xml)
                profile_path = f.name
            _run(["netsh", "wlan", "add", "profile", f"filename={profile_path}"])
            _run(["netsh", "wlan", "connect", f"name={ssid}"])
            try:
                import os
                os.unlink(profile_path)
            except Exception:
                pass
            return json.dumps({"result": f"Connecting to '{ssid}'...", "ssid": ssid})
        else:
            _run(["netsh", "wlan", "connect", f"name={ssid}"])
            return json.dumps({"result": f"Connecting to '{ssid}' (open or previously saved)...", "ssid": ssid})
    elif _OS == "darwin":
        if password:
            _run(["networksetup", "-setairportnetwork", "en0", ssid, password])
        else:
            _run(["networksetup", "-setairportnetwork", "en0", ssid])
        return json.dumps({"result": f"Connecting to '{ssid}'..."})
    else:
        if password:
            out, rc = _run(["nmcli", "dev", "wifi", "connect", ssid, "password", password])
        else:
            out, rc = _run(["nmcli", "dev", "wifi", "connect", ssid])
        success = rc == 0
        return json.dumps({"result": f"{'Connected' if success else 'Failed'}: {ssid}", "detail": out[:200]})


def wifi_disconnect(params=None):
    if _OS == "win32":
        out, _ = _run(["netsh", "wlan", "disconnect"])
        return json.dumps({"result": "Disconnected" if "disconnected" in out.lower() else out[:200]})
    elif _OS == "darwin":
        _run(["networksetup", "-setairportnetwork", "en0", ""])
        return json.dumps({"result": "Disconnected from WiFi"})
    else:
        out, _ = _run(["nmcli", "dev", "disconnect", "wlan0"])
        return json.dumps({"result": "Disconnected" if out else "Failed"})


def wifi_profiles(params=None):
    profiles = []
    if _OS == "win32":
        out, _ = _run(["netsh", "wlan", "show", "profiles"])
        if out:
            for line in out.split("\n"):
                if "All User Profile" in line or "All Users Profile" in line:
                    name = line.split(":", 1)[-1].strip() if ":" in line else ""
                    if name:
                        profiles.append(name)
    elif _OS == "linux":
        out, _ = _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
        if out:
            for line in out.split("\n"):
                parts = line.split(":")
                if len(parts) >= 2 and "wifi" in parts[1].lower():
                    profiles.append(parts[0])
    return json.dumps({"profiles": profiles})


def wifi_toggle(params=None):
    enable = (params or {}).get("enable")
    if _OS == "win32":
        if enable is None:
            out, _ = _run(["netsh", "wlan", "show", "interfaces"])
            enabled = "State                  : connected" in out or "State                  : disconnected" in out
            enable = not enabled
        action = "Enable" if enable else "Disable"
        if enable:
            _run(["powershell", "-Command",
                  "Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'} | Enable-NetAdapter -Confirm:$false"])
        else:
            _run(["powershell", "-Command",
                  "Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'} | Disable-NetAdapter -Confirm:$false"])
        return json.dumps({"enabled": enable, "result": f"WiFi {action.lower()}d"})
    elif _OS == "darwin":
        state = "on" if enable else "off"
        if enable is None:
            current = _run(["networksetup", "-getairportpower", "en0"])[0]
            state = "off" if "On" in current else "on"
        _run(["networksetup", "-setairportpower", "en0", state])
        return json.dumps({"enabled": state == "on"})
    else:
        state = "on" if enable else "off"
        if enable is None:
            current = _run(["nmcli", "radio", "wifi"])[0]
            state = "off" if "enabled" in current else "on"
        _run(["nmcli", "radio", "wifi", state])
        return json.dumps({"enabled": state == "on"})


ACTIONS = {
    "status": wifi_status,
    "scan": wifi_scan,
    "connect": wifi_connect,
    "disconnect": wifi_disconnect,
    "profiles": wifi_profiles,
    "toggle": wifi_toggle,
}


def handle(parameters=None, **_kwargs):
    action = str((parameters or {}).get("action", "status")).lower()
    fn = ACTIONS.get(action)
    if fn:
        return fn(parameters)
    return json.dumps({"error": f"Unknown action: {action}. Valid: {', '.join(ACTIONS)}"})
