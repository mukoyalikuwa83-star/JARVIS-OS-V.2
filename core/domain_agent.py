"""
Domain Agent Base Class — Part 2.3: Base class for all domain agents.
Each domain agent implements this interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

from actions._api import _load_env
from core.safety_guardian import get_safety_guardian, is_killed, KillLayer, KillReason, log_audit
from core.audit_log import write_audit_entry

_load_env()

class AutonomyLevel(Enum):
    LEVEL_0 = 0  # Observe only
    LEVEL_1 = 1  # Propose only
    LEVEL_2 = 2  # Propose + await approval
    LEVEL_3 = 3  # Execute low-risk with caps
    LEVEL_4 = 4  # Execute within caps
    LEVEL_5 = 5  # Full autonomy within caps

@dataclass
class DomainConfig:
    domain: str
    autonomy_level: int = 1
    target_ceiling: int = 5
    caps: Dict = None
    always_requires_approval: List[str] = None
    allowlist: List[str] = None
    
    def __post_init__(self):
        if self.caps is None:
            self.caps = {}
        if self.always_requires_approval is None:
            self.always_requires_approval = []
        if self.allowlist is None:
            self.allowlist = []

class DomainAgent(ABC):
    """Base class for all domain agents."""
    
    def __init__(self, config: DomainConfig):
        self.config = config
        self._callbacks: Dict[str, callable] = {}
        
    @abstractmethod
    async def handle(self, action: str, params: Dict) -> Any:
        """Handle an action from the planner."""
        pass
        
    @abstractmethod
    def get_status(self) -> Dict:
        """Return current status for dashboard."""
        pass
        
    @abstractmethod
    def get_proposals(self) -> List[Dict]:
        """Return pending proposals for approval queue."""
        pass
        
    def get_autonomy_level(self) -> int:
        return self.config.autonomy_level
        
    def set_autonomy_level(self, level: int):
        """Set autonomy level (validated against target ceiling)."""
        if level > self.config.target_ceiling:
            raise ValueError(f"Cannot exceed target ceiling {self.config.target_ceiling}")
        if level < 0 or level > 5:
            raise ValueError("Autonomy level must be 0-5")
        self.config.autonomy_level = level
        
    def can_execute(self, action: str) -> tuple:
        """
        Check if action can execute at current autonomy level.
        Returns (can_execute: bool, requires_approval: bool, reason: str)
        """
        # Always-require-approval actions (Part 4.4)
        if action in self.config.always_requires_approval:
            return (True, True, "Action always requires Boss approval")
            
        level = self.config.autonomy_level
        
        if level == 0:
            return (False, False, "Level 0: observe only")
        elif level == 1:
            return (True, True, "Level 1: propose only, needs approval")
        elif level == 2:
            return (True, True, "Level 2: propose + await approval")
        elif level == 3:
            # Low-risk reversible actions auto-execute within caps
            return (True, False, "Level 3: auto-execute low-risk within caps")
        elif level == 4:
            return (True, False, "Level 4: execute within caps")
        elif level == 5:
            return (True, False, "Level 5: full autonomy within caps")
        return (False, False, "Unknown level")
        
    def check_allowlist(self, item: str) -> bool:
        """Check if item is in allowlist."""
        if not self.config.allowlist:
            return True  # Empty allowlist = allow all
        return item in self.config.allowlist
        
    def propose(self, action: str, params: Dict, reasoning: str) -> Dict:
        """Create a proposal for approval queue."""
        return {
            "domain": self.config.domain,
            "action": action,
            "params": params,
            "reasoning": reasoning,
            "autonomy_level": self.config.autonomy_level,
            "requires_approval": True
        }
        
    def log_audit(self, action: str, screening: str, gate: str, 
                  execution: str, outcome: Any, reasoning: str, cred: str = "none"):
        """Log audit entry per Appendix C."""
        from core.audit_log import write_audit_entry
        write_audit_entry(
            domain=self.config.domain,
            action_proposed=action,
            screening_result=screening,
            gate_result=gate,
            execution_result=execution,
            real_outcome=outcome,
            reasoning_summary=reasoning,
            credential_used="none"
        )
        
    def check_killed(self) -> bool:
        """Check if this domain is killed."""
        from core.safety_guardian import is_killed
        return is_killed(self.config.domain)
        
    def register_callback(self, event: str, callback: callable):
        """Register a callback for events."""
        self._callbacks[event] = callback
        
    def _trigger_callback(self, event: str, data: Any):
        if event in self._callbacks:
            try:
                self._callbacks[event](data)
            except Exception:
                pass

class DomainRegistry:
    """Registry of all domain agents."""
    
    def __init__(self):
        self._agents: Dict[str, "DomainAgent"] = {}
        
    def register(self, agent: "DomainAgent"):
        domain = getattr(getattr(agent, "config", None), "domain", None)
        if domain is None:
            # Fallback: method get_domain() or class name
            domain = getattr(agent, "get_domain", lambda: None)()
            if domain is None:
                domain = agent.__class__.__name__.replace("Agent", "").lower()
        self._agents[domain] = agent
        
    def get(self, domain: str) -> Optional["DomainAgent"]:
        return self._agents.get(domain)
        
    def get_all(self) -> Dict[str, "DomainAgent"]:
        return self._agents.copy()
        
    def get_all_status(self) -> Dict:
        return {domain: agent.get_status() for domain, agent in self._agents.items()}
        
    def get_all_proposals(self) -> List[Dict]:
        proposals = []
        for agent in self._agents.values():
            proposals.extend(agent.get_proposals())
        return proposals

# Global registry
_registry: Optional["DomainRegistry"] = None

def get_registry() -> DomainRegistry:
    global _registry
    if _registry is None:
        _registry = DomainRegistry()
    return _registry