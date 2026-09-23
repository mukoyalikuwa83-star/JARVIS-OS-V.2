"""
Approval Gate System — Part 4.1, 4.4: Approval gates for all domains.
Implements the 5-level autonomy ladder with approval gates.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from core.safety_guardian import get_safety_guardian, is_killed
from core.audit_log import write_audit_entry

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"

@dataclass
class ApprovalRequest:
    request_id: str
    domain: str
    action: str
    params: Dict
    reasoning: str
    autonomy_level: int
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    result: Any = None

class ApprovalGate:
    """Central approval gate managing all domain approval requests."""
    
    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        
    async def submit_request(self, domain: str, action: str, params: Dict, 
                           reasoning: str, autonomy_level: int) -> Dict:
        """Submit an action for approval."""
        if is_killed(domain):
            return {"success": False, "error": f"Domain {domain} is killed"}
            
        request_id = str(uuid.uuid4())
        request = ApprovalRequest(
            request_id=request_id,
            domain=domain,
            action=action,
            params=params,
            reasoning=reasoning,
            autonomy_level=autonomy_level
        )
        
        # Determine if auto-approval applies
        if autonomy_level >= 3:
            # Level 3+ can auto-approve low-risk actions
            request.status = ApprovalStatus.AUTO_APPROVED
            request.decided_at = datetime.now(timezone.utc).isoformat()
            request.decided_by = "system"
        elif autonomy_level == 2:
            request.status = ApprovalStatus.PENDING
        else:
            request.status = ApprovalStatus.PENDING
            
        async with self._lock:
            self._requests[request_id] = request
            
        # Log to audit
        write_audit_entry(
            domain=domain,
            action_proposed=action,
            screening_result="passed",
            gate_result=f"pending_approval:{autonomy_level}",
            execution_result="pending",
            real_outcome={"request_id": request_id},
            reasoning_summary=reasoning,
            credential_used="none"
        )
        
        # Notify callbacks
        await self._notify_callbacks("new_request", {
            "request_id": request_id,
            "domain": domain,
            "action": action,
            "params": params,
            "reasoning": reasoning,
            "autonomy_level": autonomy_level
        })
        
        return {
            "success": True,
            "request_id": request_id,
            "status": request.status.value,
            "requires_approval": autonomy_level <= 2,
            "message": "Submitted for approval" if autonomy_level <= 2 else "Auto-approved"
        }
        
    async def decide(self, request_id: str, decision: str, decided_by: str = "boss") -> Dict:
        """Decide on an approval request."""
        async with self._lock:
            if request_id not in self._requests:
                return {"success": False, "error": "Request not found"}
                
            request = self._requests[request_id]
            if request.status != ApprovalStatus.PENDING:
                return {"success": False, "error": f"Request already {request.status.value}"}
                
            if decision == "approve":
                request.status = ApprovalStatus.APPROVED
            elif decision == "deny":
                request.status = ApprovalStatus.DENIED
            else:
                return {"success": False, "error": "Invalid decision"}
                
            request.decided_at = datetime.now(timezone.utc).isoformat()
            request.decided_by = decided_by
            
        # Log decision
        write_audit_entry(
            domain=request.domain,
            action_proposed=request.action,
            screening_result="passed",
            gate_result=f"approved_by_{decided_by}" if decision == "approve" else "denied",
            execution_result="pending",
            real_outcome={"request_id": request_id, "decision": decision},
            reasoning_summary=f"{decided_by} {decision}d: {request.reasoning}",
            credential_used="none"
        )
        
        await self._notify_callbacks("decision", {
            "request_id": request_id,
            "decision": decision,
            "decided_by": decided_by
        })
        
        return {"success": True, "request_id": request_id, "status": request.status.value}
        
    async def get_pending(self, domain: Optional[str] = None) -> List[Dict]:
        """Get all pending approval requests."""
        async with self._lock:
            requests = [
                {
                    "request_id": r.request_id,
                    "domain": r.domain,
                    "action": r.action,
                    "params": r.params,
                    "reasoning": r.reasoning,
                    "autonomy_level": r.autonomy_level,
                    "created_at": r.created_at
                }
                for r in self._requests.values()
                if r.status == ApprovalStatus.PENDING and (domain is None or r.domain == domain)
            ]
        return requests
        
    async def get_history(self, domain: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get approval history."""
        async with self._lock:
            history = [
                {
                    "request_id": r.request_id,
                    "domain": r.domain,
                    "action": r.action,
                    "status": r.status.value,
                    "created_at": r.created_at,
                    "decided_at": r.decided_at,
                    "decided_by": r.decided_by
                }
                for r in self._requests.values()
                if domain is None or r.domain == domain
            ]
            history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return history[:limit]
            
    def register_callback(self, event: str, callback: Callable):
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
        
    async def _notify_callbacks(self, event: str, data: Dict):
        for cb in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(data)
                else:
                    cb(data)
            except Exception:
                pass

# Global singleton
_approval_gate: Optional["ApprovalGate"] = None

def get_approval_gate() -> "ApprovalGate":
    global _approval_gate
    if _approval_gate is None:
        _approval_gate = ApprovalGate()
    return _approval_gate

# Convenience functions for domains
async def request_approval(domain: str, action: str, params: Dict, reasoning: str, autonomy_level: int) -> Dict:
    return await get_approval_gate().submit_request(domain, action, params, reasoning, autonomy_level)

async def get_pending_approvals(domain: Optional[str] = None) -> List[Dict]:
    return await get_approval_gate().get_pending(domain)

async def approve_request(request_id: str, decision: str, decided_by: str = "boss") -> Dict:
    return await get_approval_gate().decide(request_id, decision, decided_by)

async def get_approval_history(domain: Optional[str] = None, limit: int = 50) -> List[Dict]:
    return await get_approval_gate().get_history(domain, limit)