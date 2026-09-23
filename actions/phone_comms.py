"""
Phone & Comms Agent — Part 3.2: SMS, voice, messaging control.
Two jobs: outbound (on Boss's behalf) and inbound (alerts to Boss).
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from core.domain_agent import DomainAgent, DomainConfig
from core.safety_guardian import is_killed, log_audit, check_circuit_breaker, increment_scope

class PhoneCommsAgent(DomainAgent):
    """Phone & messaging control: SMS, calls, voice, alerts."""
    
    def __init__(self):
        config = DomainConfig(
            domain="phone_comms",
            autonomy_level=1,
            target_ceiling=4,
            caps={
                "max_sms_per_hour": 50,
                "max_calls_per_hour": 10,
                "max_recipients_per_day": 20
            },
            always_requires_approval=[
                "send_payment_request", "send_contract", "send_commitment",
                "make_call_to_unknown", "send_bulk_sms"
            ],
            allowlist=[]
        )
        super().__init__(config)
        self._sms_count = 0
        self._call_count = 0
        self._last_hour = time.time()
        self._pending_approvals = {}
        self._twilio_config = {
            "account_sid": "",
            "auth_token": "",
            "from_number": ""
        }
        self._approved_templates = [
            "appointment_confirmation", "schedule_reminder", 
            "status_update", "delivery_notification"
        ]
        
    async def handle(self, action: str, params: Dict) -> Any:
        if is_killed("phone_comms"):
            return {"success": False, "error": "Phone comms domain killed by safety guardian"}
            
        if action == "send_sms":
            return await self._send_sms(params)
        elif action == "make_call":
            return await self._make_call(params)
        elif action == "send_voice_message":
            return await self._send_voice_message(params)
        elif action == "send_alert_to_boss":
            return await self._send_alert_to_boss(params)
        elif action == "check_messages":
            return await self._check_messages(params)
        elif action == "get_approval_queue":
            return await self._get_approval_queue()
        elif action == "approve_message":
            return await self._approve_message(params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
            
    async def _send_sms(self, params: Dict) -> Dict:
        to = params.get("to")
        body = params.get("body")
        template = params.get("template")
        
        # Check if requires approval (Part 4.4)
        if any(k in body.lower() for k in ["payment", "payment", "contract", "commitment", "transfer", "withdraw"]):
            return await self._request_approval("send_sms", {"to": to, "body": body})
            
        # Check rate limit
        if not self._check_rate_limit():
            return {"success": False, "error": "SMS rate limit exceeded"}
            
        # Check if using approved template
        if not params.get("approved", False) and not self._is_approved_template(body):
            return await self._request_approval("send_sms", {"to": to, "body": body})
            
        # Actually send (via Twilio or similar)
        return await self._send_via_twilio(to, body)
        
    async def _make_call(self, params: Dict) -> Dict:
        to = params.get("to")
        message = params.get("message", "")
        
        # Check if unknown number
        if not params.get("approved", False):
            return await self._request_approval("make_call", {"to": to, "message": message})
            
        # Actually make call via Twilio
        return await self._make_twilio_call(to, message)
        
    async def _send_voice_message(self, params: Dict) -> Dict:
        to = params.get("to")
        message = params.get("message")
        voice = params.get("voice", "alice")
        
        if not params.get("approved", False):
            return await self._request_approval("send_voice_message", {"to": to, "message": message})
            
        return await self._send_twilio_voice(to, message, voice)
        
    async def _send_alert_to_boss(self, params: Dict) -> Dict:
        """Part 3.2: One-way alert channel to Boss - always works."""
        message = params.get("message", "")
        priority = params.get("priority", "normal")
        
        # This bypasses normal approval - it's the emergency channel to Boss
        result = await self._send_via_twilio(
            self._get_boss_number(),
            f"[JARVIS ALERT - {priority.upper()}] {message}"
        )
        
        # Also log
        self._log_audit("send_alert_to_boss", "passed", "auto_approved:4", "success",
                       {"to": "boss", "priority": priority}, "Alert sent to Boss")
        
        return {"success": True, "sent": True}
        
    async def _check_messages(self, params: Dict) -> Dict:
        # Check incoming messages
        return {"success": True, "messages": []}
        
    async def _get_approval_queue(self) -> Dict:
        return {"success": True, "pending": list(self._pending_approvals.values())}
        
    async def _approve_message(self, params: Dict) -> Dict:
        request_id = params.get("request_id")
        approved = params.get("approved", False)
        
        if request_id in self._pending_approvals:
            req = self._pending_approvals.pop(request_id)
            if approved:
                # Execute the approved action
                if req["action"] == "send_sms":
                    return await self._send_via_twilio(req["params"]["to"], req["params"]["body"])
                elif req["action"] == "make_call":
                    return await self._make_twilio_call(req["params"]["to"], req["params"]["message"])
            return {"success": True, "approved": approved}
        return {"success": False, "error": "Request not found"}
        
    def _is_approved_template(self, body: str) -> bool:
        for template in self._approved_templates:
            if template.lower() in body.lower():
                return True
        return False
        
    async def _request_approval(self, action: str, params: Dict) -> Dict:
        request_id = f"req_{int(time.time())}"
        self._pending_approvals[request_id] = {
            "id": request_id,
            "action": action,
            "params": params,
            "created": datetime.now(timezone.utc).isoformat(),
            "status": "pending"
        }
        return {
            "success": False,
            "requires_approval": True,
            "request_id": request_id,
            "message": "Requires Boss approval"
        }
        
    async def _send_via_twilio(self, to: str, body: str) -> Dict:
        # Placeholder for actual Twilio integration
        return {"success": True, "message_sid": f"SM_{int(time.time())}", "to": to}
        
    async def _make_twilio_call(self, to: str, message: str) -> Dict:
        return {"success": True, "call_sid": f"CA_{int(time.time())}", "to": to}
        
    def _get_boss_number(self) -> str:
        return os.environ.get("JARVIS_BOSS_PHONE", "+15550000000")
        
    def get_status(self) -> Dict:
        return {
            "domain": "phone_comms",
            "autonomy_level": 1,
            "target_ceiling": 4,
            "sms_this_hour": 0,
            "pending_approvals": len([k for k, v in self._pending_approvals.items() if v["status"] == "pending"])
        }
        
    def get_proposals(self) -> List[Dict]:
        return [
            {"id": k, **v} for k, v in self._pending_approvals.items() 
            if v["status"] == "pending"
        ]
        
    def get_status(self) -> Dict:
        return {
            "domain": "phone_comms",
            "autonomy_level": 1,
            "target_ceiling": 4,
            "pending_approvals": len([k for k, v in self._pending_approvals.items() if v["status"] == "pending"])
        }
        
    def get_proposals(self) -> List[Dict]:
        return [
            {"id": k, **v} for k, v in self._pending_approvals.items() 
            if v["status"] == "pending"
        ]