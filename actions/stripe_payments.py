"""
Stripe Payment Module for JARVIS.
Uses curl-based HTTP for reliability (Python HTTP stack times out in this environment).
Process payments, create products, manage subscriptions, handle webhooks.
"""
import os
import json
from pathlib import Path
from actions._api import http_get, http_post, _load_env

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_load_env()

STRIPE_API = "https://api.stripe.com/v1"


def _get_keys():
    """Load Stripe keys from env or accounts.json."""
    _load_env()
    pk = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    sk = os.environ.get("STRIPE_SECRET_KEY", "")
    if not pk or not sk:
        accounts = _DATA_DIR / "accounts.json"
        if accounts.exists():
            acc = json.loads(accounts.read_text(encoding="utf-8"))
            stripe_acc = acc.get("stripe", {})
            pk = pk or stripe_acc.get("publishable_key", "")
            sk = sk or stripe_acc.get("secret_key", "")
    return pk, sk


def _auth_headers():
    _, sk = _get_keys()
    return {"Authorization": f"Bearer {sk}"}


def handle(params=None):
    params = params or {}
    action = params.get("action", "status")

    if action == "create_payment_link":
        return _create_payment_link(params)
    elif action == "create_product":
        return _create_product(params)
    elif action == "list_products":
        return _list_products(params)
    elif action == "create_price":
        return _create_price(params)
    elif action == "create_checkout":
        return _create_checkout(params)
    elif action == "get_balance":
        return _get_balance()
    elif action == "list_transactions":
        return _list_transactions(params)
    elif action == "create_refund":
        return _create_refund(params)
    elif action == "create_customer":
        return _create_customer(params)
    elif action == "create_subscription":
        return _create_subscription(params)
    elif action == "verify_webhook":
        return _verify_webhook(params)
    elif action == "status":
        return _stripe_status()
    else:
        return "Stripe: create_payment_link|create_product|list_products|create_price|create_checkout|get_balance|list_transactions|create_refund|create_customer|create_subscription|verify_webhook|status"


def _stripe_status():
    pk, sk = _get_keys()
    if not pk or not sk:
        return "Stripe not configured. Provide STRIPE_PUBLISHABLE_KEY and STRIPE_SECRET_KEY in .env"
    out, rc = http_get(f"{STRIPE_API}/balance", headers=_auth_headers(), timeout=30)
    if rc != 0 or not out:
        return f"Stripe connection error: no response"
    try:
        data = json.loads(out)
        if "error" in data:
            return f"Stripe connection error: {data['error'].get('message', 'unknown')}"
        available = data.get("available", [])
        pending = data.get("pending", [])
        avail = sum(a.get("amount", 0) for a in available) / 100
        pend = sum(p.get("amount", 0) for p in pending) / 100
        return f"Stripe connected. Balance: ${avail:.2f} available, ${pend:.2f} pending"
    except json.JSONDecodeError:
        return f"Stripe connection error: bad response {out[:200]}"


def _create_payment_link(params):
    _, sk = _get_keys()
    headers = _auth_headers()
    price_id = params.get("price_id", "")
    product_name = params.get("product_name", "JARVIS Product")
    amount = params.get("amount", 0)
    currency = params.get("currency", "usd")

    if not price_id and amount:
        # Create product with name
        data = {"name": product_name}
        out, rc = http_post(f"{STRIPE_API}/products", data, None, headers, timeout=30, form_type="urlencoded")
        if rc != 0 or not out:
            return "Stripe payment link error: no response"
        try:
            product_data = json.loads(out)
            if "error" in product_data:
                return f"Stripe error: {product_data['error'].get('message', 'unknown')}"
            product_id = product_data.get("id", "")
        except json.JSONDecodeError:
            return "Stripe payment link error: bad response"
        # Create price
        data = {"product": product_id, "unit_amount": str(int(amount * 100)), "currency": currency}
        out, rc = http_post(f"{STRIPE_API}/prices", data, None, headers, timeout=30, form_type="urlencoded")
        if rc == 0 and out:
            try:
                price_data = json.loads(out)
                if "error" not in price_data:
                    price_id = price_data.get("id", "")
            except json.JSONDecodeError:
                pass

    if not price_id:
        return "Stripe payment link error: need price_id or amount"

    data = {"line_items[0][price]": price_id, "line_items[0][quantity]": "1", "metadata[source]": "jarvis"}
    out, rc = http_post(f"{STRIPE_API}/payment_links", data, None, headers, timeout=30, form_type="urlencoded")
    if rc != 0 or not out:
        return "Stripe payment link error: no response"
    try:
        link_data = json.loads(out)
        if "error" in link_data:
            return f"Stripe error: {link_data['error'].get('message', 'unknown')}"
        return f"Payment link created: {link_data.get('url', 'N/A')}"
    except json.JSONDecodeError:
        return f"Stripe payment link error: bad response {out[:200]}"


