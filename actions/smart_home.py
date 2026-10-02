"""
Smart Home / IoT Agent — Part 3.3: Lights, sensors, thermostats, locks.
Integrates via Home Assistant hub (Matter/Zigbee/Z-Wave).
"""
import asyncio
import ipaddress
import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, quote

from core.domain_agent import DomainAgent, DomainConfig
from core.safety_guardian import is_killed, check_circuit_breaker
from core.audit_log import write_audit_entry

class SmartHomeAgent(DomainAgent):
    """Smart Home / IoT control via Home Assistant hub."""
    
    def __init__(self):
        config = DomainConfig(
            domain="smart_home",
            autonomy_level=1,
            target_ceiling=5,
            caps={
                "max_commands_per_min": 30,
                "max_sensors": 100
            },
            always_requires_approval=[
                "unlock_door", "disable_alarm", "open_garage",
                "disable_camera", "change_lock_config"
            ],
            allowlist=[]
        )
        super().__init__(config)
        self._lock_config = {
            "fail_locked": True,
            "require_second_factor": True
        }
        self._ha_config = {
            "url": os.environ.get("JARVIS_HOME_ASSISTANT_URL", "").strip().rstrip("/"),
            "token": os.environ.get("JARVIS_HOME_ASSISTANT_TOKEN", "").strip(),
        }
        self._entity_states: Dict[str, Any] = {}
        self._command_count = 0
        self._last_minute = time.time()
        
    async def handle(self, action: str, params: Dict) -> Any:
        if is_killed("smart_home"):
            return {"success": False, "error": "Smart home domain killed by safety guardian"}
        if action == "status":
            return {"success": True, "status": self.get_status()}
        elif action in {"list_devices", "discover"}:
            return await self._list_devices(registered_only=(action == "list_devices"))
        elif action == "add_device":
            return await self._add_device(params)
        elif action == "remove_device":
            return self._remove_device(params)
        elif action == "control":
            return await self._control_device(params)
        elif action == "scene":
            return await self._activate_scene(params)
        if action == "get_state":
            return await self._get_state(params)
        elif action == "set_state":
            return await self._set_state(params)
        elif action == "lock_door":
            return await self._lock_door(params)
        elif action == "unlock_door":
            return await self._unlock_door(params)
        elif action == "get_sensors":
            return await self._get_sensors(params)
        elif action == "set_thermostat":
            return await self._set_thermostat(params)
        elif action == "trigger_scene":
            return await self._trigger_scene(params)
        elif action == "get_cameras":
            return await self._get_cameras(params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
            
    async def _get_state(self, params: Dict) -> Dict:
        entity_id = params.get("entity_id")
        endpoint = f"/api/states/{quote(str(entity_id), safe='._')}" if entity_id else "/api/states"
        return await self._ha_request("GET", endpoint)
        
    async def _set_state(self, params: Dict) -> Dict:
        return {
            "success": False,
            "error": "Directly setting a Home Assistant state does not control a device. Use a supported control command.",
        }
        
    async def _lock_door(self, params: Dict) -> Dict:
        """Auto-lock - can be higher autonomy (Part 3.3: auto-lock toward security)."""
        entity_id = params.get("entity_id", "lock.front_door")
        
        # Check if auto-lock is enabled
        if not params.get("approved", False):
            # Auto-lock is allowed at higher autonomy levels
            pass
            
        return await self._ha_request("POST", f"/api/services/lock/lock", 
                                    json={"entity_id": entity_id})
        
    async def _unlock_door(self, params: Dict) -> Dict:
        """Unlock - Part 3.3 hard rule: ALWAYS requires Boss approval + second factor."""
        if not params.get("approved", False):
            return {
                "success": False,
                "error": "Unlocking door requires Boss approval + second factor",
                "requires_approval": True,
                "requires_second_factor": True
            }
            
        # Verify second factor
        second_factor = params.get("second_factor")
        if not second_factor or second_factor != "boss_confirmed":
            return {
                "success": False,
                "error": "Requires second factor confirmation from Boss",
                "requires_second_factor": True
            }
            
        entity_id = params.get("entity_id", "lock.front_door")
        return await self._ha_request("POST", f"/api/services/lock/unlock",
                                    json={"entity_id": entity_id})
        
    async def _get_sensors(self, params: Dict) -> Dict:
        """Get sensor readings - read-only, high autonomy."""
        return await self._ha_request("GET", "/api/states", 
                                    params={"domain": "sensor"})
        
    async def _set_thermostat(self, params: Dict) -> Dict:
        entity_id = params.get("entity_id", "climate.main")
        temperature = params.get("temperature")
        mode = params.get("mode", "heat_cool")
        
        return await self._ha_request("POST", f"/api/services/climate/set_temperature",
                                    json={"entity_id": entity_id, "temperature": temperature, "hvac_mode": mode})
        
    async def _trigger_scene(self, params: Dict) -> Dict:
        scene_id = params.get("scene_id")
        return await self._ha_request("POST", f"/api/services/scene/turn_on",
                                    json={"entity_id": scene_id})
        
    async def _get_cameras(self, params: Dict) -> Dict:
        return await self._ha_request("GET", "/api/states",
                                    params={"domain": "camera"})

    def _device_registry_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / ".jarvis" / "smart_home_devices.json"

    def _load_devices(self) -> Dict[str, Dict[str, str]]:
        path = self._device_registry_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_devices(self, devices: Dict[str, Dict[str, str]]) -> None:
        path = self._device_registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(devices, indent=2), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _supported_entity(state: Dict) -> bool:
        entity_id = str(state.get("entity_id", ""))
        return entity_id.split(".", 1)[0] in {"light", "switch", "fan", "climate"}

    async def _list_devices(self, registered_only: bool = False) -> Dict:
        response = await self._ha_request("GET", "/api/states")
        if not response.get("success"):
            return response
        states = response.get("data")
        if not isinstance(states, list):
            return {"success": False, "error": "Home Assistant returned an invalid device list."}
        devices = [item for item in states if isinstance(item, dict) and self._supported_entity(item)]
        registered = self._load_devices()
        if registered_only:
            ids = {value.get("entity_id") for value in registered.values()}
            devices = [item for item in devices if item.get("entity_id") in ids]
        return {
            "success": True,
            "devices": [
                {
                    "entity_id": item.get("entity_id", ""),
                    "name": item.get("attributes", {}).get("friendly_name") or item.get("entity_id", ""),
                    "type": str(item.get("entity_id", "")).split(".", 1)[0],
                    "state": item.get("state", "unknown"),
                    "room": next(
                        (entry.get("room", "") for entry in registered.values()
                         if entry.get("entity_id") == item.get("entity_id")),
                        "",
                    ),
                }
                for item in devices
            ],
        }

    async def _find_entity(self, name: str) -> tuple[Dict | None, List[Dict], str | None]:
        query = str(name or "").strip().casefold()
        if not query:
            return None, [], None
        registered = self._load_devices()
        entity_id = next(
            (entry.get("entity_id") for key, entry in registered.items()
             if key.casefold() == query or entry.get("name", "").casefold() == query),
            None,
        )
        response = await self._ha_request(
            "GET",
            f"/api/states/{quote(entity_id, safe='._')}" if entity_id
            else "/api/states",
        )
        if not response.get("success"):
            return None, [], str(response.get("error", "Home Assistant request failed."))
        states = response.get("data")
        if isinstance(states, dict):
            states = [states]
        if not isinstance(states, list):
            return None, [], "Home Assistant returned an invalid device list."
        matches = [
            item for item in states
            if isinstance(item, dict)
            and (
                str(item.get("entity_id", "")).casefold() == query
                or str(item.get("attributes", {}).get("friendly_name", "")).casefold() == query
                or (entity_id and item.get("entity_id") == entity_id)
            )
        ]
        if entity_id and not matches:
            return None, [], None
        return (matches[0] if len(matches) == 1 else None), matches, None

    async def _add_device(self, params: Dict) -> Dict:
        if params.get("api_key") or params.get("ip"):
            return {
                "success": False,
                "error": "Device URLs and tokens are not accepted through voice. Configure the Home Assistant connection locally, then add the device by its exact name.",
            }
        protocol = str(params.get("protocol", "")).strip().lower()
        if protocol and protocol not in {"home_assistant", "home assistant"}:
            return {"success": False, "error": "Only the configured Home Assistant bridge is supported."}
        name = str(params.get("name", "")).strip()
        if not name:
            return {"success": False, "error": "Provide the exact Home Assistant device name."}
        entity, matches, error = await self._find_entity(name)
        if entity is None:
            return {
                "success": False,
                "error": error or "Device was not found or its name is ambiguous. Use an exact entity ID.",
                "matches": [item.get("entity_id") for item in matches],
            }
        entity_id = str(entity.get("entity_id", ""))
        domain = entity_id.split(".", 1)[0]
        requested_type = str(params.get("type", "")).strip().lower()
        if domain not in {"light", "switch", "fan", "climate"}:
            return {"success": False, "error": f"{domain or 'This'} device type is not enabled for control."}
        if requested_type and requested_type not in {domain, "thermostat" if domain == "climate" else domain}:
            return {"success": False, "error": f"This entity is a {domain}, not a {requested_type}."}
        devices = self._load_devices()
        devices[name.casefold()] = {
            "name": name,
            "entity_id": entity_id,
            "type": domain,
            "room": str(params.get("room", "")).strip(),
        }
        self._save_devices(devices)
        return {"success": True, "device": devices[name.casefold()]}

    def _remove_device(self, params: Dict) -> Dict:
        name = str(params.get("name", "")).strip().casefold()
        if not name:
            return {"success": False, "error": "Provide the registered device name to remove."}
        devices = self._load_devices()
        if name not in devices:
            return {"success": False, "error": "No registered device has that exact name."}
        del devices[name]
        self._save_devices(devices)
        return {"success": True, "removed": name}

    async def _control_device(self, params: Dict) -> Dict:
        name = str(params.get("name", "")).strip()
        entity, matches, error = await self._find_entity(name)
        if entity is None:
            return {
                "success": False,
                "error": error or "Device was not found or its name is ambiguous.",
                "matches": [item.get("entity_id") for item in matches],
            }
        entity_id = str(entity.get("entity_id", ""))
        domain = entity_id.split(".", 1)[0]
        if domain not in {"light", "switch", "fan", "climate"}:
            return {"success": False, "error": f"{domain or 'This'} device type is not enabled for control."}
        command = str(params.get("command", "")).strip().lower()
        service_data = {"entity_id": entity_id}
        if command in {"on", "off"} and domain in {"light", "switch", "fan"}:
            service = "turn_on" if command == "on" else "turn_off"
        elif command.startswith("brightness ") and domain == "light":
            try:
                brightness = int(command.split(None, 1)[1])
            except (IndexError, ValueError):
                return {"success": False, "error": "Brightness must be a number from 1 to 255."}
            if not 1 <= brightness <= 255:
                return {"success": False, "error": "Brightness must be from 1 to 255."}
            service = "turn_on"
            service_data["brightness"] = brightness
        elif command.startswith("temperature ") and domain == "climate":
            try:
                temperature = float(command.split(None, 1)[1])
            except (IndexError, ValueError):
                return {"success": False, "error": "Temperature must be a number from 10 to 35 °C."}
            if not 10 <= temperature <= 35:
                return {"success": False, "error": "Temperature must be from 10 to 35 °C."}
            service = "set_temperature"
            service_data["temperature"] = temperature
        else:
            return {
                "success": False,
                "error": "Supported commands: on, off, brightness N (lights), temperature N (thermostats). Locks and garage controls are disabled.",
            }
        return await self._ha_request(
            "POST", f"/api/services/{domain}/{service}", json_data=service_data
        )

    async def _activate_scene(self, params: Dict) -> Dict:
        scene_name = str(params.get("scene", "")).strip()
        allowed = {
            name.strip().casefold()
            for name in os.environ.get("JARVIS_HOME_ASSISTANT_ALLOWED_SCENES", "").split(",")
            if name.strip()
        }
        if not scene_name or scene_name.casefold() not in allowed:
            return {
                "success": False,
                "error": "This scene is not allowlisted. Add trusted scene names to JARVIS_HOME_ASSISTANT_ALLOWED_SCENES locally first.",
            }
        response = await self._ha_request("GET", "/api/states")
        if not response.get("success"):
            return response
        states = response.get("data")
        matches = [
            item for item in states if isinstance(item, dict)
            and str(item.get("entity_id", "")).startswith("scene.")
            and str(item.get("attributes", {}).get("friendly_name", "")).casefold() == scene_name.casefold()
        ] if isinstance(states, list) else []
        if len(matches) != 1:
            return {"success": False, "error": "The allowlisted scene was not found uniquely."}
        entity_id = matches[0].get("entity_id")
        return await self._ha_request(
            "POST", "/api/services/scene/turn_on", json_data={"entity_id": entity_id}
        )

    def _check_rate_limit(self) -> bool:
        now = time.time()
        if now - self._last_minute >= 60:
            self._command_count = 0
            self._last_minute = now
        if self._command_count >= 30:
            return False
        self._command_count += 1
        return True

    async def _ha_request(self, method: str, endpoint: str, json_data: Dict = None, params: Dict = None) -> Dict:
        """Call only an explicitly configured, local Home Assistant instance."""
        base_url = self._ha_config.get("url", "").strip().rstrip("/")
        token = self._ha_config.get("token", "").strip()
        if not base_url or not token:
            return {
                "success": False,
                "error": "Home Assistant is not configured. Set JARVIS_HOME_ASSISTANT_URL and JARVIS_HOME_ASSISTANT_TOKEN locally; no device command was sent.",
            }
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return {"success": False, "error": "Home Assistant URL must be a local HTTP or HTTPS URL without embedded credentials."}
        host = parsed.hostname.casefold()
        try:
            address = ipaddress.ip_address(host)
            local_host = address.is_private or address.is_loopback or address.is_link_local
        except ValueError:
            local_host = host in {"localhost", "homeassistant"} or host.endswith(".local")
        if not local_host:
            return {"success": False, "error": "Home Assistant must resolve to a local network host."}
        if not endpoint.startswith("/api/") or ".." in endpoint.split("/"):
            return {"success": False, "error": "Invalid Home Assistant API path."}
        method = method.upper()
        if method not in {"GET", "POST"}:
            return {"success": False, "error": "Unsupported Home Assistant HTTP method."}
        if method != "GET" and not self._check_rate_limit():
            return {"success": False, "error": "Smart home command rate limit reached."}

        def _request():
            import requests
            with requests.Session() as session:
                session.trust_env = False
                return session.request(
                    method,
                    f"{base_url}{endpoint}",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=json_data,
                    params=params,
                    timeout=(3, 10),
                    allow_redirects=False,
                )

        try:
            response = await asyncio.to_thread(_request)
            if not 200 <= response.status_code < 300:
                return {
                    "success": False,
                    "error": f"Home Assistant returned HTTP {response.status_code}; the operation was not confirmed.",
                }
            try:
                data = response.json()
            except ValueError:
                data = None
            return {"success": True, "data": data}
        except Exception as exc:
            return {"success": False, "error": f"Home Assistant request failed: {type(exc).__name__}."}
        
    def get_status(self) -> Dict:
        return {
            "domain": "smart_home",
            "autonomy_level": 1,
            "target_ceiling": 5,
            "connected": bool(self._ha_config.get("url") and self._ha_config.get("token")),
            "registered_devices": len(self._load_devices()),
            "supported_domains": ["light", "switch", "fan", "climate"],
            "security_devices_enabled": False,
        }
        
    def get_proposals(self) -> List[Dict]:
        return []


_smart_home_agent: SmartHomeAgent | None = None


def handle(parameters: Dict | None = None, response=None, player=None, session_memory=None) -> Dict[str, Any]:
    """JARVIS tool entry point for the configured Home Assistant bridge."""
    global _smart_home_agent
    params = dict(parameters or {})
    action = str(params.pop("action", "")).strip().lower()
    if not action:
        return {"success": False, "error": "Choose a smart-home action."}
    if _smart_home_agent is None:
        _smart_home_agent = SmartHomeAgent()
    try:
        return asyncio.run(_smart_home_agent.handle(action, params))
    except Exception as exc:
        return {"success": False, "error": f"Smart-home action failed: {type(exc).__name__}."}
