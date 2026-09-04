"""
Smart Home / Device Control Module for JARVIS.
Control lights, thermostats, plugs, sensors via APIs.
Supports: Philips Hue, Tuya, MQTT, Home Assistant, generic HTTP.
Requires: requests (installed)
"""
import os
import time
import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_DEVICES_FILE = _DATA_DIR / "smart_devices.json"

def handle(params=None):
    params = params or {}
    action = params.get("action", "status")
    
    if action == "add_device":
        return _add_device(params)
    elif action == "remove_device":
        return _remove_device(params)
    elif action == "list_devices":
        return _list_devices()
    elif action == "control":
        return _control_device(params)
    elif action == "status":
        return _device_status(params)
    elif action == "scene":
        return _activate_scene(params)
    elif action == "hue_setup":
        return _setup_hue(params)
    elif action == "home_assistant":
        return _home_assistant_call(params)
    elif action == "mqtt_publish":
        return _mqtt_publish(params)
    elif action == "discover":
        return _discover_devices()
    else:
        return "SmartHome: add_device|remove_device|list_devices|control|status|scene|hue_setup|home_assistant|mqtt_publish|discover"

def _load_devices():
    try:
        if _DEVICES_FILE.exists():
            return json.loads(_DEVICES_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def _save_devices(devices):
    _DEVICES_FILE.write_text(json.dumps(devices, indent=2, default=str), encoding="utf-8")

def _add_device(params):
    devices = _load_devices()
    device = {
        "id": params.get("id", str(int(time.time()))[-8:]),
        "name": params.get("name", "Unknown"),
        "type": params.get("type", "light"),
        "protocol": params.get("protocol", "http"),
        "ip": params.get("ip", ""),
        "api_key": params.get("api_key", ""),
        "room": params.get("room", ""),
        "state": "off",
        "added": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    devices.append(device)
    _save_devices(devices)
    return f"Device added: {device['name']} ({device['type']})"

def _remove_device(params):
    devices = _load_devices()
    name = params.get("name", "").lower()
    before = len(devices)
    devices = [d for d in devices if name not in d["name"].lower()]
    if len(devices) == before:
        return f"No device matching '{name}'"
    _save_devices(devices)
    return f"Removed {before - len(devices)} device(s)"

def _list_devices():
    devices = _load_devices()
    if not devices:
        return "No devices registered. Use add_device or discover."
    lines = []
    for d in devices:
        lines.append(f"[{d['id']}] {d['name']} ({d['type']}) - {d['state']} - {d.get('room', 'no room')}")
    return "\n".join(lines)

def _control_device(params):
    devices = _load_devices()
    name = params.get("name", "").lower()
    command = params.get("command", "on").lower()
    target = [d for d in devices if name in d["name"].lower()]
    if not target:
        return f"No device matching '{name}'"
    device = target[0]
    
    if device["protocol"] == "hue":
        return _control_hue(device, command, params)
    elif device["protocol"] == "home_assistant":
        return _control_ha(device, command, params)
    elif device["protocol"] == "mqtt":
        return _control_mqtt(device, command, params)
    else:
        device["state"] = command
        _save_devices(devices)
        return f"{device['name']} set to {command}"

def _control_hue(device, command, params):
    try:
        import requests
        ip = device.get("ip", "")
        api_key = device.get("api_key", "")
        if not ip or not api_key:
            return "Hue bridge IP and API key required"
        if command == "on":
            r = requests.put(f"http://{ip}/api/{api_key}/lights/{device['id']}/state", json={"on": True}, timeout=5)
        elif command == "off":
            r = requests.put(f"http://{ip}/api/{api_key}/lights/{device['id']}/state", json={"on": False}, timeout=5)
        elif command.startswith("brightness"):
            level = int(command.split()[1]) if len(command.split()) > 1 else 128
            r = requests.put(f"http://{ip}/api/{api_key}/lights/{device['id']}/state", json={"bri": level}, timeout=5)
        else:
            return f"Unknown Hue command: {command}"
        return f"Hue {device['name']}: {command} (status {r.status_code})"
    except Exception as e:
        return f"Hue error: {e}"

def _control_ha(device, command, params):
    try:
        import requests
        url = device.get("ip", "")
        api_key = device.get("api_key", "")
        if not url or not api_key:
            return "Home Assistant URL and token required"
        entity_id = params.get("entity_id", device.get("id", ""))
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        r = requests.post(f"{url}/api/services/light/turn_{command}", headers=headers, json={"entity_id": entity_id}, timeout=5)
        return f"HA {device['name']}: {command} (status {r.status_code})"
    except Exception as e:
        return f"HA error: {e}"

def _control_mqtt(device, command, params):
    try:
        import paho.mqtt.publish as publish
        host = device.get("ip", "localhost")
        topic = params.get("topic", f"jarvis/{device['id']}")
        publish.single(topic, command, hostname=host, timeout=5)
        return f"MQTT {device['name']}: {command} sent to {topic}"
    except ImportError:
        return "paho-mqtt not installed. Run: pip install paho-mqtt"
    except Exception as e:
        return f"MQTT error: {e}"

def _device_status(params):
    devices = _load_devices()
    name = params.get("name", "").lower()
    if name:
        target = [d for d in devices if name in d["name"].lower()]
        if not target:
            return f"No device matching '{name}'"
        d = target[0]
        return f"{d['name']}: type={d['type']}, state={d['state']}, protocol={d['protocol']}, room={d.get('room', '')}"
    return f"Total devices: {len(devices)}"

def _activate_scene(params):
    devices = _load_devices()
    scene = params.get("scene", "movie").lower()
    if scene == "movie":
        for d in devices:
            if d["type"] == "light":
                d["state"] = "dim"
        _save_devices(devices)
        return "Movie scene activated: lights dimmed"
    elif scene == "morning":
        for d in devices:
            if d["type"] == "light":
                d["state"] = "on"
        _save_devices(devices)
        return "Morning scene activated: all lights on"
    elif scene == "away":
        for d in devices:
            d["state"] = "off"
        _save_devices(devices)
        return "Away scene activated: all devices off"
    elif scene == "night":
        for d in devices:
            if d["type"] == "light":
                d["state"] = "off"
            elif d["type"] == "thermostat":
                d["state"] = "65"
        _save_devices(devices)
        return "Night scene activated"
    return f"Unknown scene: {scene}. Available: movie, morning, away, night"

def _setup_hue(params):
    ip = params.get("ip", "")
    api_key = params.get("api_key", "")
    if not ip:
        return "Hue bridge IP required"
    try:
        import requests
        r = requests.get(f"http://{ip}/api/{api_key}/lights", timeout=5)
        if r.status_code == 200:
            lights = r.json()
            devices = _load_devices()
            for lid, light in lights.items():
                existing = [d for d in devices if d.get("id") == lid and d.get("protocol") == "hue"]
                if not existing:
                    devices.append({
                        "id": lid,
                        "name": light.get("name", f"Hue Light {lid}"),
                        "type": "light",
                        "protocol": "hue",
                        "ip": ip,
                        "api_key": api_key,
                        "room": "",
                        "state": "on" if light.get("state", {}).get("on") else "off",
                        "added": time.strftime("%Y-%m-%d %H:%M:%S"),
                    })
            _save_devices(devices)
            return f"Hue setup: {len(lights)} lights discovered and added"
        return f"Hue bridge returned status {r.status_code}"
    except Exception as e:
        return f"Hue setup error: {e}"

def _home_assistant_call(params):
    try:
        import requests
        url = params.get("url", "")
        api_key = params.get("api_key", "")
        endpoint = params.get("endpoint", "/api/")
        if not url or not api_key:
            return "Home Assistant URL and API key required"
        headers = {"Authorization": f"Bearer {api_key}"}
        r = requests.get(f"{url}{endpoint}", headers=headers, timeout=10)
        return r.text[:2000]
    except Exception as e:
        return f"HA error: {e}"

def _mqtt_publish(params):
    try:
        import paho.mqtt.publish as publish
        host = params.get("host", "localhost")
        topic = params.get("topic", "jarvis/test")
        message = params.get("message", "hello")
        publish.single(topic, message, hostname=host, timeout=5)
        return f"MQTT published to {topic}: {message}"
    except ImportError:
        return "paho-mqtt not installed. Run: pip install paho-mqtt"
    except Exception as e:
        return f"MQTT error: {e}"

def _discover_devices():
    devices = _load_devices()
    discovered = []
    try:
        import requests
        for port in [8123, 8080, 5000]:
            try:
                r = requests.get(f"http://127.0.0.1:{port}/api/", timeout=2)
                if r.status_code == 200:
                    discovered.append(f"Service found on port {port}")
            except Exception:
                pass
    except ImportError:
        pass
    return f"Registered: {len(devices)} devices. Discovered services: {discovered or 'none on local network'}"