def _create_product(params):
    headers = _auth_headers()
    name = params.get("name", "JARVIS Product")
    desc = params.get("description", "")
    data = {"name": name, "description": desc, "metadata[source]": "jarvis"}
    out, rc = http_post(f"{STRIPE_API}/products", data, None, headers, timeout=30, form_type="urlencoded")
    if rc != 0 or not out:
        return "Stripe product error: no response"
    try:
        product_data = json.loads(out)
        if "error" in product_data:
            return f"Stripe product error: {product_data['error'].get('message', 'unknown')}"
        return f"Product created: {product_data.get('id')} ({product_data.get('name')})"
    except json.JSONDecodeError:
        return f"Stripe product error: bad response {out[:200]}"


def _list_products(params):
    headers = _auth_headers()
    limit = params.get("limit", 10)
    out, rc = http_get(f"{STRIPE_API}/products?limit={limit}", headers=headers, timeout=30)
    if rc != 0 or not out:
        return "Stripe list error: no response"
    try:
        data = json.loads(out)
        if "error" in data:
            return f"Stripe list error: {data['error'].get('message', 'unknown')}"
        products = data.get("data", [])
        if not products:
            return "No Stripe products"
        lines = []
        for p in products:
            lines.append(f"{p.get('id')} | {p.get('name')} | {p.get('description', '')[:50]}")
        return "\n".join(lines)
    except json.JSONDecodeError:
        return f"Stripe list error: bad response {out[:200]}"


def _create_price(params):
    headers = _auth_headers()
    product_id = params.get("product_id", "")
    amount = params.get("amount", 0)
    currency = params.get("currency", "usd")
    data = {"product": product_id, "unit_amount": str(int(amount * 100)), "currency": currency}
    out, rc = http_post(f"{STRIPE_API}/prices", data, None, headers, timeout=30, form_type="urlencoded")
    if rc != 0 or not out:
        return "Stripe price error: no response"
    try:
        price_data = json.loads(out)
        if "error" in price_data:
            return f"Stripe price error: {price_data['error'].get('message', 'unknown')}"
        return f"Price created: {price_data.get('id')} (${amount} {currency})"
    except json.JSONDecodeError:
        return f"Stripe price error: bad response {out[:200]}"


