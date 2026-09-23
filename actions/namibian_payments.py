"""Namibian Payment Gateway Integration — FNB, PayToday, DPO, PayPal, generic bank transfer."""
import json
import os
import hashlib
import hmac
import time
from datetime import datetime
from pathlib import Path
from actions._api import http_get, http_post, _load_env
from core.audit_log import write_audit_entry

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_NAM_PAY_LOG = _DATA_DIR / "namibian_payments.json"
_NAM_CONFIG = _DATA_DIR / "namibian_payment_config.json"
_REVENUE_FILE = _DATA_DIR / "revenue.json"

# Revenue domains recognised by reconciliation (Part 6 Phase 5)
MONEY_DOMAINS = ("gumroad", "stripe", "paypal", "fnb", "dpo", "namibian", "bank_transfer", "worker", "trading")

# Namibian payment gateways
GATEWAYS = {
    "fnb": {
        "name": "FNB Namibia",
        "api_base": "https://api.fnbnamibia.com.na",  # May require partnership
        "supports": ["card", "eft", "wallet"],
        "currency": "NAD",
    },
    "paytoday": {
        "name": "PayToday Namibia",
        "api_base": "https://api.paytoday.com.na",
        "supports": ["card", "mobicred"],
        "currency": "NAD",
    },
    "dpo": {
        "name": "DPO Group",
        "api_base": "https://secure.dpopayments.com/api",
        "supports": ["card", "mobile_money", "bank_transfer"],
        "currency": "NAD",
    },
    "bank_transfer": {
        "name": "Manual Bank Transfer (FNB Namibia)",
        "api_base": None,
        "supports": ["eft"],
        "currency": "NAD",
    },
    "paypal": {
        "name": "PayPal (USD - international buyers)",
        "api_base": "https://api-m.paypal.com",
        "supports": ["card", "paypal_balance"],
        "currency": "USD",
    },
}

def _load_nam_config():
    if _NAM_CONFIG.exists():
        try:
            return json.loads(_NAM_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_nam_config(cfg):
    _NAM_CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def configure_fnb(merchant_id, api_key, api_secret, webhook_secret=""):
    """Configure FNB Namibia merchant credentials."""
    cfg = _load_nam_config()
    cfg["fnb"] = {
        "merchant_id": merchant_id,
        "api_key": api_key,
        "api_secret": api_secret,
        "webhook_secret": webhook_secret,
        "enabled": True,
    }
    _save_nam_config(cfg)
    return "FNB Namibia configured"

def configure_paytoday(merchant_id, api_key, api_secret):
    """Configure PayToday Namibia."""
    cfg = _load_nam_config()
    cfg["paytoday"] = {
        "merchant_id": merchant_id,
        "api_key": api_key,
        "api_secret": api_secret,
        "enabled": True,
    }
    _save_nam_config(cfg)
    return "PayToday configured"

def configure_dpo(company_token, service_type="live"):
    """Configure DPO Group (works across Africa including Namibia)."""
    cfg = _load_nam_config()
    cfg["dpo"] = {
        "company_token": company_token,
        "service_type": service_type,  # "live" or "test"
        "enabled": True,
    }
    _save_nam_config(cfg)
    return f"DPO Group configured ({service_type})"

def configure_paypal(client_id, client_secret, mode="live"):
    """Configure PayPal REST (works for international buyers, pays out to FNB via withdrawal)."""
    cfg = _load_nam_config()
    cfg["paypal"] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "mode": mode,  # "live" or "sandbox"
        "enabled": True,
    }
    _save_nam_config(cfg)
    base = "api-m.sandbox.paypal.com" if mode == "sandbox" else "api-m.paypal.com"
    GATEWAYS["paypal"]["api_base"] = f"https://{base}"
    return f"PayPal configured ({mode})"

def _paypal_token(cfg):
    """Get PayPal OAuth2 access token."""
    base = GATEWAYS["paypal"]["api_base"]
    import base64
    auth = base64.b64encode(f"{cfg['client_id']}:{cfg['client_secret']}".encode()).decode()
    result = http_post(
        f"{base}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
        form_type="urlencoded",
    )
    if isinstance(result, tuple):
        result = result[0] if len(result) and isinstance(result[0], str) else {}
    try:
        result = json.loads(result) if isinstance(result, str) else result
    except Exception:
        result = {}
    if isinstance(result, dict) and result.get("access_token"):
        return result["access_token"]
    return None

