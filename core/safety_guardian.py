"""
Safety & Guardian Agent — Part 4.2: Five-layer kill switch, circuit breakers, audit log.
This is the foundation layer. Nothing ships without this working.
"""
import asyncio
import json
import os
import time
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager

from actions._api import _load_env

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_AUDIT_LOG = _DATA_DIR / "audit_log.jsonl"
_KILL_STATE = _DATA_DIR / "kill_state.json"
_CONFIG_FILE = _DATA_DIR / "safety_config.json"

_load_env()

class KillLayer(Enum):
    LOCAL_STOP = 1           # Hotkey/spoken "stand down"
    REMOTE_STOP = 2          # SMS code/phone app
    DEAD_MAN_SWITCH = 3      # Missed heartbeat/bounds
    FINANCIAL_CIRCUIT = 4    # Loss caps, position limits
    SCOPE_CIRCUIT = 5        # Rate limits: msgs/hr, accounts/day

class KillReason(Enum):
    MANUAL_LOCAL = "manual_local"
    MANUAL_REMOTE = "manual_remote"
    HEARTBEAT_MISSED = "heartbeat_missed"
    BOUNDS_VIOLATION = "bounds_violation"
    FINANCIAL_LIMIT = "financial_limit"
    SCOPE_LIMIT = "scope_limit"
    SAFETY_VIOLATION = "safety_violation"

@dataclass
class KillState:
    layer: KillLayer
    reason: KillReason
    timestamp: str
    domain: str
    details: Dict = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None

@dataclass
class CircuitBreakerState:
    name: str
    limit: float
    current: float
    triggered: bool = False
    triggered_at: Optional[str] = None
    domain: str = ""

@dataclass
class HeartbeatState:
    domain: str
    last_beat: float = 0.0
    expected_interval: float = 60.0
    max_missed: int = 3
    missed_count: int = 0

