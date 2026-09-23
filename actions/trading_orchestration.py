"""
Trading Orchestration Agent — Part 3.5.1: Directs GFT Matrix + Aegis.
Sits above existing engines, respects their circuit breakers.
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.domain_agent import DomainAgent, DomainConfig
from core.safety_guardian import is_killed, is_breaker_tripped, log_audit
from core.audit_log import write_audit_entry

class TradingOrchestrationAgent(DomainAgent):
    """Orchestrates GFT Matrix + Aegis - respects their circuit breakers."""
    
    def __init__(self):
        config = DomainConfig(
            domain="trading",
            autonomy_level=5,  # Part 4.1: already has mature circuit breakers
            target_ceiling=5,
            caps={
                "max_daily_loss_pct": 2.0,
                "max_position_size_pct": 5.0,
                "max_capital_at_risk_pct": 20.0
            },
            always_requires_approval=[
                "withdrawal", "new_payee", "account_creation",
                "change_risk_params", "override_circuit_breaker"
            ],
            allowlist=[]
        )
        super().__init__(config)
        self._session_active = False
        self._positions = {}
        self._daily_pnl = 0.0
        self._gft_config = {
            "enabled": True,
            "config_path": "config/gft_matrix_config.json"
        }
        self._aegis_config = {
            "enabled": True,
            "config_path": "config/aegis_config.json"
        }
        
    async def handle(self, action: str, params: Dict) -> Any:
        if is_killed("trading"):
            return {"success": False, "error": "Trading domain killed by safety guardian"}
            
        if action == "start_session":
            return await self._start_session(params)
        elif action == "stop_session":
            return await self._stop_session(params)
        elif action == "get_status":
            return await self._get_status()
        elif action == "get_positions":
            return await self._get_positions()
        elif action == "get_pnl":
            return await self._get_pnl(params)
        elif action == "analyze_market":
            return await self._analyze_market(params)
        elif action == "execute_trade":
            return await self._execute_trade(params)
        elif action == "get_circuit_breakers":
            return await self._get_circuit_breakers()
        elif action == "override_breaker":
            return await self._override_breaker(params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
            
    async def _start_session(self, params: Dict) -> Dict:
        # Check financial circuit breakers
        if is_breaker_tripped("financial_daily_loss"):
            return {"success": False, "error": "Daily loss limit reached"}
        if is_breaker_tripped("financial_capital_at_risk"):
            return {"success": False, "error": "Capital at risk limit reached"}
            
        # Start GFT Matrix engine
        gft_result = await self._start_gft_matrix()
        
        # Start Aegis
        aegis_result = await self._start_aegis()
        
        return {
            "success": True,
            "session_started": True,
            "gft_matrix": gft_result,
            "aegis": aegis_result
        }
        
    async def _stop_session(self, params: Dict) -> Dict:
        # Gracefully stop both engines
        return {"success": True, "session_stopped": True}
        
    async def _get_status(self) -> Dict:
        return {
            "domain": "trading",
            "autonomy_level": 5,
            "target_ceiling": 5,
            "session_active": False,
            "daily_pnl": self._daily_pnl,
            "positions": len({}),
            "gft_matrix_status": "ready",
            "aegis_status": "ready"
        }
        
    async def _get_positions(self) -> Dict:
        return {"success": True, "positions": []}
        
    async def _get_pnl(self, params: Dict) -> Dict:
        # Would fetch from broker API
        return {
            "success": True,
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "monthly_pnl": 0.0,
            "total_pnl": 0.0
        }
        
    async def _analyze_market(self, params: Dict) -> Dict:
        symbols = params.get("symbols", ["BTC", "ETH"])
        # Would call GFT Matrix analysis
        return {
            "success": True,
            "analysis": {s: {"signal": "neutral", "confidence": 0.5} for s in params.get("symbols", [])}
        }
        
    async def _execute_trade(self, params: Dict) -> Dict:
        # Would execute via GFT Matrix
        return {"success": True, "order_id": "placeholder", "status": "simulated"}
        
    async def _start_gft_matrix(self) -> Dict:
        return {"started": True, "engine": "GFT Matrix"}
        
    async def _start_aegis(self) -> Dict:
        return {"started": True, "engine": "Aegis AI MT5"}
        
    async def _get_circuit_breakers(self) -> Dict:
        return {
            "gft_matrix": {
                "daily_loss_limit": "2%",
                "position_size_limit": "5%",
                "capital_at_risk": "20%"
            },
            "aegis": {
                "daily_loss_limit": "1%",
                "position_size_limit": "3%",
                "max_trades_per_hour": 10
            }
        }
        
    async def _override_breaker(self, params: Dict) -> Dict:
        # Part 4.4: overriding breaker requires Boss approval
        if not params.get("approved", False):
            return {"success": False, "error": "Override requires Boss approval", "requires_approval": True}
        return {"success": True, "overridden": True}
        
    def get_status(self) -> Dict:
        return {
            "domain": "trading",
            "autonomy_level": 5,
            "target_ceiling": 5,
            "session_active": False,
            "daily_pnl": 0.0
        }
        
    def get_proposals(self) -> List[Dict]:
        return []