def _create_checkout(params):
    headers = _auth_headers()
    price_id = params.get("price_id", "")
    success_url = params.get("success_url", "https://example.com/success")
    cancel_url = params.get("cancel_url", "https://example.com/cancel")
    data = {
        "mode": params.get("mode", "payment"),
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    out, rc = http_post(f"{STRIPE_API}/checkout/sessions", data, None, headers, timeout=30, form_type="urlencoded")
    if rc != 0 or not out:
        return "Stripe checkout error: no response"
    try:
        session_data = json.loads(out)
        if "error" in session_data:
            return f"Stripe checkout error: {session_data['error'].get('message', 'unknown')}"
        return f"Checkout session: {session_data.get('url', 'N/A')}"
    except json.JSONDecodeError:
        return f"Stripe checkout error: bad response {out[:200]}"


def _get_balance():
    headers = _auth_headers()
    out, rc = http_get(f"{STRIPE_API}/balance", headers=headers, timeout=30)
    if rc != 0 or not out:
        return "Stripe balance error: no response"
    try:
        data = json.loads(out)
        if "error" in data:
            return f"Stripe balance error: {data['error'].get('message', 'unknown')}"
        available = data.get("available", [])
        pending = data.get("pending", [])
        avail = sum(a.get("amount", 0) for a in available) / 100
        pend = sum(p.get("amount", 0) for p in pending) / 100
        return f"Balance: ${avail:.2f} available, ${pend:.2f} pending"
    except json.JSONDecodeError:
        return f"Stripe balance error: bad response {out[:200]}"


def _list_transactions(params):
    headers = _auth_headers()
    limit = params.get("limit", 10)
    out, rc = http_get(f"{STRIPE_API}/charges?limit={limit}", headers=headers, timeout=30)
    if rc != 0 or not out:
        return "Stripe transactions error: no response"
    try:
        data = json.loads(out)
        if "error" in data:
            return f"Stripe transactions error: {data['error'].get('message', 'unknown')}"
        charges = data.get("data", [])
        if not charges:
            return "No transactions"
        lines = []
        for c in charges:
            amt = c.get("amount", 0) / 100
            lines.append(f"{c.get('id')[:12]}... | ${amt:.2f} | {c.get('status')}")
        return "\n".join(lines)
    except json.JSONDecodeError:
        return f"Stripe transactions error: bad response {out[:200]}"


def _create_refund(params):
    headers = _auth_headers()
    charge_id = params.get("charge_id", "")
    data = {"charge": charge_id}
    out, rc = http_post(f"{STRIPE_API}/refunds", data, None, headers, timeout=30, form_type="urlencoded")
    if rc != 0 or not out:
        return "Stripe refund error: no response"
    try:
        refund_data = json.loads(out)
        if "error" in refund_data:
            return f"Stripe refund error: {refund_data['error'].get('message', 'unknown')}"
        return f"Refund created: {refund_data.get('id')} ({refund_data.get('status')})"
    except json.JSONDecodeError:
        return f"Stripe refund error: bad response {out[:200]}"


def _create_customer(params):
    headers = _auth_headers()
    data = {"email": params.get("email", ""), "name": params.get("name", "")}
    out, rc = http_post(f"{STRIPE_API}/customers", data, None, headers, timeout=30, form_type="urlencoded")
    if rc != 0 or not out:
        return "Stripe customer error: no response"
    try:
        customer_data = json.loads(out)
        if "error" in customer_data:
            return f"Stripe customer error: {customer_data['error'].get('message', 'unknown')}"
        return f"Customer created: {customer_data.get('id')} ({customer_data.get('email')})"
    except json.JSONDecodeError:
        return f"Stripe customer error: bad response {out[:200]}"


def _create_subscription(params):
    headers = _auth_headers()
    customer_id = params.get("customer_id", "")
    price_id = params.get("price_id", "")
    data = {"customer": customer_id, "items[0][price]": price_id}
    out, rc = http_post(f"{STRIPE_API}/subscriptions", data, None, headers, timeout=30, form_type="urlencoded")
    if rc != 0 or not out:
        return "Stripe subscription error: no response"
    try:
        sub_data = json.loads(out)
        if "error" in sub_data:
            return f"Stripe subscription error: {sub_data['error'].get('message', 'unknown')}"
        return f"Subscription created: {sub_data.get('id')} ({sub_data.get('status')})"
    except json.JSONDecodeError:
        return f"Stripe subscription error: bad response {out[:200]}"


def _verify_webhook(params):
    payload = params.get("payload", "")
    sig_header = params.get("sig_header", "")
    webhook_secret = params.get("webhook_secret", os.environ.get("STRIPE_WEBHOOK_SECRET", ""))
    if not webhook_secret:
        return "No webhook secret configured"
    # For webhook verification we'd need the stripe library or manual HMAC verification
    # This is a placeholder - actual verification requires the stripe.webhook module
    return "Webhook verification requires the stripe library. Install with: pip install stripe"
