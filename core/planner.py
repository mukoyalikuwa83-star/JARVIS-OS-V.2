"""
Planning / Orchestrator Agent — Part 2.3: Turns goals into plans across domains.
The central coordinator that decomposes goals and delegates to domain agents.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from actions._api import _load_env
from core.safety_guardian import get_safety_guardian, is_killed, trigger_kill, log_audit
from core.audit_log import write_audit_entry

_load_env()

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_PLANS_FILE = Path(__file__).resolve().parent.parent / ".jarvis" / "plans.json"

class PlanStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class PlanStep:
    step_id: str
    domain: str
    action: str
    params: Dict
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None

@dataclass
class Plan:
    plan_id: str
    goal: str
    created_at: str
    steps: List[PlanStep] = field(default_factory=list)
    status: str = "pending"
    current_step: int = 0
    result: Any = None
    error: Optional[str] = None

class PlanningOrchestrator:
    """Plans goals, delegates to domain agents, merges results."""
    
    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._domain_handlers: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        
    def register_domain(self, domain: str, handler: Callable):
        """Register a domain agent handler."""
        self._domain_handlers[domain] = handler
        
    async def create_plan(self, goal: str, domain_hints: List[str] = None) -> str:
        """Create a plan from a high-level goal."""
        plan_id = str(uuid.uuid4())
        
        # Decompose goal into steps (simplified - in production would use LLM)
        steps = self._decompose_goal(goal, domain_hints or [])
        
        plan = Plan(
            plan_id=plan_id,
            goal=goal,
            created_at=datetime.now(timezone.utc).isoformat(),
            steps=steps
        )
        
        self._plans[plan_id] = plan
        self._save_plans()
        
        # Log plan creation
        write_audit_entry(
            domain="planner",
            action_proposed=f"create_plan:{plan_id}",
            screening_result="passed",
            gate_result="auto_approved:1",
            execution_result="success",
            real_outcome={"plan_id": plan_id, "steps": len(steps)},
            reasoning_summary=f"Created plan for goal: {goal}",
            credential_used="none"
        )
        
        return plan_id
        
    def _decompose_goal(self, goal: str, hints: List[str]) -> List:
        """Simple goal decomposition - in production would use LLM."""
        # Basic keyword-based decomposition
        steps = []
        goal_lower = goal.lower()
        
        if any(k in goal_lower for k in ["build", "create", "develop", "code"]):
            steps.append(PlanStep(
                step_id=str(__import__("uuid").uuid4()),
                domain="computer_control",
                action="create_project",
                params={"description": goal, "type": "auto"}
            ))
            
        if any(k in goal_lower for k in ["deploy", "publish", "release"]):
            steps.append(PlanStep(
                step_id=str(__import__("uuid").uuid4()),
                domain="computer_control",
                action="deploy",
                params={"target": "github_pages"}
            ))
            
        if any(k in goal_lower for k in ["market", "promote", "advertise", "sell"]):
            steps.append(PlanStep(
                step_id=str(__import__("uuid").uuid4()),
                domain="opportunity",
                action="promote_product",
                params={"platform": "all"}
            ))
            
        if any(k in goal_lower for k in ["trade", "invest", "buy", "sell"]):
            steps.append(PlanStep(
                step_id=str(__import__("uuid").uuid4()),
                domain="trading",
                action="analyze_market",
                params={"symbols": ["BTC", "ETH"]}
            ))
            
        if any(k in goal_lower for k in ["monitor", "check", "watch", "alert"]):
            steps.append(PlanStep(
                step_id=str(__import__("uuid").uuid4()),
                domain="smart_home",
                action="check_sensors",
                params={}
            ))
            
        if any(k in goal_lower for k in ["message", "text", "notify", "alert"]):
            steps.append(PlanStep(
                step_id=str(__import__("uuid").uuid4()),
                domain="phone_comms",
                action="send_message",
                params={"recipient": "boss", "content": goal}
            ))
            
        if not steps:
            # Default: treat as research task
            steps.append(PlanStep(
                step_id=str(__import__("uuid").uuid4()),
                domain="opportunity",
                action="research_opportunity",
                params={"query": goal}
            ))
            
        return steps
        
    async def execute_plan(self, plan_id: str) -> Dict:
        """Execute a plan step by step."""
        if plan_id not in self._plans:
            return {"success": False, "error": "Plan not found"}
            
        plan = self._plans[plan_id]
        plan.status = "in_progress"
        self._save_plans()
        
        results = {}
        for i, step in enumerate(plan.steps):
            # Check dependencies
            for dep_id in step.depends_on:
                dep_step = next((s for s in plan.steps if s.step_id == dep_id), None)
                if not dep_step or dep_step.status != "completed":
                    step.status = "failed"
                    step.error = f"Dependency {dep_id} not completed"
                    plan.status = "failed"
                    self._save_plans()
                    return {"success": False, "error": f"Dependency {dep_id} not met"}
                    
            # Check if killed
            if is_killed(step.domain):
                step.status = "failed"
                step.error = "Domain killed by safety guardian"
                plan.status = "failed"
                self._save_plans()
                return {"success": False, "error": "Domain killed by safety guardian"}
                
            plan.current_step = i
            step.status = "in_progress"
            self._save_plans()
            
            # Execute step
            handler = self._domain_handlers.get(step.domain)
            if not handler:
                step.status = "failed"
                step.error = f"No handler for domain {step.domain}"
                plan.status = "failed"
                self._save_plans()
                return {"success": False, "error": f"No handler for domain {step.domain}"}
                
            try:
                result = await handler(step.action, step.params)
                step.result = result
                step.status = "completed"
                results[step.step_id] = result
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                plan.status = "failed"
                self._save_plans()
                return {"success": False, "error": str(e), "partial_results": results}
                
            self._save_plans()
            
        plan.status = "completed"
        plan.result = results
        self._save_plans()
        return {"success": True, "results": results}
        
    def get_plan(self, plan_id: str) -> Optional[Dict]:
        if plan_id in self._plans:
            plan = self._plans[plan_id]
            return {
                "plan_id": plan.plan_id,
                "goal": plan.goal,
                "status": plan.status,
                "steps": [
                    {
                        "step_id": s.step_id,
                        "domain": s.domain,
                        "action": s.action,
                        "params": s.params,
                        "status": s.status,
                        "result": s.result,
                        "error": s.error
                    }
                    for s in plan.steps
                ],
                "created_at": plan.created_at,
                "result": plan.result,
                "error": plan.error
            }
        return None
        
    def list_plans(self) -> List[Dict]:
        return [
            {
                "plan_id": p.plan_id,
                "goal": p.goal,
                "status": p.status,
                "created_at": p.created_at,
                "steps_total": len(p.steps),
                "steps_completed": sum(1 for s in p.steps if s.status == "completed")
            }
            for p in self._plans.values()
        ]
        
    def _save_plans(self):
        _PLANS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for pid, plan in self._plans.items():
            data[pid] = {
                "plan_id": plan.plan_id,
                "goal": plan.goal,
                "created_at": plan.created_at,
                "status": plan.status,
                "current_step": plan.current_step,
                "steps": [
                    {
                        "step_id": s.step_id,
                        "domain": s.domain,
                        "action": s.action,
                        "params": s.params,
                        "depends_on": s.depends_on,
                        "status": s.status,
                        "result": s.result,
                        "error": s.error
                    }
                    for s in plan.steps
                ],
                "result": plan.result,
                "error": plan.error
            }
        Path(_PLANS_FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")
        
    def load_plans(self):
        if _PLANS_FILE.exists():
            try:
                data = json.loads(_PLANS_FILE.read_text(encoding="utf-8"))
                for pid, pdata in data.items():
                    plan = Plan(
                        plan_id=pdata["plan_id"],
                        goal=pdata["goal"],
                        created_at=pdata["created_at"],
                        status=pdata["status"],
                        current_step=pdata.get("current_step", 0),
                        result=pdata.get("result"),
                        error=pdata.get("error")
                    )
                    plan.steps = [
                        PlanStep(**s) for s in pdata.get("steps", [])
                    ]
                    self._plans[pid] = plan
            except Exception:
                pass

# Global singleton
_planner: Optional["PlanningOrchestrator"] = None

def get_planner() -> PlanningOrchestrator:
    global _planner
    if _planner is None:
        _planner = PlanningOrchestrator()
        _planner.load_plans()
    return _planner