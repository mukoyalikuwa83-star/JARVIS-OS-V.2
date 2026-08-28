"""Gumroad API Integration — real payment processing and product delivery."""
import json
import requests
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

GUMROAD_API = "https://api.gumroad.com/v2"


def _load_config():
    p = _DATA_DIR / "config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _save_config(cfg):
    p = _DATA_DIR / "config.json"
    p.write_text(json.dumps(cfg, indent=2, default=str), encoding="utf-8")


def _get_token():
    cfg = _load_config()
    return cfg.get("gumroad_access_token", "")


def set_token(token):
    cfg = _load_config()
    cfg["gumroad_access_token"] = token
    _save_config(cfg)
    return f"Gumroad access token set. Length: {len(token)}"


def list_products():
    token = _get_token()
    if not token:
        return "No Gumroad access token. Run: gumroad_token <your_token>"
    try:
        r = requests.get(f"{GUMROAD_API}/products", params={"access_token": token}, timeout=15)
        data = r.json()
        if not data.get("success"):
            return f"Gumroad API error: {data.get('message', 'unknown')}"
        products = data.get("products", [])
        if not products:
            return "No products on Gumroad yet. Use 'gumroad_publish' to create one."
        lines = [f"=== GUMROAD PRODUCTS ({len(products)}) ==="]
        for p in products:
            sales = p.get("sales_count", 0)
            revenue = p.get("total_revenue_cents", 0) / 100
            lines.append(f"  {p.get('id', 'N/A')[:12]}: {p.get('name', 'N/A')[:50]} — ${p.get('price', 0)/100:.0f} ({sales} sales, ${revenue:.2f} revenue)")
        return "\n".join(lines)
    except Exception as e:
        return f"Gumroad API error: {e}"


def publish_product(title, description, price_cents, file_path=None):
    token = _get_token()
    if not token:
        return "No Gumroad access token. Run: gumroad_token <your_token>"
    try:
        payload = {
            "access_token": token,
            "name": title,
            "description": description,
            "price": price_cents,
            "currency": "usd",
            "content": description[:500],
            "url": "",
        }
        files = {}
        if file_path and Path(file_path).exists():
            files["file"] = (Path(file_path).name, open(file_path, "rb"), "application/zip")
            r = requests.post(f"{GUMROAD_API}/products", data=payload, files=files, timeout=30)
        else:
            r = requests.post(f"{GUMROAD_API}/products", data=payload, timeout=30)
        data = r.json()
        if not data.get("success"):
            return f"Gumroad publish error: {data.get('message', 'unknown')}"
        product = data.get("product", {})
        return (f"Published to Gumroad!\n"
                f"  ID: {product.get('id')}\n"
                f"  Name: {product.get('name')}\n"
                f"  Price: ${product.get('price', 0)/100:.2f}\n"
                f"  URL: {product.get('short_url', 'N/A')}\n"
                f"  Dashboard: https://app.gumroad.com/products/{product.get('id')}")
    except Exception as e:
        return f"Gumroad publish error: {e}"


def check_sales():
    token = _get_token()
    if not token:
        return "No Gumroad access token."
    try:
        r = requests.get(f"{GUMROAD_API}/sales", params={"access_token": token}, timeout=15)
        data = r.json()
        if not data.get("success"):
            return f"Gumroad API error: {data.get('message', 'unknown')}"
        sales = data.get("sales", [])
        if not sales:
            return "No sales yet on Gumroad."
        total = sum(s.get("sale_amount_cents", 0) for s in sales) / 100
        lines = [f"=== GUMROAD SALES ({len(sales)} total, ${total:.2f} revenue) ==="]
        for s in sales[:10]:
            product_name = s.get("product_name", "N/A")
            amount = s.get("sale_amount_cents", 0) / 100
            buyer = s.get("email", "unknown")
            created = s.get("created_at", "N/A")
            lines.append(f"  ${amount:.2f} — {product_name[:40]} — {buyer[:30]} — {created}")
        return "\n".join(lines)
    except Exception as e:
        return f"Gumroad sales error: {e}"


def update_product(product_id, **kwargs):
    token = _get_token()
    if not token:
        return "No Gumroad access token."
    try:
        payload = {"access_token": token}
        for k, v in kwargs.items():
            payload[k] = v
        r = requests.put(f"{GUMROAD_API}/products/{product_id}", data=payload, timeout=15)
        data = r.json()
        if not data.get("success"):
            return f"Gumroad update error: {data.get('message', 'unknown')}"
        return f"Updated product {product_id}: {kwargs}"
    except Exception as e:
        return f"Gumroad update error: {e}"


def handle(parameters=None):
    params = parameters or {}
    action = params.get("action", "status")
    target = params.get("target", "")
    value = params.get("value", "")
    if action == "token" or action == "set_token":
        return set_token(target or value)
    elif action == "products" or action == "list":
        return list_products()
    elif action == "publish" or action == "create":
        price = int(value) if value and value.isdigit() else 4900
        return publish_product(target or "Untitled Product", "Production-quality code", price)
    elif action == "sales":
        return check_sales()
    elif action == "status":
        token = _get_token()
        if not token:
            return "Gumroad: No token configured. Run: gumroad_token <your_token>"
        try:
            r = requests.get(f"{GUMROAD_API}/user", params={"access_token": token}, timeout=10)
            data = r.json()
            if data.get("success"):
                user = data.get("user", {})
                return f"Gumroad connected: {user.get('name', 'N/A')} ({user.get('email', 'N/A')})"
            return f"Gumroad token invalid: {data.get('message', 'unknown')}"
        except Exception as e:
            return f"Gumroad connection error: {e}"
    return f"Unknown gumroad_api action: {action}. Available: token, products, publish, sales, status"
