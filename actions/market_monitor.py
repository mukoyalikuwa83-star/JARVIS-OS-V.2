"""Market monitoring: stocks, crypto, financial data via web scraping."""

import json
import ssl
import time
from datetime import datetime
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_WATCHLIST_FILE = _BASE_DIR / ".jarvis" / "market_watchlist.json"

CRYPTO_SYMBOLS = {
    "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
    "dogecoin": "DOGE", "cardano": "ADA", "ripple": "XRP",
    "polkadot": "DOT", "litecoin": "LTC",
}


def _load_watchlist():
    try:
        return json.loads(_WATCHLIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"stocks": ["AAPL", "MSFT", "GOOGL"], "crypto": ["bitcoin", "ethereum"], "check_interval_min": 30}


def _save_watchlist(wl):
    _WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WATCHLIST_FILE.write_text(json.dumps(wl, indent=2, ensure_ascii=False), encoding="utf-8")


def get_prices(params=None):
    import urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    wl = _load_watchlist()
    results = {"stocks": {}, "crypto": {}, "timestamp": datetime.now().isoformat()}
    for symbol in wl.get("stocks", []):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            data = json.loads(resp.read())
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev = meta.get("chartPreviousClose", meta.get("previousClose", price))
            change_pct = round(((price - prev) / prev) * 100, 2) if prev else 0
            results["stocks"][symbol] = {
                "price": round(price, 2), "change_pct": change_pct,
                "currency": meta.get("currency", "USD"),
            }
        except Exception as e:
            results["stocks"][symbol] = {"error": str(e)[:100]}
    for coin in wl.get("crypto", []):
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd&include_24hr_change=true"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            data = json.loads(resp.read())
            if coin in data:
                sym = CRYPTO_SYMBOLS.get(coin, coin.upper())
                results["crypto"][sym] = {
                    "price_usd": data[coin].get("usd", 0),
                    "change_24h_pct": round(data[coin].get("usd_24h_change", 0), 2),
                }
        except Exception as e:
            results["crypto"][coin] = {"error": str(e)[:100]}
    return json.dumps(results)


def add_to_watchlist(params=None):
    wl = _load_watchlist()
    item = (params or {}).get("symbol", "").upper()
    category = (params or {}).get("category", "stocks").lower()
    if category == "crypto":
        item = (params or {}).get("symbol", "").lower()
        if item not in wl.get("crypto", []):
            wl.setdefault("crypto", []).append(item)
    else:
        if item and item not in wl.get("stocks", []):
            wl.setdefault("stocks", []).append(item)
    _save_watchlist(wl)
    return json.dumps({"result": f"Added {item} to {category} watchlist", "watchlist": wl})


def remove_from_watchlist(params=None):
    wl = _load_watchlist()
    item = (params or {}).get("symbol", "").upper()
    category = (params or {}).get("category", "stocks").lower()
    key = "crypto" if category == "crypto" else "stocks"
    items = wl.get(key, [])
    if item.lower() in [i.lower() for i in items]:
        items = [i for i in items if i.lower() != item.lower()]
        wl[key] = items
        _save_watchlist(wl)
        return json.dumps({"result": f"Removed {item} from {category} watchlist"})
    return json.dumps({"error": f"{item} not found in {category} watchlist"})


def get_watchlist(params=None):
    return json.dumps(_load_watchlist())


ACTIONS = {
    "get_prices": get_prices,
    "add": add_to_watchlist,
    "remove": remove_from_watchlist,
    "watchlist": get_watchlist,
}


def handle(parameters=None, **_kwargs):
    action = str((parameters or {}).get("action", "get_prices")).lower()
    fn = ACTIONS.get(action)
    if fn:
        return fn(parameters)
    return json.dumps({"error": f"Unknown action: {action}. Valid: {', '.join(ACTIONS)}"})
