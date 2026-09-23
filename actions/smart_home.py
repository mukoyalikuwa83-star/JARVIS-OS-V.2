"""
Smart Home / IoT Agent — Part 3.3: Lights, sensors, thermostats, locks.
Integrates via Home Assistant hub (Matter/Zigbee/Z-Wave).
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

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
            "url": "http://localhost:8123",
            "token": ""
        }
        self._entity_states: Dict[str, Any] = {}
        self._command_count = 0
        self._last_minute = time.time()
        
    async def handle(self, action: str, params: Dict) -> Any:
        if is_killed("smart_home"):
            return {"success": False, "error": "Smart home domain killed by safety guardian"}
            
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
        # Query Home Assistant API
        return await self._ha_request("GET", f"/api/states/{entity_id}" if entity_id else "/api/states")
        
    async def _set_state(self, params: Dict) -> Dict:
        entity_id = params.get("entity_id")
        state = params.get("state")
        attributes = params.get("attributes", {})
        
        # Check rate limit
        if not self._check_rate_limit():
            return {"success": False, "error": "Rate limit exceeded"}
            
        return await self._ha_request("POST", f"/api/states/{entity_id}", 
                                    json={"state": state, "attributes": attributes})
        
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
        
    async def _ha_request(self, method: str, endpoint: str, json_data: Dict = None, params: Dict = None) -> Dict:
        """Make request to Home Assistant API."""
        ha_url = "http://localhost:8123"
        token = ""
        
        # In production, would use actual HA token
        return {
            "success": True,
            "data": f"HA {method} {endpoint} - placeholder response",
            "note": "Configure Home Assistant URL and token in config"
        }
        
    def get_status(self) -> Dict:
        return {
            "domain": "smart_home",
            "autonomy_level": 1,
            "target_ceiling": 5,
            "lock_ceiling": 2,  # Hard cap per Part 3.3
            "entities_tracked": 0
        }
        
    def get_proposals(self) -> List[Dict]:
        return []