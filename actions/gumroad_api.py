"""Gumroad API Integration — real payment processing and product delivery.
Uses curl-based HTTP for reliability (requests/urllib time out in this environment).
"""
import json
from pathlib import Path
from actions._api import http_get, http_post, http_put, _load_env

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_load_env()

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
    token = cfg.get("gumroad_access_token", "")
    if not token:
        import os
        _load_env()
        token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
    if not token:
        accounts = _DATA_DIR / "accounts.json"
        if accounts.exists():
            acc = json.loads(accounts.read_text(encoding="utf-8"))
            token = acc.get("gumroad", {}).get("access_token", "")
    return token


def set_token(token):
    cfg = _load_config()
    cfg["gumroad_access_token"] = token
    _save_config(cfg)
    return f"Gumroad access token set. Length: {len(token)}"


def list_products():
    token = _get_token()
    if not token:
        return "No Gumroad access token. Run: gumroad_token <your_token>"
    out, rc = http_get(f"{GUMROAD_API}/products", {"access_token": token}, timeout=30)
    if rc != 0 or not out:
        return f"Gumroad API error: no response"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return f"Gumroad API error: bad response {out[:200]}"
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


def _upload_file(file_path):
    """Upload a file to Gumroad via presigned multipart flow. Returns file_url or error string."""
    import os
    import subprocess as _sp
    from pathlib import Path as _P
    file_path = _P(file_path)
    if not file_path.exists():
        return None, f"File not found: {file_path}"
    token = _get_token()
    if not token:
        return None, "No Gumroad access token"
    fname = file_path.name
    fsize = file_path.stat().st_size
    CURL = r"C:\Windows\System32\curl.exe"
    if not os.path.exists(CURL):
        CURL = "curl"

    # 1. Presign
    try:
        proc = _sp.run(
            [CURL, "-s", "-m", "30", "-X", "POST",
             "-d", f"access_token={token}", "-d", f"filename={fname}",
             "-d", f"file_size={fsize}",
             f"{GUMROAD_API}/files/presign"],
            capture_output=True, text=True, timeout=35)
        if proc.returncode != 0 or not proc.stdout.strip():
            return None, f"Presign failed: {proc.stdout[:200]}"
        presign = json.loads(proc.stdout)
    except Exception as e:
        return None, f"Presign error: {e}"
    if not presign.get("success"):
        return None, f"Presign error: {presign.get('message', 'unknown')}"

    upload_id = presign.get("upload_id", "")
    key = presign.get("key", "")
    parts = presign.get("parts", [])
    if not parts:
        return None, "No presigned parts returned"

    # 2. Upload each part (for files < 100MB there's usually just 1 part)
    etags = []
    for part in parts:
        part_num = part.get("part_number")
        presigned_url = part.get("presigned_url")
        try:
            proc = _sp.run(
                [CURL, "-s", "-m", "300", "-D", "-", "-o", "NUL",
                 "-X", "PUT", "-H", "Content-Type: application/zip",
                 "--data-binary", f"@{file_path}", presigned_url],
                capture_output=True, text=True, timeout=310)
            etag = None
            for line in proc.stdout.splitlines():
                if line.lower().startswith("etag:"):
                    etag = line.split(":", 1)[1].strip()
                    break
            if not etag:
                return None, f"Part {part_num} upload: no ETag returned (rc={proc.returncode}, out={proc.stdout[:100]})"
            etags.append({"part_number": part_num, "etag": etag})
        except Exception as e:
            return None, f"Part {part_num} upload error: {e}"

    # 3. Complete
    try:
        cmd = [CURL, "-s", "-m", "30", "-X", "POST",
               "-d", f"access_token={token}",
               "-d", f"upload_id={upload_id}",
               "-d", f"key={key}"]
        for e in etags:
            cmd.extend(["-d", f"parts[][part_number]={e['part_number']}"])
            cmd.extend(["-d", f"parts[][etag]={e['etag']}"])
        cmd.append(f"{GUMROAD_API}/files/complete")
        proc = _sp.run(cmd, capture_output=True, text=True, timeout=35)
        if proc.returncode != 0 or not proc.stdout.strip():
            return None, f"Complete failed: {proc.stdout[:200]}"
        complete = json.loads(proc.stdout)
    except Exception as e:
        return None, f"Complete error: {e}"
    if not complete.get("success"):
        return None, f"Complete error: {complete.get('message', 'unknown')}"
    return complete.get("file_url", ""), None