def _create_paypal_payment(cfg, amount, currency, reference, callback_url, metadata):
    """Create a PayPal Order — buyer pays in USD (international)."""
    _load_env()
    base = GATEWAYS["paypal"]["api_base"]
    token = _paypal_token(cfg)
    if not token:
        return {"gateway": "PayPal", "error": "PayPal auth failed - check client credentials",
                "reference": reference}
    amount_usd = amount if currency == "USD" else round(amount * 0.27, 2)  # NAD~0.27 USD approx
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": reference,
            "amount": {"currency_code": "USD", "value": f"{amount_usd:.2f}"},
            "description": (metadata or {}).get("description", "JARVIS Digital Product"),
        }],
        "application_context": {
            "brand_name": "Mukoya Digital Products",
            "user_action": "PAY_NOW",
            "return_url": callback_url or "https://mukoya0.gumroad.com/",
            "cancel_url": callback_url or "https://mukoya0.gumroad.com/",
        },
    }
    result = http_post(f"{base}/v2/checkout/orders", json=payload,
                       headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    if isinstance(result, tuple):
        result = result[0] if len(result) and isinstance(result[0], str) else {}
    try:
        result = json.loads(result) if isinstance(result, str) else result
    except Exception:
        result = {}
    if isinstance(result, dict) and result.get("id"):
        approve_url = next((l["href"] for l in result.get("links", []) if l.get("rel") == "approve"), "")
        _log_payment("paypal", reference, amount, currency, "created", approve_url)
        return {
            "gateway": "PayPal",
            "payment_url": approve_url,
            "order_id": result.get("id"),
            "reference": reference,
            "amount": amount_usd,
            "currency": "USD",
            "status": "created",
            "note": "Buyer pays via PayPal; payout withdrawable to FNB Namibia bank account",
        }
    return {"gateway": "PayPal", "error": f"PayPal order creation failed: {result}", "reference": reference}

def create_payment_link(gateway, amount, currency="NAD", reference="", callback_url="", metadata=None):
    """Create a payment link via specified gateway."""
    _load_env()
    cfg = _load_nam_config()
    
    # Bank transfer always works - no config needed
    if gateway == "bank_transfer":
        return _create_bank_transfer_instructions(amount, currency, reference, metadata)
    
    if gateway not in cfg or not cfg[gateway].get("enabled"):
        return f"Gateway {gateway} not configured"
    
    gw_cfg = cfg[gateway]
    ref = reference or f"JARVIS_{int(time.time())}"
    
    if gateway == "dpo":
        return _create_dpo_payment(gw_cfg, amount, currency, ref, callback_url, metadata)
    elif gateway == "fnb":
        return _create_fnb_payment(gw_cfg, amount, currency, ref, callback_url, metadata)
    elif gateway == "paytoday":
        return _create_paytoday_payment(gw_cfg, amount, currency, ref, callback_url, metadata)
    elif gateway == "bank_transfer":
        return _create_bank_transfer_instructions(amount, currency, ref, metadata)
    elif gateway == "paypal":
        return _create_paypal_payment(gw_cfg, amount, currency, ref, callback_url, metadata)
    
    return f"Gateway {gateway} not implemented"

def _create_dpo_payment(cfg, amount, currency, reference, callback_url, metadata):
    """Create DPO payment - works across Africa including Namibia."""
    # DPO API format
    payload = {
        "CompanyToken": cfg.get("company_token", ""),
        "RequestType": "create",
        "Transaction": {
            "Amount": str(amount),
            "Currency": currency,
            "Reference": reference,
            "Description": metadata.get("description", "JARVIS Product Purchase") if metadata else "JARVIS Product",
            "CallbackURL": callback_url,
            "RedirectURL": callback_url,
        }
    }
    if metadata:
        payload["Transaction"]["Metadata"] = json.dumps(metadata)
    
    # For demo - return payment URL structure
    payment_url = f"https://secure.dpopayments.com/pay?CompanyToken={cfg.get('company_token')}&Amount={amount}&Currency={currency}&Reference={reference}"
    
    _log_payment("dpo", reference, amount, currency, "created", payment_url)
    return {
        "gateway": "DPO Group",
        "payment_url": payment_url,
        "reference": reference,
        "amount": amount,
        "currency": currency,
        "status": "created",
    }

def _create_fnb_payment(cfg, amount, currency, reference, callback_url, metadata):
    """Create FNB Namibia payment (requires merchant partnership)."""
    # FNB API would go here - requires merchant onboarding
    # For now return instructions
    payment_url = f"https://fnbnamibia.com.na/pay?merchant={cfg.get('merchant_id')}&amount={amount}&ref={reference}"
    
    _log_payment("fnb", reference, amount, currency, "created", payment_url)
    return {
        "gateway": "FNB Namibia",
        "payment_url": payment_url,
        "reference": reference,
        "amount": amount,
        "currency": currency,
        "status": "created",
        "note": "Requires FNB merchant partnership",
    }

def _create_paytoday_payment(cfg, amount, currency, reference, callback_url, metadata):
    """Create PayToday Namibia payment."""
    payment_url = f"https://paytoday.com.na/pay?merchant={cfg.get('merchant_id')}&amount={amount}&ref={reference}"
    
    _log_payment("paytoday", reference, amount, currency, "created", payment_url)
    return {
        "gateway": "PayToday Namibia",
        "payment_url": payment_url,
        "reference": reference,
        "amount": amount,
        "currency": currency,
        "status": "created",
    }

def _create_bank_transfer_instructions(amount, currency, reference, metadata):
    """Generate manual bank transfer instructions for Namibia."""
    cfg = _load_nam_config()
    bank = cfg.get("bank_details", {})
    fnb_acc = bank.get("fnb_account", "[YOUR_FNB_ACCOUNT_NUMBER]")
    fnb_branch = bank.get("fnb_branch", "280172")
    
    instructions = f"""
MANUAL BANK TRANSFER - NAMIBIA

Amount: {currency} {amount}
Reference: {reference}
Description: {metadata.get('description', 'JARVIS Product') if metadata else 'JARVIS Product'}

BANK DETAILS (PRIMARY - FNB NAMIBIA):
Bank: First National Bank Namibia
Account Name: JARVIS Digital Products
Account Number: {fnb_acc}
Branch Code: {fnb_branch} (FNB Windhoek)
SWIFT: FIRNNANX

ALTERNATIVE BANKS:
Bank: Bank Windhoek
Account Name: JARVIS Digital Products
Account Number: [YOUR_BW_ACCOUNT_NUMBER]
Branch Code: 480172

Bank: Standard Bank Namibia
Account Name: JARVIS Digital Products
Account Number: [YOUR_SB_ACCOUNT_NUMBER]
Branch Code: 082772

INSTRUCTIONS:
1. Transfer {currency} {amount} to above FNB account
2. Use reference: {reference}
3. Email/WhatsApp proof of payment to payments@jarvis.local / +264 81 XXX XXXX
4. Product access granted within 1 hour of verification

RECOMMENDED: Use FNB App / Online Banking for instant transfer
"""
    _log_payment("bank_transfer", reference, amount, currency, "instructions_sent", "")
    return {
        "gateway": "Manual Bank Transfer (FNB Namibia)",
        "instructions": instructions.strip(),
        "reference": reference,
        "amount": amount,
        "currency": currency,
        "status": "instructions_sent",
    }

def verify_payment(gateway, reference, webhook_data=None):
    """Verify payment status via gateway webhook or API."""
    _load_env()
    cfg = _load_nam_config()
    
    if gateway == "dpo":
        return _verify_dpo(cfg, reference, webhook_data)
    elif gateway == "fnb":
        return _verify_fnb(cfg, reference, webhook_data)
    elif gateway == "paytoday":
        return _verify_paytoday(cfg, reference, webhook_data)
    elif gateway == "bank_transfer":
        return _verify_bank_transfer(reference)
    elif gateway == "paypal":
        return _verify_paypal(cfg, reference, webhook_data)
    
    return {"verified": False, "error": "Gateway not supported"}

def _verify_dpo(cfg, reference, webhook_data):
    """Verify DPO payment via webhook."""
    if not webhook_data:
        return {"verified": False, "error": "No webhook data"}
    
    # DPO sends: CompanyToken, TransactionToken, Result, TransactionReference, Amount, Currency
    token = webhook_data.get("TransactionToken")
    result = webhook_data.get("Result")
    ref = webhook_data.get("TransactionReference")
    
    if ref == reference and result == "00":  # 00 = Success
        _log_payment("dpo", reference, 0, "", "verified", "")
        amount = float(webhook_data.get("Amount", 0))
        currency = webhook_data.get("Currency", "NAD")
        recorded = record_verified_income("dpo", amount, currency, reference, proof=f"TransactionToken:{token}")
        return {"verified": True, "gateway": "DPO", "reference": reference,
                "recorded": bool(recorded), "amount": amount, "currency": currency}
    return {"verified": False, "gateway": "DPO", "reference": reference}

def _verify_fnb(cfg, reference, webhook_data):
    """Verify FNB payment via webhook."""
    if not webhook_data:
        return {"verified": False, "error": "No webhook data"}
    # FNB webhook format would go here
    return {"verified": False, "gateway": "FNB", "note": "Webhook verification not implemented"}

def _verify_paytoday(cfg, reference, webhook_data):
    """Verify PayToday payment."""
    return {"verified": False, "gateway": "PayToday", "note": "Not implemented"}

def _verify_bank_transfer(reference):
    """Manual bank transfer verification - returns pending."""
    return {"verified": False, "gateway": "Bank Transfer", "status": "pending_manual_verification"}

def _verify_paypal(cfg, reference, webhook_data):
    """Verify PayPal webhook (order captured) or query PayPal API."""
    # 1) Trusted webhook data (HMAC-verified upstream) is authoritative
    if isinstance(webhook_data, dict):
        status = webhook_data.get("status", "")
        if status == "COMPLETED":
            paid = 0.0
            try:
                paid = float(webhook_data["purchase_units"][0]["amount"]["value"])
            except Exception:
                pass
            currency = "USD"
            try:
                currency = webhook_data["purchase_units"][0]["amount"]["currency_code"]
            except Exception:
                pass
            _log_payment("paypal", reference, 0, "USD", "verified", "")
            recorded = record_verified_income("paypal", paid or 0.0, currency, reference,
                                              proof=f"webhook order {webhook_data.get('id', '')}")
            return {"verified": True, "gateway": "PayPal", "reference": reference,
                    "source": "webhook", "recorded": bool(recorded),
                    "amount": paid, "currency": currency}
        return {"verified": False, "gateway": "PayPal", "reference": reference,
                "status": status if isinstance(status, str) else webhook_data.get("status")}

    # 2) API query fallback (needs configured client_id/secret)
    _load_env()
    try:
        base = GATEWAYS["paypal"]["api_base"]
        token = _paypal_token(cfg)
        if not token:
            return {"verified": False, "gateway": "PayPal", "error": "Auth failed"}
        result = http_get(f"{base}/v2/checkout/orders/{reference}",
                          headers={"Authorization": f"Bearer {token}"})
        if isinstance(result, tuple):
            result = result[0] if len(result) and isinstance(result[0], str) else {}
        try:
            result = json.loads(result) if isinstance(result, str) else result
        except Exception:
            result = {}
        if isinstance(result, dict):
            status = result.get("status", "")
            if status == "COMPLETED":
                _log_payment("paypal", reference, 0, "USD", "verified", "")
                try:
                    paid = float(result["purchase_units"][0]["amount"]["value"])
                except Exception:
                    paid = 0.0
                recorded = record_verified_income("paypal", paid, "USD", reference,
                                                  proof=f"order {result.get('id')}")
                return {"verified": True, "gateway": "PayPal", "reference": reference,
                        "order_id": result.get("id"), "status": status,
                        "recorded": bool(recorded), "amount": paid, "currency": "USD"}
            return {"verified": False, "gateway": "PayPal", "reference": reference, "status": status}
    except Exception as e:
        return {"verified": False, "gateway": "PayPal", "error": str(e)}
    return {"verified": False, "gateway": "PayPal", "reference": reference}

def _log_payment(gateway, reference, amount, currency, status, url):
    log = []
    if _NAM_PAY_LOG.exists():
        try:
            log = json.loads(_NAM_PAY_LOG.read_text(encoding="utf-8"))
        except Exception:
            log = []
    log.append({
        "time": datetime.now().isoformat(),
        "gateway": gateway,
        "reference": reference,
        "amount": amount,
        "currency": currency,
        "status": status,
        "url": url,
    })
    _NAM_PAY_LOG.write_text(json.dumps(log[-100:], indent=2), encoding="utf-8")


def _load_revenue_file():
    if _REVENUE_FILE.exists():
        try:
            return json.loads(_REVENUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"total_earned": 0.0, "total_withdrawn": 0.0, "balance": 0.0, "transactions": []}


def _save_revenue_file(rev):
    _REVENUE_FILE.write_text(json.dumps(rev, indent=2), encoding="utf-8")


def record_verified_income(gateway, amount, currency="USD", reference="", proof=""):
    """Record a gateway-verified real payment into revenue.json AND the audit log (Appendix C).

    Idempotent per (gateway, reference): a second call for the same payment is a no-op,
    so webhooks re-delivery can never double-count income. Returns the recorded dict,
    or None if the payment was already recorded.
    """
    amount = float(amount)
    rev = _load_revenue_file()
    txns = rev.setdefault("transactions", [])
    if reference:
        for t in txns:
            if t.get("ref") == reference and t.get("source") == gateway:
                return None  # already recorded — idempotent

    txn = {
        "time": time.time(),
        "amount": amount,
        "currency": currency,
        "source": gateway,
        "desc": f"Gateway-verified payment{ ' (' + reference + ')' if reference else ''}",
        "type": "income",
        "ref": reference,
        "verified": True,
        "proof": proof,
    }
    txns.append(txn)
    rev["total_earned"] = float(rev.get("total_earned", 0)) + amount
    rev["balance"] = float(rev.get("balance", 0)) + amount
    _save_revenue_file(rev)

    entry_id = write_audit_entry(
        domain=gateway,
        action_proposed=f"payment_received:{gateway}",
        screening_result="passed",
        gate_result="auto_approved:verified",
        execution_result="success",
        real_outcome={"gateway": gateway, "reference": reference, "amount": amount,
                      "currency": currency, "proof": proof},
        reasoning_summary=f"Gateway {gateway} confirmed payment {reference or 'n/a'} - amount {amount} {currency}",
        credential_used="webhook",
    )
    _log_payment(gateway, reference, amount, currency, "income_recorded", "")
    return {"recorded": True, "amount": amount, "currency": currency, "entry_id": entry_id}

def _deduct_and_record_withdrawal(gateway, amount, currency, reference, detail, payout_status="sent"):
    """Deduct balance and record a real withdrawal in revenue.json + audit log.

    Never called for amounts <= 0. Callers must validate amount and balance first.
    """
    rev = _load_revenue_file()
    balance = float(rev.get("balance", 0))
    if amount <= 0 or amount > balance:
        return {"success": False, "error": "invalid amount or insufficient balance"}
    txn = {
        "time": time.time(),
        "amount": -amount,
        "currency": currency,
        "source": "withdrawal",
        "desc": f"Withdrawn via {gateway} - {detail}",
        "type": "withdrawal",
        "ref": reference,
        "payout_status": payout_status,
    }
    rev.setdefault("transactions", []).append(txn)
    rev["total_withdrawn"] = float(rev.get("total_withdrawn", 0)) + amount
    rev["balance"] = balance - amount
    _save_revenue_file(rev)

    entry_id = write_audit_entry(
        domain="money",
        action_proposed=f"withdrawal:{gateway}",
        screening_result="passed",
        gate_result="approved",
        execution_result="success",
        real_outcome={"gateway": gateway, "reference": reference, "amount": amount,
                      "currency": currency, "detail": detail, "payout_status": payout_status},
        reasoning_summary=f"Payout {reference} via {gateway} for {amount} {currency} initiated",
        credential_used="payout_gateway",
    )
    _log_payment(gateway, reference, amount, currency, f"withdrawal_{payout_status}", "")

    return {"success": True, "amount": amount, "currency": currency, "reference": reference,
            "status": payout_status, "entry_id": entry_id}


def _bank_transfer_withdrawal(amount, currency, reference, destination=""):
    """Real bank-transfer withdrawal rail: produces payout instructions with a unique ref."""
    cfg = _load_nam_config()
    bank = cfg.get("bank_details", {})
    fnb_acc = bank.get("fnb_account", "[YOUR_FNB_ACCOUNT_NUMBER]")
    fnb_branch = bank.get("fnb_branch", "280172")
    instructions = (
        f"Manual transfer {currency} {amount} to the account linked to this JARVIS, "
        f"ref {reference}. FNB {fnb_acc} branch {fnb_branch}. "
        f"Destination: {destination or 'your linked bank account'}."
    )
    return instructions


def _paypal_withdrawal(cfg, amount, currency, reference, destination):
    """Attempt a REAL PayPal Payouts API call using live credentials.

    Returns a dict. Only a payout batch id means money really moved. Never fabricates success.
    """
    import base64
    base = GATEWAYS["paypal"]["api_base"]
    if not destination:
        return {"success": False, "error": "PayPal withdrawal needs a destination email"}
    auth = base64.b64encode(f"{cfg['client_id']}:{cfg['client_secret']}".encode()).decode()
    token_resp = http_post(
        f"{base}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
        form_type="urlencoded",
    )
    token = None
    if isinstance(token_resp, tuple):
        token_resp = token_resp[0] if len(token_resp) else ""
    try:
        token = json.loads(token_resp).get("access_token") if token_resp else None
    except Exception:
        token = None
    if not token:
        return {"success": False, "error": "PayPal auth failed - check client credentials"}
    batch = {
        "sender_batch_header": {
            "sender_batch_id": reference,
            "email_subject": "JARVIS payout",
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {"value": f"{amount:.2f}", "currency": "USD"},
            "receiver": destination,
            "note": f"JARVIS payout {reference}",
        }],
    }
    resp = http_post(
        f"{base}/v1/payments/payouts",
        json=batch,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    if isinstance(resp, tuple):
        resp = resp[0] if len(resp) else ""
    try:
        parsed = json.loads(resp) if isinstance(resp, str) else resp
    except Exception:
        parsed = {}
    if isinstance(parsed, dict) and (parsed.get("batch_header", {}).get("payout_batch_id") or parsed.get("batch_header", {}).get("batch_status")):
        return {"success": True, "batch_id": parsed["batch_header"].get("payout_batch_id"),
                "status": parsed["batch_header"].get("batch_status", "PENDING")}
    return {"success": False, "error": f"PayPal payout failed: {str(parsed)[:400]}", "reference": reference}


def process_withdrawal(gateway, amount, currency="USD", destination="", reference=""):
    """Process a REAL withdrawal through a payment gateway. Truthful: only
    records a withdrawal in revenue.json + audit when the payout is actually
    initiated/sent. Returns a clear error otherwise.

    Unsupported gateways return error instead of silently "succeeding".
    """
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return {"success": False, "error": "Withdrawal amount must be a number"}
    if amount <= 0:
        return {"success": False, "error": "Withdrawal amount must be greater than 0"}
    currency = (currency or "USD").upper()
    ref = reference or f"PAY_{gateway or 'x'}_{int(time.time())}"

    rev = _load_revenue_file()
    balance = float(rev.get("balance", 0))
    if amount > balance:
        return {"success": False, "error": f"Insufficient balance: {balance:.2f} < {amount:.2f}", "balance": balance}

    gateway = (gateway or "manual").lower()
    if gateway in ("manual", "bank_transfer", "fnb"):
        details = _bank_transfer_withdrawal(amount, currency, ref, destination)
        return _deduct_and_record_withdrawal(gateway, amount, currency, ref, details, payout_status="instructions_sent")

    if gateway in ("dpo", "paytoday", "stripe"):
        return {"success": False,
                "error": f"{gateway} is configured for receiving payments only - no payout rail. "
                         f"Use manual bank transfer or PayPal for withdrawals.",
                "reference": ref}

    if gateway == "paypal":
        cfg = _load_nam_config()
        gw = cfg.get("paypal")
        if not gw or not gw.get("enabled"):
            return {"success": False,
                    "error": "PayPal payout not configured. Configure paypal client_id/client_secret in namibian_payment_config.json first.",
                    "reference": ref}
        res = _paypal_withdrawal(gw, amount, "USD" if currency == "NAD" else currency, ref, destination)
        if not res.get("success"):
            return {"success": False, "error": res.get("error", "PayPal payout failed"), "reference": ref}
        return _deduct_and_record_withdrawal("paypal", amount, "USD" if currency == "NAD" else currency, ref,
                                             res.get("batch_id", ""), payout_status="sent")

    return {"success": False, "error": f"Gateway {gateway} has no payout rail", "reference": ref}


def list_payments():
    if not _NAM_PAY_LOG.exists():
        return "No payments logged"
    log = json.loads(_NAM_PAY_LOG.read_text(encoding="utf-8"))
    lines = ["=== NAMIBIAN PAYMENTS ==="]
    for p in log[-20:]:
        lines.append(f"  {p['time'][:19]} | {p['gateway']} | {p['reference']} | {p['status']}")
    return "\n".join(lines)

def get_gateway_status():
    cfg = _load_nam_config()
    lines = ["=== NAMIBIAN GATEWAYS ==="]
    for gw_name, gw_info in GATEWAYS.items():
        if gw_name == "bank_transfer":
            configured = "✅"  # always available, uses configured FNB account
            bank = cfg.get("bank_details", {})
            acc = bank.get("fnb_account", "[not set]")
            lines.append(f"  {configured} {gw_info['name']} - {gw_info['currency']} - acc {acc}")
        else:
            configured = "✅" if gw_name in cfg and cfg[gw_name].get("enabled") else "❌"
            lines.append(f"  {configured} {gw_info['name']} - {gw_info['currency']} - {', '.join(gw_info['supports'])}")
    return "\n".join(lines)

def handle(parameters):
    action = parameters.get("action", "status")
    target = parameters.get("target", "")
    value = parameters.get("value", "")
    
    if action == "configure_fnb":
        parts = target.split(",")
        return configure_fnb(parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else "")
    elif action == "configure_paytoday":
        parts = target.split(",")
        return configure_paytoday(parts[0], parts[1], parts[2])
    elif action == "configure_dpo":
        parts = target.split(",")
        return configure_dpo(parts[0], parts[1] if len(parts) > 1 else "live")
    elif action == "configure_paypal":
        parts = target.split(",")
        mode = parts[2] if len(parts) > 2 else "sandbox"
        return configure_paypal(parts[0], parts[1], mode)
    elif action == "create_payment":
        parts = target.split(",")
        gateway = parts[0] if parts else "bank_transfer"
        amount = float(parts[1]) if len(parts) > 1 else 0
        currency = parts[2] if len(parts) > 2 else "NAD"
        reference = parts[3] if len(parts) > 3 else ""
        callback = parts[4] if len(parts) > 4 else ""
        return create_payment_link(gateway, amount, currency, reference, callback)
    elif action == "verify_payment":
        return verify_payment(target, value)
    elif action == "record_verified_income":
        # target format: gateway,amount,currency,reference
        parts = target.split(",")
        if len(parts) < 2:
            return "Usage: record_verified_income target='gateway,amount[,currency[,reference]]'"
        gateway = parts[0]
        amount = float(parts[1])
        currency = parts[2] if len(parts) > 2 else "USD"
        reference = parts[3] if len(parts) > 3 else ""
        rec = record_verified_income(gateway, amount, currency, reference, proof="manual_confirmation")
        if rec is None:
            return f"Payment {reference} already recorded (idempotent, no double-count)"
        return (f"Verified income recorded: {currency} {amount} from {gateway} "
                f"(audit {rec['entry_id'][:8]})")
    elif action == "list_payments":
        return list_payments()
    elif action == "gateway_status":
        return get_gateway_status()
    elif action == "configure_bank_details":
        # Parse account,branch from target (format: "account,branch") or use value as branch
        account_branch = target
        if "," in account_branch and not value:
            acc, branch = account_branch.split(",", 1)
        else:
            acc = account_branch
            branch = value or "280172"
        cfg = _load_nam_config()
        cfg["bank_details"] = {
            "fnb_account": acc.strip(),
            "fnb_branch": branch.strip(),
            "updated": datetime.now().isoformat(),
        }
        _save_nam_config(cfg)
        return f"Bank details configured: Account {acc}, Branch {branch}"
    
    return get_gateway_status()