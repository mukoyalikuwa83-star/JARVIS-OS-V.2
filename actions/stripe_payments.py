"""
Stripe Payment Module for JARVIS.
Process payments, create products, manage subscriptions, handle webhooks.
Requires: stripe package (installed)
"""
import os
import json
import time
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

def _get_keys():
    """Load Stripe keys from env or accounts.json."""
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
    return f"Stripe configured: pk={pk[:12]}..., sk={'set' if sk else 'missing'}"

def _create_payment_link(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        price_id = params.get("price_id", "")
        product_name = params.get("product_name", "JARVIS Product")
        amount = params.get("amount", 0)
        currency = params.get("currency", "usd")
        
        if not price_id and amount:
            product = stripe.Product.create(name=product_name)
            price = stripe.Price.create(
                product=product.id,
                amount=int(amount * 100),
                currency=currency,
            )
            price_id = price.id
        
        link = stripe.PaymentLink.create(
            line_items=[{"price": price_id, "quantity": 1}],
            metadata={"source": "jarvis", "product": product_name},
        )
        return f"Payment link created: {link.url}"
    except ImportError:
        return "stripe package not installed. Run: pip install stripe"
    except Exception as e:
        return f"Stripe payment link error: {e}"

def _create_product(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        name = params.get("name", "JARVIS Product")
        desc = params.get("description", "")
        product = stripe.Product.create(
            name=name,
            description=desc,
            metadata={"source": "jarvis"},
        )
        return f"Product created: {product.id} ({product.name})"
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe product error: {e}"

def _list_products(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        limit = params.get("limit", 10)
        products = stripe.Product.list(limit=limit)
        if not products.data:
            return "No Stripe products"
        lines = []
        for p in products.data:
            lines.append(f"{p.id} | {p.name} | {p.get('description', '')[:50]}")
        return "\n".join(lines)
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe list error: {e}"

def _create_price(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        product_id = params.get("product_id", "")
        amount = params.get("amount", 0)
        currency = params.get("currency", "usd")
        recurring = params.get("recurring", False)
        
        price_params = {
            "product": product_id,
            "unit_amount": int(amount * 100),
            "currency": currency,
        }
        if recurring:
            price_params["recurring"] = {"interval": params.get("interval", "month")}
        
        price = stripe.Price.create(**price_params)
        return f"Price created: {price.id} (${amount} {currency})"
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe price error: {e}"

def _create_checkout(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        price_id = params.get("price_id", "")
        success_url = params.get("success_url", "https://example.com/success")
        cancel_url = params.get("cancel_url", "https://example.com/cancel")
        
        session = stripe.checkout.Session.create(
            mode=params.get("mode", "payment"),
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"source": "jarvis"},
        )
        return f"Checkout session: {session.url}"
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe checkout error: {e}"

def _get_balance():
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        balance = stripe.Balance.retrieve()
        available = balance.available[0] if balance.available else None
        pending = balance.pending[0] if balance.pending else None
        avail_amt = available.amount / 100 if available else 0
        pend_amt = pending.amount / 100 if pending else 0
        return f"Balance: ${avail_amt:.2f} available, ${pend_amt:.2f} pending"
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe balance error: {e}"

def _list_transactions(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        limit = params.get("limit", 10)
        charges = stripe.Charge.list(limit=limit)
        if not charges.data:
            return "No transactions"
        lines = []
        for c in charges.data:
            amt = c.amount / 100
            lines.append(f"{c.id[:12]}... | ${amt:.2f} | {c.status} | {c.created}")
        return "\n".join(lines)
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe transactions error: {e}"

def _create_refund(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        charge_id = params.get("charge_id", "")
        amount = params.get("amount")
        
        refund_params = {"charge": charge_id}
        if amount:
            refund_params["amount"] = int(amount * 100)
        
        refund = stripe.Refund.create(**refund_params)
        return f"Refund created: {refund.id} ({refund.status})"
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe refund error: {e}"

def _create_customer(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        
        customer = stripe.Customer.create(
            email=params.get("email", ""),
            name=params.get("name", ""),
            metadata={"source": "jarvis"},
        )
        return f"Customer created: {customer.id} ({customer.email})"
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe customer error: {e}"

def _create_subscription(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        
        subscription = stripe.Subscription.create(
            customer=params.get("customer_id", ""),
            items=[{"price": params.get("price_id", "")}],
            metadata={"source": "jarvis"},
        )
        return f"Subscription created: {subscription.id} ({subscription.status})"
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Stripe subscription error: {e}"

def _verify_webhook(params):
    try:
        import stripe
        _, sk = _get_keys()
        stripe.api_key = sk
        payload = params.get("payload", "")
        sig_header = params.get("sig_header", "")
        webhook_secret = params.get("webhook_secret", os.environ.get("STRIPE_WEBHOOK_SECRET", ""))
        
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        return f"Webhook verified: {event['type']}"
    except ImportError:
        return "stripe package not installed"
    except Exception as e:
        return f"Webhook verification failed: {e}"