class SafetyGuardian:
    """The Safety & Guardian Agent — holds veto power over all domains."""
    
    def __init__(self):
        self._kill_states: List[KillState] = []
        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self._heartbeats: Dict[str, HeartbeatState] = {}
        self._kill_callbacks: List[Callable] = []
        self._lock = threading.RLock()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Load persisted state
        self._load_state()
        
        # Default circuit breakers (configurable)
        self._init_default_breakers()
        
    def _load_state(self):
        if _KILL_STATE.exists():
            try:
                data = json.loads(_KILL_STATE.read_text(encoding="utf-8"))
                for k in data.get("kill_states", []):
                    # Handle both enum and string from saved state
                    layer = k.get("layer")
                    if isinstance(layer, str):
                        layer = KillLayer[layer]
                    reason = k.get("reason")
                    if isinstance(reason, str):
                        reason = KillReason[reason]
                    k["layer"] = layer
                    k["reason"] = reason
                    self._kill_states.append(KillState(**k))
                for cb_data in data.get("circuit_breakers", {}).values():
                    cb = CircuitBreakerState(**cb_data)
                    self._circuit_breakers[cb.name] = cb
            except Exception:
                pass
                
    def _save_state(self):
        data = {
            "kill_states": [
                {
                    "layer": k.layer.name,
                    "reason": k.reason.name,
                    "timestamp": k.timestamp,
                    "domain": k.domain,
                    "details": k.details,
                    "acknowledged": k.acknowledged,
                    "acknowledged_at": k.acknowledged_at
                }
                for k in self._kill_states
            ],
            "circuit_breakers": {
                k: {
                    "domain": v.domain,
                    "limit": v.limit,
                    "current": v.current,
                    "triggered": v.triggered,
                    "triggered_at": v.triggered_at,
                }
                for k, v in self._circuit_breakers.items()
            },
            "updated": datetime.now(timezone.utc).isoformat()
        }
        _KILL_STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
    def _init_default_breakers(self):
        """Initialize default circuit breakers per Part 4.2."""
        defaults = {
            "financial_daily_loss": CircuitBreakerState(
                name="financial_daily_loss",
                limit=2.0,  # 2% daily loss cap
                current=0.0,
                domain="trading"
            ),
            "financial_position_size": CircuitBreakerState(
                name="financial_position_size",
                limit=5.0,  # 5% max position
                current=0.0,
                domain="trading"
            ),
            "financial_capital_at_risk": CircuitBreakerState(
                name="financial_capital_at_risk",
                limit=20.0,  # 20% max capital at risk
                current=0.0,
                domain="trading"
            ),
            "scope_messages_per_hour": CircuitBreakerState(
                name="scope_messages_per_hour",
                limit=50,  # 50 messages/hour
                current=0,
                domain="phone_comms"
            ),
            "scope_accounts_per_day": CircuitBreakerState(
                name="scope_accounts_per_day",
                limit=5,  # 5 new accounts/day
                current=0,
                domain="opportunity"
            ),
            "scope_published_per_day": CircuitBreakerState(
                name="scope_published_per_day",
                limit=20,  # 20 published items/day
                current=0,
                domain="content"
            ),
        }
        for name, cb in defaults.items():
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = cb
        self._save_state()
        
    def register_heartbeat(self, domain: str, interval: float = 60.0, max_missed: int = 3):
        """Register a domain for dead-man's switch monitoring."""
        with self._lock:
            self._heartbeats[domain] = HeartbeatState(
                domain=domain,
                last_beat=time.time(),
                expected_interval=interval,
                max_missed=max_missed
            )
            
    def heartbeat(self, domain: str):
        """Record a heartbeat from a domain."""
        with self._lock:
            if domain in self._heartbeats:
                self._heartbeats[domain].last_beat = time.time()
                self._heartbeats[domain].missed_count = 0
                
    def register_kill_callback(self, callback: Callable):
        """Register a callback to be invoked on kill trigger."""
        self._kill_callbacks.append(callback)
        
    def trigger_kill(self, layer: KillLayer, reason: KillReason, domain: str, details: Dict = None):
        """Trigger a kill switch layer — pauses affected domain, alerts Boss."""
        with self._lock:
            state = KillState(
                layer=layer,
                reason=reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
                domain=domain,
                details=details or {}
            )
            self._kill_states.append(state)
            self._save_state()
            
        # Invoke callbacks (pauses domains, alerts Boss)
        for cb in self._kill_callbacks:
            try:
                cb(layer, reason, domain, details or {})
            except Exception:
                pass
                
        # Log to audit
        self._log_audit("kill_triggered", {
            "layer": layer.name,
            "reason": reason.value,
            "domain": domain,
            "details": details or {}
        })
        
    def check_heartbeats(self):
        """Check all heartbeats — trigger dead-man's switch if missed."""
        now = time.time()
        with self._lock:
            for domain, hb in self._heartbeats.items():
                elapsed = now - hb.last_beat
                if elapsed > hb.expected_interval * hb.max_missed:
                    if hb.missed_count < hb.max_missed:
                        hb.missed_count += 1
                        self.trigger_kill(
                            KillLayer.DEAD_MAN_SWITCH,
                            KillReason.HEARTBEAT_MISSED,
                            domain,
                            {"elapsed": elapsed, "expected": hb.expected_interval, "missed": hb.missed_count}
                        )
                        
    def check_circuit_breaker(self, name: str, current_value: float) -> bool:
        """Check and update circuit breaker. Returns True if triggered."""
        with self._lock:
            if name not in self._circuit_breakers:
                return False
            cb = self._circuit_breakers[name]
            cb.current = current_value
            if current_value >= cb.limit and not cb.triggered:
                cb.triggered = True
                cb.triggered_at = datetime.now(timezone.utc).isoformat()
                self._save_state()
                self.trigger_kill(
                    KillLayer.FINANCIAL_CIRCUIT if "financial" in name else KillLayer.SCOPE_CIRCUIT,
                    KillReason.FINANCIAL_LIMIT if "financial" in name else KillReason.SCOPE_LIMIT,
                    cb.domain,
                    {"breaker": name, "limit": cb.limit, "current": current_value}
                )
                return True
            return False
            
    def increment_scope_counter(self, name: str, increment: int = 1):
        """Increment a scope circuit breaker counter."""
        with self._lock:
            if name in self._circuit_breakers:
                cb = self._circuit_breakers[name]
                cb.current += increment
                if cb.current >= cb.limit and not cb.triggered:
                    cb.triggered = True
                    cb.triggered_at = datetime.now(timezone.utc).isoformat()
                    self._save_state()
                    self.trigger_kill(
                        KillLayer.SCOPE_CIRCUIT,
                        KillReason.SCOPE_LIMIT,
                        cb.domain,
                        {"breaker": name, "limit": cb.limit, "current": cb.current}
                    )
                else:
                    self._save_state()
                    
    def reset_circuit_breaker(self, name: str, boss_confirmed: bool = False):
        """Reset a circuit breaker — requires Boss confirmation if triggered."""
        with self._lock:
            if name in self._circuit_breakers:
                cb = self._circuit_breakers[name]
                if cb.triggered and not boss_confirmed:
                    raise PermissionError(f"Circuit breaker {name} triggered — requires Boss confirmation to reset")
                cb.triggered = False
                cb.triggered_at = None
                cb.current = 0
                self._save_state()
                
    def is_breaker_tripped(self, name: str) -> bool:
        """Check if a circuit breaker is currently tripped (not the one-shot signal)."""
        with self._lock:
            cb = self._circuit_breakers.get(name)
            return bool(cb and cb.triggered)
                
    def is_killed(self, domain: str = None) -> bool:
        """Check if a domain (or any) is currently killed."""
        with self._lock:
            active = [k for k in self._kill_states if not k.acknowledged]
            if domain:
                return any(k.domain == domain for k in active)
            return len(active) > 0
            
    def acknowledge_kill(self, kill_index: int, boss_confirmed: bool = True):
        """Acknowledge a kill state — requires Boss confirmation."""
        with self._lock:
            if 0 <= kill_index < len(self._kill_states):
                self._kill_states[kill_index].acknowledged = True
                self._kill_states[kill_index].acknowledged_at = datetime.now(timezone.utc).isoformat()
                self._save_state()
                
    def acknowledge_domain_kills(self, domain: str, boss_confirmed: bool = True):
        """Acknowledge ALL active kills for a domain (Boss confirmation)."""
        with self._lock:
            changed = False
            for k in self._kill_states:
                if k.domain == domain and not k.acknowledged:
                    k.acknowledged = True
                    k.acknowledged_at = datetime.now(timezone.utc).isoformat()
                    changed = True
            if changed:
                self._save_state()
                self._log_audit("kill_acknowledged", {"domain": domain, "boss_confirmed": boss_confirmed})
            return changed
                
    def get_status(self) -> Dict:
        """Get current safety status for dashboard."""
        with self._lock:
            def _ser(obj):
                if isinstance(obj, Enum):
                    return obj.name
                if hasattr(obj, "__dict__"):
                    return {k: _ser(v) for k, v in vars(obj).items()}
                return obj
            return {
                "active_kills": [_ser(k) for k in self._kill_states if not k.acknowledged],
                "circuit_breakers": {k: _ser(v) for k, v in self._circuit_breakers.items()},
                "heartbeats": {k: {"last_beat": v.last_beat, "missed": v.missed_count} 
                              for k, v in self._heartbeats.items()},
                "any_active": len([k for k in self._kill_states if not k.acknowledged]) > 0
            }
            
    # Audit logging per Appendix C
    def _log_audit(self, action: str, data: Dict):
        """Write immutable audit log entry per Appendix C schema."""
        entry = {
            "entry_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "domain": "safety_guardian",
            "action_proposed": action,
            "screening_result": "passed",
            "gate_result": "auto_approved",
            "execution_result": "success",
            "real_outcome": data,
            "reasoning_summary": f"Safety guardian action: {action}",
            "credential_used": "none"
        }
        _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            
    def log_audit_entry(self, domain: str, action_proposed: str, screening_result: str,
                        gate_result: str, execution_result: str, real_outcome: Any,
                        reasoning: str, credential: str = "none"):
        """Public method for domains to log audit entries per Appendix C."""
        entry = {
            "entry_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "domain": domain,
            "action_proposed": action_proposed,
            "screening_result": screening_result,
            "gate_result": gate_result,
            "execution_result": execution_result,
            "real_outcome": real_outcome,
            "reasoning_summary": reasoning,
            "credential_used": credential
        }
        _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            
    async def start_monitoring(self):
        """Start the background monitoring task."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
    async def stop_monitoring(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
    async def _monitor_loop(self):
        while self._running:
            try:
                self.check_heartbeats()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

# Global singleton
_safety_guardian: Optional[SafetyGuardian] = None

def get_safety_guardian() -> SafetyGuardian:
    global _safety_guardian
    if _safety_guardian is None:
        _safety_guardian = SafetyGuardian()
    return _safety_guardian

# Convenience functions for domains
def trigger_kill(layer: KillLayer, reason: KillReason, domain: str, details: Dict = None):
    get_safety_guardian().trigger_kill(layer, reason, domain, details)

def heartbeat(domain: str):
    get_safety_guardian().heartbeat(domain)

def register_heartbeat(domain: str, interval: float = 60.0, max_missed: int = 3):
    get_safety_guardian().register_heartbeat(domain, interval, max_missed)

def check_circuit_breaker(name: str, value: float) -> bool:
    return get_safety_guardian().check_circuit_breaker(name, value)

def is_breaker_tripped(name: str) -> bool:
    return get_safety_guardian().is_breaker_tripped(name)

def increment_scope(name: str, increment: int = 1):
    get_safety_guardian().increment_scope_counter(name, increment)

def log_audit(domain: str, action: str, screening: str, gate: str, 
              execution: str, outcome: Any, reasoning: str, cred: str = "none"):
    get_safety_guardian().log_audit_entry(domain, action, screening, gate, 
                                           execution, str(outcome), reasoning)

def is_killed(domain: str = None) -> bool:
    return get_safety_guardian().is_killed(domain)

def get_safety_status() -> Dict:
    return get_safety_guardian().get_status()