def publish_product(title, description, price_cents, file_path=None):
    token = _get_token()
    if not token:
        return "No Gumroad access token. Run: gumroad_token <your_token>"
    payload = {
        "access_token": token,
        "name": title,
        "description": description,
        "price": str(price_cents),
        "currency": "usd",
        "content": description[:500],
    }
    file_url = None
    if file_path and Path(file_path).exists():
        file_url, err = _upload_file(file_path)
        if err:
            return f"Gumroad file upload error: {err}"
        if file_url:
            payload["files[][url]"] = file_url
            payload["native_type"] = "digital"
    out, rc = http_post(f"{GUMROAD_API}/products", data=payload, timeout=60)
    if rc != 0 or not out:
        return f"Gumroad publish error: no response"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return f"Gumroad publish error: bad response {out[:200]}"
    if not data.get("success"):
        return f"Gumroad publish error: {data.get('message', 'unknown')}"
    product = data.get("product", {})
    return (f"Published to Gumroad!\n"
            f"  ID: {product.get('id')}\n"
            f"  Name: {product.get('name')}\n"
            f"  Price: ${product.get('price', 0)/100:.2f}\n"
            f"  URL: {product.get('short_url', 'N/A')}\n"
            f"  File: {'attached' if file_url else 'none'}\n"
            f"  Dashboard: https://app.gumroad.com/products/{product.get('id')}")


def check_sales():
    token = _get_token()
    if not token:
        return "No Gumroad access token."
    out, rc = http_get(f"{GUMROAD_API}/sales", {"access_token": token}, timeout=30)
    if rc != 0 or not out:
        return f"Gumroad sales error: no response"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return f"Gumroad sales error: bad response {out[:200]}"
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


def record_gumroad_sales():
    """Pull REAL Gumroad sales and record each as verified income (idempotent by sale id).

    Skips: refunded sales, free downloads, test purchases.
    Returns a summary dict {checked, recorded, skipped_refunded, total_recorded}.
    """
    from actions.namibian_payments import record_verified_income
    token = _get_token()
    if not token:
        return {"error": "No Gumroad access token", "checked": 0}
    out, rc = http_get(f"{GUMROAD_API}/sales", {"access_token": token}, timeout=30)
    if rc != 0 or not out:
        return {"error": "no response", "checked": 0}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"error": "bad response", "checked": 0}
    if not data.get("success"):
        return {"error": data.get("message", "api error"), "checked": 0}

    recorded = 0
    skipped_refunded = 0
    skipped_free = 0
    checked = 0
    for s in data.get("sales", []):
        checked += 1
        if s.get("refunded"):
            skipped_refunded += 1
            continue
        amount_cents = s.get("sale_amount_cents") or 0
        if amount_cents <= 0:
            skipped_free += 1
            continue
        rec = record_verified_income(
            "gumroad",
            amount_cents / 100,
            "USD",
            reference=str(s.get("id", "")),
            proof=f"gumroad_sale {s.get('id')} {s.get('product_name', '')}".strip(),
        )
        if rec:
            recorded += 1

    return {
        "checked": checked,
        "recorded": recorded,
        "skipped_refunded": skipped_refunded,
        "skipped_free": skipped_free,
        "total_recorded": recorded,
    }


def update_product(product_id, **kwargs):
    token = _get_token()
    if not token:
        return "No Gumroad access token."
    payload = {"access_token": token}
    for k, v in kwargs.items():
        payload[k] = v
    out, rc = http_put(f"{GUMROAD_API}/products/{product_id}", data=payload, timeout=30)
    if rc != 0 or not out:
        return "Gumroad update error: no response"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return f"Gumroad update error: bad response {out[:200]}"
    if not data.get("success"):
        return f"Gumroad update error: {data.get('message', 'unknown')}"
    return f"Updated product {product_id}: {kwargs}"


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
        out, rc = http_get(f"{GUMROAD_API}/user", {"access_token": token}, timeout=30)
        if rc != 0 or not out:
            return "Gumroad connection error: no response"
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return f"Gumroad connection error: bad response {out[:200]}"
        if data.get("success"):
            user = data.get("user", {})
            return f"Gumroad connected: {user.get('name', 'N/A')} ({user.get('email', 'N/A')})"
        return f"Gumroad token invalid: {data.get('message', 'unknown')}"
    return f"Unknown gumroad_api action: {action}. Available: token, products, publish, sales, status"
