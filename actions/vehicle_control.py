"""
Vehicle Integration Module for JARVIS.
Tesla API, OBD-II, GPS tracking, vehicle status.
Requires: requests (installed), optional teslajson, obd packages
"""
import os
import time
import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_VEHICLE_CONFIG = _DATA_DIR / "vehicle_config.json"

def handle(params=None):
    params = params or {}
    action = params.get("action", "status")
    
    if action == "tesla_status":
        return _tesla_status(params)
    elif action == "tesla_unlock":
        return _tesla_command(params, "unlock")
    elif action == "tesla_lock":
        return _tesla_command(params, "lock")
    elif action == "tesla_climate":
        return _tesla_climate(params)
    elif action == "tesla_location":
        return _tesla_location(params)
    elif action == "tesla_charge":
        return _tesla_charge_status(params)
    elif action == "obd_read":
        return _obd_read(params)
    elif action == "obd_codes":
        return _obd_read_codes(params)
    elif action == "gps_track":
        return _gps_track(params)
    elif action == "setup":
        return _setup_vehicle(params)
    elif action == "status":
        return _vehicle_overview()
    else:
        return "Vehicle: tesla_status|tesla_unlock|tesla_lock|tesla_climate|tesla_location|tesla_charge|obd_read|obd_codes|gps_track|setup|status"

