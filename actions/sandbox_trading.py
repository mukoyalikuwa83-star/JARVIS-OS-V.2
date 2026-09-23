"""
Paper/Sandbox Trading Mode — Part 4.6: Simulated environment for testing strategies.
All new strategies and Track B ideas must pass sandbox before real execution.
"""
import asyncio
import json
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from core.safety_guardian import get_safety_guardian, log_audit
from core.audit_log import write_audit_entry

class SandboxMode(Enum):
    PAPER = "paper"           # Simulated with historical data
    SIMULATED = "simulated"   # Real-time simulation with fake capital
    BACKTEST = "backtest"     # Historical backtesting

class SandboxStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

@dataclass
class SandboxConfig:
    mode: SandboxMode = SandboxMode.PAPER
    starting_capital: float = 10000.0
    max_position_pct: float = 5.0
    max_daily_loss_pct: float = 2.0
    max_drawdown_pct: float = 10.0
    commission_pct: float = 0.1
    slippage_pct: float = 0.05
    data_source: str = "historical"  # "historical" | "realtime" | "synthetic"
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL", "DOGE"])
    timeframe: str = "1h"
    max_trades_per_day: int = 10

@dataclass
class SandboxPosition:
    symbol: str
    side: str  # "long" | "short"
    size: float
    entry_price: float
    entry_time: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@dataclass
class SandboxTrade:
    trade_id: str
    symbol: str
    side: str
    size: float
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: str = ""
    exit_time: Optional[str] = None
    pnl: float = 0.0
    commission: float = 0.0
    status: str = "open"

