"""
FastAPI Dashboard — Part 4.2: Boss's primary window into the system.
Shows safety status, approval queue, audit log, kill switch.
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
import json
import uvicorn

from core.safety_guardian import get_safety_guardian, get_safety_status, KillLayer, KillReason
from core.audit_log import read_audit_log, get_audit_stats, get_recent_entries
from core.credential_vault import get_vault
from actions._api import _load_env

_load_env()

app = FastAPI(title="JARVIS Dashboard")

# Templates
templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# WebSocket connections for real-time updates
active_websockets: List[WebSocket] = []

class KillRequest(BaseModel):
    layer: str  # "LOCAL_STOP", "REMOTE_STOP", etc.
    reason: str
    domain: str
    details: Optional[Dict] = None

class AcknowledgeRequest(BaseModel):
    kill_index: int

class CredentialRequest(BaseModel):
    key: str
    value: str
    metadata: Optional[Dict] = None

class ApprovalAction(BaseModel):
    entry_id: str
    action: str  # "approve" | "deny"

@app.on_event("startup")
async def startup():
    # Initialize safety guardian monitoring
    from core.safety_guardian import get_safety_guardian
    sg = get_safety_guardian()
    await sg.start_monitoring()
    
    # Broadcast initial status
    await broadcast_status()

@app.on_event("shutdown")
async def shutdown():
    from core.safety_guardian import get_safety_guardian
    sg = get_safety_guardian()
    await sg.stop_monitoring()

async def broadcast_status():
    """Broadcast safety status to all connected websockets."""
    status = get_safety_status()
    message = json.dumps({"type": "status", "data": status})
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        active_websockets.remove(ws)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/api/status")
async def get_status():
    return get_safety_status()

@app.get("/api/audit/stats")
async def audit_stats():
    from core.audit_log import get_audit_stats
    return get_audit_stats()

@app.get("/api/audit/recent")
async def audit_recent(domain: Optional[str] = None, count: int = 50):
    from core.audit_log import get_recent_entries
    return get_recent_entries(domain=domain, count=count)

@app.get("/api/audit/search")
async def audit_search(query: str, domain: Optional[str] = None, limit: int = 100):
    from core.audit_log import search_audit
    return search_audit(query, domain=domain, limit=limit)

@app.get("/api/audit/entries")
async def audit_entries(domain: Optional[str] = None, since: Optional[str] = None, limit: int = 100):
    from core.audit_log import read_audit_log
    return read_audit_log(domain=domain, since=since, limit=limit)

@app.post("/api/kill")
async def trigger_kill(request: KillRequest):
    from core.safety_guardian import get_safety_guardian, KillLayer, KillReason
    sg = get_safety_guardian()
    
    try:
        layer = KillLayer[request.layer]
        reason = KillReason(request.reason)
    except (KeyError, ValueError):
        raise HTTPException(400, "Invalid layer or reason")

    sg.trigger_kill(layer, reason, request.domain, request.details)
    await broadcast_status()
    return {"status": "triggered"}

@app.post("/api/kill/acknowledge")
async def acknowledge_kill(request: AcknowledgeRequest):
    sg = get_safety_guardian()
    sg.acknowledge_kill(request.kill_index, boss_confirmed=True)
    await broadcast_status()
    return {"status": "acknowledged"}

@app.post("/api/circuit-breaker/reset")
async def reset_breaker(name: str, confirmed: bool = True):
    sg = get_safety_guardian()
    try:
        sg.reset_circuit_breaker(name, boss_confirmed=confirmed)
        return {"status": "reset"}
    except PermissionError as e:
        raise HTTPException(403, str(e))

@app.get("/api/credentials")
async def list_credentials():
    from core.credential_vault import get_vault
    vault = get_vault()
    keys = vault.list_keys()
    return {"keys": keys}

@app.post("/api/credentials")
async def store_credential(request: CredentialRequest):
    from core.credential_vault import store_credential
    store_credential(request.key, request.value, request.metadata)
    return {"status": "stored"}

@app.delete("/api/credentials/{key}")
async def delete_credential(key: str):
    from core.credential_vault import delete_credential
    if delete_credential(key):
        return {"status": "deleted"}
    raise HTTPException(404, "Not found")

@app.get("/api/audit/verify")
async def verify_audit():
    from core.audit_log import verify_log_integrity
    return verify_log_integrity()


# ─── Payment webhook receiver + revenue/reconciliation endpoints ────────────────

class PaymentWebhook(BaseModel):
    gateway: str          # "paypal" | "dpo" | "fnb" | "bank_transfer"
    reference: str
    webhook_data: Dict    # gateway-specific payload (trusted once HMAC verified upstream)

@app.post("/api/webhooks/payment")
async def payment_webhook(request: PaymentWebhook):
    """Receive a payment confirmation from any gateway and record verified income."""
    from actions.namibian_payments import verify_payment
    result = verify_payment(request.gateway, request.reference, request.webhook_data)
    if result.get("verified"):
        await broadcast_status()
    return result

class ManualIncome(BaseModel):
    gateway: str
    amount: float
    currency: str = "USD"
    reference: str = ""

@app.post("/api/income/confirm")
async def confirm_income(request: ManualIncome):
    """Manually confirm received income (e.g. boss confirms bank transfer receipt)."""
    from actions.namibian_payments import record_verified_income
    rec = record_verified_income(
        request.gateway, request.amount, request.currency,
        request.reference, proof="dashboard_manual_confirm",
    )
    if rec is None:
        return {"status": "already_recorded", "note": "Idempotent — no double count"}
    await broadcast_status()
    return {"status": "recorded", "amount": request.amount, "currency": request.currency,
            "audit_entry": rec.get("entry_id")}

@app.get("/api/revenue")
async def revenue_stats():
    """Current revenue: total earned, balance, recent transactions."""
    from actions.namibian_payments import _load_revenue_file
    rev = _load_revenue_file()
    txns = rev.get("transactions", [])[-20:]  # last 20
    return {
        "total_earned": rev.get("total_earned", 0),
        "total_withdrawn": rev.get("total_withdrawn", 0),
        "balance": rev.get("balance", 0),
        "recent": txns,
    }

@app.get("/api/reconciliation")
async def reconciliation(days: int = 30):
    """30-day audit↔revenue reconciliation."""
    from actions.reconciliation import reconcile_30d
    return reconcile_30d(days=days)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        # Send initial status
        await websocket.send_text(json.dumps({"type": "status", "data": get_safety_status()}))
        while True:
            data = await websocket.receive_text()
            # Echo for keepalive
            await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

# Mount static files
static_dir = Path(__file__).resolve().parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)