def _load_config():
    try:
        if _VEHICLE_CONFIG.exists():
            return json.loads(_VEHICLE_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_config(config):
    _VEHICLE_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")

def _setup_vehicle(params):
    config = {
        "type": params.get("type", "tesla"),
        "tesla_token": params.get("tesla_token", ""),
        "tesla_email": params.get("tesla_email", ""),
        "obd_port": params.get("obd_port", "COM3"),
        "gps_device": params.get("gps_device", ""),
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_config(config)
    return f"Vehicle configured: {config['type']}"

def _tesla_status(params):
    config = _load_config()
    token = config.get("tesla_token", "")
    if not token:
        return "Tesla API token not configured. Use: Vehicle setup with tesla_token."
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get("https://owner-api.teslamotors.com/api/1/vehicles", headers=headers, timeout=10)
        if r.status_code == 200:
            vehicles = r.json().get("response", [])
            if vehicles:
                v = vehicles[0]
                vid = v["id"]
                r2 = requests.get(f"https://owner-api.teslamotors.com/api/1/vehicles/{vid}/vehicle_data", headers=headers, timeout=10)
                if r2.status_code == 200:
                    data = r2.json().get("response", {})
                    state = data.get("state", "unknown")
                    battery = data.get("charge_state", {}).get("battery_level", "?")
                    range_m = data.get("charge_state", {}).get("battery_range", "?")
                    temp = data.get("climate_state", {}).get("inside_temp", "?")
                    locked = data.get("vehicle_state", {}).get("locked", "?")
                    return f"Tesla: {state}, Battery: {battery}%, Range: {range_m}mi, Interior: {temp}°C, Locked: {locked}"
                return f"Tesla vehicle found but data fetch failed (status {r2.status_code})"
            return "No Tesla vehicles found"
        return f"Tesla API error: {r.status_code} {r.text[:200]}"
    except ImportError:
        return "requests not installed"
    except Exception as e:
        return f"Tesla error: {e}"

def _tesla_command(params, command):
    config = _load_config()
    token = config.get("tesla_token", "")
    if not token:
        return "Tesla API token not configured"
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get("https://owner-api.teslamotors.com/api/1/vehicles", headers=headers, timeout=10)
        if r.status_code == 200:
            vehicles = r.json().get("response", [])
            if vehicles:
                vid = vehicles[0]["id"]
                r2 = requests.post(f"https://owner-api.teslamotors.com/api/1/vehicles/{vid}/command/{command}", headers=headers, timeout=10)
                if r2.status_code == 200:
                    result = r2.json().get("response", {})
                    return f"Tesla {command}: {result.get('result', 'unknown')}"
                return f"Tesla {command} failed: {r2.status_code}"
        return "Could not connect to Tesla"
    except Exception as e:
        return f"Tesla command error: {e}"

def _tesla_climate(params):
    config = _load_config()
    token = config.get("tesla_token", "")
    if not token:
        return "Tesla API token not configured"
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get("https://owner-api.teslamotors.com/api/1/vehicles", headers=headers, timeout=10)
        if r.status_code == 200:
            vehicles = r.json().get("response", [])
            if vehicles:
                vid = vehicles[0]["id"]
                temp = params.get("temperature", 22)
                r2 = requests.post(f"https://owner-api.teslamotors.com/api/1/vehicles/{vid}/command/set_temps", headers=headers, json={"driver_temp": temp, "passenger_temp": temp}, timeout=10)
                return f"Tesla climate set to {temp}°C (status {r2.status_code})"
        return "Could not connect to Tesla"
    except Exception as e:
        return f"Tesla climate error: {e}"

def _tesla_location(params):
    config = _load_config()
    token = config.get("tesla_token", "")
    if not token:
        return "Tesla API token not configured"
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get("https://owner-api.teslamotors.com/api/1/vehicles", headers=headers, timeout=10)
        if r.status_code == 200:
            vehicles = r.json().get("response", [])
            if vehicles:
                vid = vehicles[0]["id"]
                r2 = requests.get(f"https://owner-api.teslamotors.com/api/1/vehicles/{vid}/vehicle_data", headers=headers, timeout=10)
                if r2.status_code == 200:
                    data = r2.json().get("response", {})
                    loc = data.get("drive_state", {})
                    lat = loc.get("latitude", "?")
                    lon = loc.get("longitude", "?")
                    speed = loc.get("speed", "?")
                    return f"Tesla location: {lat}, {lon}, Speed: {speed}mph"
                return "Could not fetch location"
        return "Could not connect to Tesla"
    except Exception as e:
        return f"Tesla location error: {e}"

def _tesla_charge_status(params):
    config = _load_config()
    token = config.get("tesla_token", "")
    if not token:
        return "Tesla API token not configured"
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get("https://owner-api.teslamotors.com/api/1/vehicles", headers=headers, timeout=10)
        if r.status_code == 200:
            vehicles = r.json().get("response", [])
            if vehicles:
                vid = vehicles[0]["id"]
                r2 = requests.get(f"https://owner-api.teslamotors.com/api/1/vehicles/{vid}/vehicle_data", headers=headers, timeout=10)
                if r2.status_code == 200:
                    charge = r2.json().get("response", {}).get("charge_state", {})
                    level = charge.get("battery_level", "?")
                    range_m = charge.get("battery_range", "?")
                    charging = charge.get("charging_state", "Disconnected")
                    limit = charge.get("charge_limit_soc", "?")
                    return f"Charge: {level}% ({range_m}mi), State: {charging}, Limit: {limit}%"
                return "Could not fetch charge status"
        return "Could not connect to Tesla"
    except Exception as e:
        return f"Tesla charge error: {e}"

def _obd_read(params):
    try:
        import obd
        port = params.get("port", _load_config().get("obd_port", "COM3"))
        connection = obd.OBD(port)
        if params.get("command"):
            cmd = getattr(obd.commands, params["command"].upper(), None)
            if cmd:
                result = connection.query(cmd)
                return f"{params['command']}: {result.value}"
            return f"Unknown OBD command: {params['command']}"
        commands = ["RPM", "SPEED", "COOLANT_TEMP", "ENGINE_LOAD", "THROTTLE_POS", "FUEL_LEVEL"]
        results = []
        for cmd_name in commands:
            cmd = getattr(obd.commands, cmd_name, None)
            if cmd:
                r = connection.query(cmd)
                if not r.is_null():
                    results.append(f"{cmd_name}: {r.value}")
        connection.close()
        return "\n".join(results) if results else "No OBD data"
    except ImportError:
        return "obd package not installed. Run: pip install obd"
    except Exception as e:
        return f"OBD error: {e}"

def _obd_read_codes(params):
    try:
        import obd
        port = params.get("port", _load_config().get("obd_port", "COM3"))
        connection = obd.OBD(port)
        codes = connection.query(obd.commands.GET_DTC)
        connection.close()
        if codes.value:
            return f"DTC codes: {codes.value}"
        return "No diagnostic trouble codes"
    except ImportError:
        return "obd package not installed"
    except Exception as e:
        return f"OBD DTC error: {e}"

def _gps_track(params):
    try:
        import serial
        port = params.get("port", "COM4")
        baud = params.get("baud", 9600)
        ser = serial.Serial(port, baud, timeout=5)
        for _ in range(20):
            line = ser.readline().decode("ascii", errors="ignore").strip()
            if line.startswith("$GPRMC"):
                parts = line.split(",")
                if len(parts) > 5 and parts[2] == "A":
                    lat = _nmea_to_decimal(parts[3], parts[4])
                    lon = _nmea_to_decimal(parts[5], parts[6])
                    return f"GPS: {lat}, {lon}"
        ser.close()
        return "No valid GPS fix"
    except ImportError:
        return "pyserial not installed. Run: pip install pyserial"
    except Exception as e:
        return f"GPS error: {e}"

def _nmea_to_decimal(coord, direction):
    try:
        if len(coord) < 4:
            return coord
        if direction in ("N", "S"):
            deg = int(coord[:2])
            minutes = float(coord[2:])
        else:
            deg = int(coord[:3])
            minutes = float(coord[3:])
        decimal = deg + minutes / 60
        if direction in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return coord

def _vehicle_overview():
    config = _load_config()
    if not config:
        return "No vehicle configured. Use: Vehicle setup with type, tesla_token, etc."
    return f"Vehicle: {config.get('type', 'unknown')}, Token: {'set' if config.get('tesla_token') else 'not set'}"