@dataclass
class SandboxSession:
    session_id: str
    config: SandboxConfig
    status: SandboxStatus = SandboxStatus.RUNNING
    capital: float = 10000.0
    starting_capital: float = 10000.0
    positions: Dict[str, SandboxPosition] = field(default_factory=dict)
    trades: List[SandboxTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

class SandboxEngine:
    """Paper/sandbox trading engine for testing strategies safely."""
    
    def __init__(self):
        self._sessions: Dict[str, SandboxSession] = {}
        self._market_data: Dict[str, List[Dict]] = {}
        self._price_callbacks: List[Callable] = []
        self._running = False
        self._update_task: Optional[asyncio.Task] = None
        
    async def create_session(self, config: SandboxConfig = None) -> str:
        """Create a new sandbox session."""
        session_id = f"sandbox_{int(time.time())}_{random.randint(1000,9999)}"
        config = config or SandboxConfig()
        
        session = SandboxSession(
            session_id=session_id,
            config=config,
            capital=config.starting_capital,
            starting_capital=config.starting_capital,
            equity_curve=[config.starting_capital]
        )
        
        self._sessions[session_id] = session
        await self._save_session(session)
        
        write_audit_entry(
            domain="sandbox",
            action_proposed="create_session",
            screening_result="passed",
            gate_result="auto_approved:1",
            execution_result="success",
            real_outcome={"session_id": session_id, "mode": config.mode.value},
            reasoning_summary=f"Created sandbox session in {config.mode.value} mode",
            credential_used="none"
        )
        
        return session_id
        
    async def get_session(self, session_id: str) -> Optional[SandboxSession]:
        return self._sessions.get(session_id)
        
    async def list_sessions(self) -> List[Dict]:
        return [
            {
                "session_id": s.session_id,
                "mode": s.config.mode.value,
                "status": s.status.value,
                "capital": s.capital,
                "starting_capital": s.starting_capital,
                "pnl_pct": ((s.capital - s.starting_capital) / s.starting_capital * 100) if s.starting_capital > 0 else 0,
                "total_trades": s.total_trades,
                "win_rate": (s.winning_trades / s.total_trades * 100) if s.total_trades > 0 else 0,
                "max_drawdown": s.max_drawdown,
                "created_at": s.created_at
            }
            for s in self._sessions.values()
        ]
        
    async def place_order(self, session_id: str, symbol: str, side: str, 
                         size: float, order_type: str = "market", 
                         price: Optional[float] = None, 
                         stop_loss: Optional[float] = None,
                         take_profit: Optional[float] = None) -> Dict:
        """Place an order in the sandbox."""
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
            
        if session.status != SandboxStatus.RUNNING:
            return {"success": False, "error": "Session not running"}
            
        # Check circuit breakers
        if session.daily_pnl <= -session.config.max_daily_loss_pct / 100 * session.starting_capital:
            return {"success": False, "error": "Daily loss limit reached"}
            
        if len(session.trades) >= session.config.max_trades_per_day:
            return {"success": False, "error": "Max trades per day reached"}
            
        # Get current price (simulated)
        current_price = await self._get_price(session_id, symbol)
        if current_price is None:
            return {"success": False, "error": "Price not available"}
            
        # Calculate position size
        max_position_value = session.capital * session.config.max_position_pct / 100
        order_value = size * current_price
        if order_value > max_position_value:
            return {"success": False, "error": f"Position size exceeds limit ({session.config.max_position_pct}%)"}
            
        # Check capital
        required_capital = order_value * (1 + session.config.commission_pct / 100)
        if required_capital > session.capital:
            return {"success": False, "error": "Insufficient capital"}
            
        # Create position
        position = SandboxPosition(
            symbol=symbol,
            side=side.lower(),
            size=size,
            entry_price=current_price,
            entry_time=datetime.now(timezone.utc).isoformat(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        session.positions[symbol] = position
        session.capital -= required_capital
        
        trade = SandboxTrade(
            trade_id=f"trade_{int(time.time())}_{random.randint(1000,9999)}",
            symbol=symbol,
            side=side.lower(),
            size=size,
            entry_price=current_price,
            entry_time=datetime.now(timezone.utc).isoformat(),
            commission=required_capital * session.config.commission_pct / 100,
            status="open"
        )
        session.trades.append(trade)
        session.total_trades += 1
        
        await self._save_session(session)
        
        write_audit_entry(
            domain="sandbox",
            action_proposed="place_order",
            screening_result="passed",
            gate_result="auto_approved",
            execution_result="success",
            real_outcome={"session_id": session_id, "trade_id": trade.trade_id},
            reasoning_summary=f"Paper trade: {side} {size} {symbol} @ {current_price}",
            credential_used="none"
        )
        
        return {
            "success": True,
            "trade_id": trade.trade_id,
            "symbol": symbol,
            "side": side,
            "size": size,
            "entry_price": current_price,
            "commission": trade.commission
        }
        
    async def close_position(self, session_id: str, symbol: str, 
                            reason: str = "manual") -> Dict:
        """Close an open position."""
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
            
        position = session.positions.get(symbol)
        if not position:
            return {"success": False, "error": "Position not found"}
            
        current_price = await self._get_price(session_id, symbol)
        if current_price is None:
            return {"success": False, "error": "Price not available"}
            
        # Calculate PnL
        if position.side == "long":
            pnl = (current_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - current_price) * position.size
            
        commission = position.size * current_price * session.config.commission_pct / 100
        net_pnl = pnl - commission
        
        # Update session
        session.capital += position.size * current_price * (1 - session.config.commission_pct / 100)
        session.daily_pnl += net_pnl
        
        # Update trade record
        for trade in session.trades:
            if trade.symbol == symbol and trade.status == "open":
                trade.exit_price = current_price
                trade.exit_time = datetime.now(timezone.utc).isoformat()
                trade.pnl = net_pnl
                trade.status = "closed"
                break
                
        session.total_trades += 1
        if net_pnl > 0:
            session.winning_trades += 1
        else:
            session.losing_trades += 1
            
        # Update drawdown
        equity = session.capital
        for p in session.positions.values():
            px = await self._get_price(session_id, p.symbol)
            equity += p.size * (px or p.entry_price)
        drawdown = (session.starting_capital - equity) / session.starting_capital * 100
        if drawdown > session.max_drawdown:
            session.max_drawdown = drawdown
            
        session.equity_curve.append(equity)
        session.updated_at = datetime.now(timezone.utc).isoformat()
        
        del session.positions[symbol]
        await self._save_session(session)
        
        write_audit_entry(
            domain="sandbox",
            action_proposed="close_position",
            screening_result="passed",
            gate_result="auto_approved",
            execution_result="success",
            real_outcome={"session_id": session_id, "symbol": symbol, "pnl": net_pnl},
            reasoning_summary=f"Closed {position.side} {symbol} @ {current_price}, PnL: {net_pnl:.2f}",
            credential_used="none"
        )
        
        return {
            "success": True,
            "symbol": symbol,
            "exit_price": current_price,
            "pnl": net_pnl,
            "commission": commission
        }
        
    async def _get_price(self, session_id: str, symbol: str) -> Optional[float]:
        """Get current price - simulated based on mode."""
        session = self._sessions.get(session_id)
        if not session:
            return None
            
        # Simulate price movement
        base_prices = {
            "BTC": 80000, "ETH": 3000, "SOL": 150, "DOGE": 0.1,
            "BTCUSDT": 80000, "ETHUSDT": 3000, "SOLUSDT": 150, "DOGEUSDT": 0.1
        }
        
        base = base_prices.get(symbol, 100)
        # Add random walk
        volatility = 0.02  # 2% per tick
        change = random.uniform(-volatility, volatility)
        return base * (1 + change)
        
    async def _save_session(self, session: SandboxSession):
        session.updated_at = datetime.now(timezone.utc).isoformat()
        
    def get_status(self) -> Dict:
        return {
            "active_sessions": len(self._sessions),
            "total_sessions": len(self._sessions)
        }

# Global singleton
_sandbox_engine: Optional["SandboxEngine"] = None

def get_sandbox_engine() -> "SandboxEngine":
    global _sandbox_engine
    if _sandbox_engine is None:
        _sandbox_engine = SandboxEngine()
    return _sandbox_engine