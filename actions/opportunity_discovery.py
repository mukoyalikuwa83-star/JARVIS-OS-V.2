"""
Opportunity Discovery Agent — Part 3.5.2-4: Finds and runs new income opportunities.
Scans → Scores → Screens (exclusion list) → Gates → Executes → Reports.
"""
import asyncio
import json
import time
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from core.domain_agent import DomainAgent, DomainConfig
from core.safety_guardian import is_killed, check_circuit_breaker, increment_scope
from core.audit_log import write_audit_entry

class OpportunityDiscoveryAgent(DomainAgent):
    """Finds and runs new income opportunities - Track B of Part 3.5."""
    
    def __init__(self):
        config = DomainConfig(
            domain="opportunity",
            autonomy_level=1,
            target_ceiling=4,
            caps={
                "max_ideas_per_day": 20,
                "max_concurrent_projects": 5,
                "max_capital_per_idea": 100.0,
                "max_time_per_idea_hours": 4
            },
            always_requires_approval=[
                "publish_content", "deploy_service", "create_account",
                "spend_budget", "sign_contract"
            ],
            allowlist=[]
        )
        super().__init__(config)
        self._exclusion_list = [  # Appendix D
            "guaranteed_return", "unlicensed_financial_advice",
            "spam_engagement_farming", "plagiarized_content",
            "impersonation", "fake_accounts", "mlm_pyramid",
            "market_manipulation", "bypass_anti_bot", "tos_violating_scraping"
        ]
        self._scoring_weights = {
            "legitimacy": 0.30,
            "fit": 0.20,
            "capital_required": 0.15,
            "time_to_revenue": 0.20,
            "automatability": 0.15
        }
        self._active_ideas: Dict = {}
        self._completed_ideas: List = []
        self._sandbox_results: Dict = {}
        
    async def handle(self, action: str, params: Dict) -> Any:
        if is_killed("opportunity"):
            return {"success": False, "error": "Opportunity domain killed by safety guardian"}
            
        if action == "scan_opportunities":
            return await self._scan_opportunities(params)
        elif action == "score_idea":
            return await self._score_idea(params)
        elif action == "screen_idea":
            return await self._screen_idea(params)
        elif action == "execute_idea":
            return await self._execute_idea(params)
        elif action == "get_ideas":
            return await self._get_ideas(params)
        elif action == "get_sandbox_results":
            return await self._get_sandbox_results(params)
        elif action == "promote_idea":
            return await self._promote_idea(params)
        elif action == "run_sandbox_test":
            return await self._run_sandbox_test(params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
            
    async def _scan_opportunities(self, params: Dict) -> Dict:
        """Scan for new opportunities - would use web search, APIs, trend analysis."""
        # Simulated opportunities for demo
        opportunities = [
            {
                "id": f"opp_{int(time.time())}_{i}",
                "type": t,
                "title": title,
                "description": desc,
                "source": "trend_scan",
                "created": datetime.now(timezone.utc).isoformat()
            }
            for i, (t, title, desc) in enumerate([
                ("python_tool", "CLI Tool - Log Analyzer", "Parse and analyze log files with regex patterns"),
                ("web_scraper", "E-commerce Price Monitor", "Track competitor prices automatically"),
                ("api_wrapper", "Crypto Exchange Wrapper", "Unified interface for multiple exchanges"),
                ("automation", "Email-to-Task Converter", "Turn emails into structured tasks"),
                ("saas_template", "Micro-SaaS Boilerplate", "Auth, billing, dashboard starter kit"),
            ], 1)
        ]
        
        # Score each
        for opp in opportunities:
            opp["score"] = await self._calculate_score(opp)
            
        # Sort by score
        opportunities.sort(key=lambda x: x["score"], reverse=True)
        
        # Store
        for opp in opportunities:
            self._active_ideas[opp["id"]] = opp
            
        return {"success": True, "opportunities": opportunities[:10]}
        
    async def _calculate_score(self, opp: Dict) -> float:
        """Score opportunity on 5 dimensions (Part 3.5.2)."""
        weights = self._scoring_weights
        
        # Simulated scoring - in production would use real data
        scores = {
            "legitimacy": random.uniform(0.6, 0.95),
            "fit": random.uniform(0.5, 0.9),
            "capital_required": random.uniform(0.4, 0.8),
            "time_to_revenue": random.uniform(0.3, 0.9),
            "automatability": random.uniform(0.6, 0.95)
        }
        
        weighted = sum(scores[k] * self._scoring_weights[k] for k in weights)
        return round(weighted, 3)
        
    async def _screen_idea(self, params: Dict) -> Dict:
        """Screen against Appendix D exclusion list - Part 3.5.2."""
        idea = params.get("idea", {})
        description = idea.get("description", "").lower()
        title = idea.get("title", "").lower()
        
        # Check exclusion list (Appendix D)
        exclusions = {
            "guaranteed_return": ["guaranteed", "guarantee", "risk-free", "no risk"],
            "unlicensed_financial_advice": ["financial advice", "investment advice", "portfolio management"],
            "spam_engagement_farming": ["buy views", "buy likes", "fake engagement", "bot"],
            "plagiarized_content": ["copy", "duplicate", "scrape content"],
            "impersonation": ["impersonate", "pretend to be", "fake identity"],
            "fake_accounts": ["fake account", "bot account", "mass account"],
            "mlm_pyramid": ["mlm", "pyramid", "multi-level", "downline"],
            "market_manipulation": ["wash trade", "pump and dump", "manipulate"],
            "bypass_anti_bot": ["bypass captcha", "evade detection", "anti-bot"],
            "tos_violating_scraping": ["scrape", "crawl", "extract data"]
        }
        
        text = f"{title} {description}"
        violations = []
        
        for category, keywords in exclusions.items():
            for kw in keywords:
                if kw in text:
                    violations.append(category)
                    
        if violations:
            return {
                "success": True,
                "passed": False,
                "violations": violations,
                "screening_result": f"rejected:{','.join(violations)}"
            }
            
        return {
            "success": True,
            "passed": True,
            "screening_result": "passed"
        }
        
    async def _execute_idea(self, params: Dict) -> Dict:
        idea_id = params.get("idea_id")
        if idea_id not in self._active_ideas:
            return {"success": False, "error": "Idea not found"}
            
        idea = self._active_ideas[idea_id]
        
        # Screen first
        screen = await self._screen_idea({"idea": idea})
        if not screen["passed"]:
            return {"success": False, "error": f"Screening failed: {screen['violations']}"}
            
        # Check autonomy level for execution
        can_exec, needs_approval, reason = self._can_execute("execute_idea")
        if needs_approval and not params.get("approved", False):
            return {"success": False, "error": reason, "requires_approval": True}
            
        # Execute based on type
        idea_type = idea.get("type", "unknown")
        if idea_type in ["python_tool", "web_scraper", "api_wrapper", "automation"]:
            return await self._build_python_tool(idea)
        elif idea_type == "saas_template":
            return await self._build_saas_template(idea)
        elif idea_type in ["content", "blog", "video"]:
            return await self._create_content(idea)
        else:
            return {"success": False, "error": f"Unknown idea type: {idea_type}"}
            
    async def _build_python_tool(self, idea: Dict) -> Dict:
        # Would generate Python tool code
        return {"success": True, "type": "python_tool", "status": "built"}
        
    async def _build_saas_template(self, idea: Dict) -> Dict:
        return {"success": True, "type": "saas_template", "status": "built"}
        
    async def _create_content(self, idea: Dict) -> Dict:
        # Would generate content
        return {"success": True, "type": "content", "status": "draft"}
        
    async def _get_ideas(self, params: Dict) -> Dict:
        status = params.get("status", "all")
        ideas = list(self._active_ideas.values())
        if status != "all":
            ideas = [i for i in ideas if i.get("status") == status]
        return {"success": True, "ideas": ideas}
        
    async def _get_sandbox_results(self, params: Dict) -> Dict:
        idea_id = params.get("idea_id")
        return {"success": True, "results": self._sandbox_results.get(idea_id, {})}
        
    async def _promote_idea(self, params: Dict) -> Dict:
        """Promote idea to next autonomy level after sandbox testing."""
        idea_id = params.get("idea_id")
        if idea_id not in self._active_ideas:
            return {"success": False, "error": "Idea not found"}
            
        idea = self._active_ideas[idea_id]
        if idea_id not in self._sandbox_results:
            return {"success": False, "error": "No sandbox results - run test first"}
            
        results = self._sandbox_results[idea_id]
        if results.get("success", False):
            idea["status"] = "promoted"
            idea["promoted_at"] = datetime.now(timezone.utc).isoformat()
            return {"success": True, "promoted": True, "idea": idea}
        return {"success": False, "error": "Sandbox test failed"}
        
    async def _run_sandbox_test(self, params: Dict) -> Dict:
        """Run paper/sandbox test per Part 4.6."""
        idea_id = params.get("idea_id")
        if idea_id not in self._active_ideas:
            return {"success": False, "error": "Idea not found"}
            
        idea = self._active_ideas[idea_id]
        
        # Simulate sandbox test
        await asyncio.sleep(1)
        
        # Simulated results
        results = {
            "success": True,
            "profit_estimate": random.uniform(10, 500),
            "time_estimate_hours": random.uniform(1, 10),
            "risk_score": random.uniform(0.1, 0.5),
            "automation_feasibility": random.uniform(0.6, 0.95),
            "tested_at": datetime.now(timezone.utc).isoformat()
        }
        
        self._sandbox_results[idea["id"]] = results
        return {"success": True, "results": results}
        
    def get_status(self) -> Dict:
        return {
            "domain": "opportunity",
            "autonomy_level": 1,
            "target_ceiling": 4,
            "active_ideas": len(self._active_ideas),
            "completed": len(self._completed_ideas),
            "sandbox_tested": len(self._sandbox_results)
        }
        
    def get_proposals(self) -> List[Dict]:
        return []