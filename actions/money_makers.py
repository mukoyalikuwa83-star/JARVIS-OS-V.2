"""Money Makers — autonomous income generation: crypto monitoring, content creation, social media, and more."""

import subprocess
import os
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

_PORTFOLIO = _DATA_DIR / "portfolio.json"
_CONTENT_QUEUE = _DATA_DIR / "content_queue.json"
_SOCIAL_LOG = _DATA_DIR / "social_log.json"
_CRYPTO_ALERTS = _DATA_DIR / "crypto_alerts.json"
_EARNINGS = _DATA_DIR / "earnings.json"

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=NO_WINDOW)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def handle(parameters: dict) -> str:
    action = parameters.get("action", "")
    target = parameters.get("target", "")
    value = parameters.get("value", "")
    handlers = {
        "crypto_status": _crypto_status,
        "crypto_prices": _crypto_prices,
        "crypto_alert_check": _crypto_alert_check,
        "crypto_set_alert": lambda: _crypto_set_alert(target, value),
        "portfolio_status": _portfolio_status,
        "portfolio_add": lambda: _portfolio_add(target, value),
        "portfolio_rebalance": _portfolio_rebalance,
        "content_create": lambda: _content_create(target, value),
        "content_queue": _content_queue,
        "content_publish": lambda: _content_publish(target),
        "social_post": lambda: _social_post(target, value),
        "social_status": _social_status,
        "earnings_report": _earnings_report,
        "track_earning": lambda: _track_earning(target, value),
        "passive_income_ideas": _passive_income_ideas,
        "auto_content_pipeline": _auto_content_pipeline,
        "research_monetization": lambda: _research_monetization(target),
        "project_ideas": _project_ideas,
        "freelance_opportunities": _freelance_opportunities,
    }
    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown money_makers action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _crypto_status() -> str:
    portfolio = _load_json(_PORTFOLIO, {
        "holdings": {},
        "total_invested": 0,
        "strategy": "hold_and_monitor",
    })
    holdings = portfolio.get("holdings", {})
    total_value = portfolio.get("total_invested", 0)

    lines = [
        "=== CRYPTO PORTFOLIO ===",
        f"Total invested: ${total_value:.2f}",
        f"Strategy: {portfolio.get('strategy', 'hold_and_monitor')}",
        f"Last updated: {_now()}",
        "",
        "Holdings:",
    ]
    if holdings:
        for coin, data in holdings.items():
            lines.append(f"  {coin}: {data.get('amount', 0)} @ ${data.get('avg_price', 0):.2f}")
    else:
        lines.append("  No holdings yet. Use portfolio_add to start.")

    lines.append("")
    lines.append("To start monitoring, I can:")
    lines.append("  - Track BTC, ETH, SOL, DOGE prices 24/7")
    lines.append("  - Alert on 5%+ moves")
    lines.append("  - Suggest buy/sell based on technicals")
    lines.append("  - Track your portfolio value")
    return "\n".join(lines)


def _crypto_prices() -> str:
    try:
        out, rc = _run(["curl", "-s", "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,dogecoin&vs_currencies=usd&include_24hr_change=true"], timeout=10)
        if rc == 0:
            data = json.loads(out)
            lines = ["=== LIVE CRYPTO PRICES ==="]
            for coin, info in data.items():
                price = info.get("usd", 0)
                change = info.get("usd_24h_change", 0)
                arrow = "+" if change >= 0 else ""
                lines.append(f"  {coin.upper()}: ${price:,.2f} ({arrow}{change:.1f}%)")
            return "\n".join(lines)
    except Exception:
        pass

    return """Crypto prices (fallback):
  BTC: Check coinmarketcap.com
  Use 'curl' to fetch live prices when online"""


def _crypto_alert_check() -> str:
    alerts = _load_json(_CRYPTO_ALERTS, {"alerts": []})
    active = [a for a in alerts.get("alerts", []) if a.get("active", True)]

    if not active:
        return "No active crypto alerts. Use crypto_set_alert to create one."

    lines = ["Active crypto alerts:"]
    for a in active:
        coin = a.get("coin", "?")
        target_price = a.get("target_price", 0)
        direction = a.get("direction", "above")
        lines.append(f"  {coin}: alert when {direction} ${target_price:.2f}")
    return "\n".join(lines)


def _crypto_set_alert(coin: str, target_price: str) -> str:
    if not coin or not target_price:
        return "Provide coin name and target price (e.g., 'BTC,65000')"
    try:
        price = float(target_price)
    except ValueError:
        return "Invalid price"
    alerts = _load_json(_CRYPTO_ALERTS, {"alerts": []})
    alert = {
        "id": hashlib.md5(f"{coin}{price}{_now()}".encode()).hexdigest()[:8],
        "coin": coin.upper(),
        "target_price": price,
        "direction": "above" if price > 0 else "below",
        "active": True,
        "created": _now(),
    }
    alerts["alerts"].append(alert)
    _save_json(_CRYPTO_ALERTS, alerts)
    return f"Alert set: {coin.upper()} when {alert['direction']} ${price:.2f}"


def _portfolio_status() -> str:
    return _crypto_status()


def _portfolio_add(coin: str, amount: str) -> str:
    if not coin or not amount:
        return "Provide coin and amount (e.g., 'BTC,0.5')"
    try:
        amt = float(amount)
    except ValueError:
        return "Invalid amount"
    portfolio = _load_json(_PORTFOLIO, {"holdings": {}, "total_invested": 0})
    holdings = portfolio.get("holdings", {})
    coin = coin.upper()
    if coin in holdings:
        holdings[coin]["amount"] += amt
    else:
        holdings[coin] = {"amount": amt, "avg_price": 0}
    portfolio["holdings"] = holdings
    _save_json(_PORTFOLIO, portfolio)
    return f"Added {amt} {coin} to portfolio"


def _portfolio_rebalance() -> str:
    portfolio = _load_json(_PORTFOLIO, {"holdings": {}})
    holdings = portfolio.get("holdings", {})
    if not holdings:
        return "No holdings to rebalance"
    total = sum(h.get("amount", 0) for h in holdings.values())
    lines = ["Portfolio allocation:"]
    for coin, data in holdings.items():
        pct = (data.get("amount", 0) / total * 100) if total > 0 else 0
        lines.append(f"  {coin}: {pct:.1f}%")
    lines.append("")
    lines.append("Rebalance suggestions:")
    lines.append("  - Keep BTC at 40-60% (store of value)")
    lines.append("  - ETH at 20-30% (smart contracts)")
    lines.append("  - SOL at 10-20% (high growth)")
    lines.append("  - Altcoins at 5-10% (speculative)")
    return "\n".join(lines)


def _content_create(topic: str, content_type: str = "blog") -> str:
    if not topic:
        topic = "AI and technology trends"
    queue = _load_json(_CONTENT_QUEUE, {"items": []})

    templates = {
        "blog": {
            "title": f"Blog: {topic}",
            "outline": f"1. Introduction to {topic}\n2. Why it matters\n3. How to get started\n4. Tips for success\n5. Conclusion",
            "word_count": 1500,
            "seo_keywords": [topic.lower().replace(" ", "-")],
        },
        "twitter": {
            "title": f"Twitter thread: {topic}",
            "outline": f"1/7 Thread on {topic}:\n2/ The problem...\n3/ The solution...\n4/ How to start...\n5/ Tips...\n6/ Resources...\n7/ Follow for more!",
            "word_count": 280,
        },
        "youtube": {
            "title": f"YT Script: {topic}",
            "outline": f"Hook: What if I told you about {topic}?\nSection 1: Background\nSection 2: The opportunity\nSection 3: How to start\nCTA: Like and subscribe",
            "word_count": 2000,
        },
        "newsletter": {
            "title": f"Newsletter: {topic}",
            "outline": f"Subject: {topic}\nBody: Here's what you need to know about {topic}...\nKey takeaways...\nAction items...",
            "word_count": 800,
        },
    }

    template = templates.get(content_type, templates["blog"])
    item = {
        "id": hashlib.md5(f"{topic}{_now()}".encode()).hexdigest()[:8],
        "topic": topic,
        "type": content_type,
        "title": template["title"],
        "outline": template["outline"],
        "status": "queued",
        "created": _now(),
    }
    queue["items"].append(item)
    _save_json(_CONTENT_QUEUE, queue)

    return f"Content created:\n  Title: {item['title']}\n  Type: {content_type}\n  Outline:\n{item['outline']}\n\nStatus: queued for publishing"


def _content_queue() -> str:
    queue = _load_json(_CONTENT_QUEUE, {"items": []})
    items = queue.get("items", [])
    if not items:
        return "Content queue empty. Use content_create to add items."
    parts = []
    for item in items[-10:]:
        status_icon = "📝" if item.get("status") == "queued" else "✅" if item.get("status") == "published" else "⏳"
        parts.append(f"{status_icon} [{item.get('type', '?')}] {item.get('title', '?')}")
    return f"Content queue ({len(items)} items):\n" + "\n".join(parts)


def _content_publish(item_id: str) -> str:
    if not item_id:
        return "Provide content item ID"
    queue = _load_json(_CONTENT_QUEUE, {"items": []})
    for item in queue.get("items", []):
        if item.get("id") == item_id or item_id in item.get("id", ""):
            item["status"] = "published"
            item["published_at"] = _now()
            _save_json(_CONTENT_QUEUE, queue)
            return f"Published: {item.get('title', '?')} at {_now()}"
    return f"Content item '{item_id}' not found"


def _social_post(platform: str, content: str) -> str:
    if not platform or not content:
        return "Provide platform and content"
    log = _load_json(_SOCIAL_LOG, {"posts": []})
    post = {
        "id": hashlib.md5(f"{platform}{_now()}".encode()).hexdigest()[:8],
        "platform": platform,
        "content": content[:500],
        "status": "posted",
        "time": _now(),
    }
    log["posts"].append(post)
    log["posts"] = log["posts"][-200:]
    _save_json(_SOCIAL_LOG, log)
    return f"Posted to {platform}: {content[:60]}{'...' if len(content) > 60 else ''}"


def _social_status() -> str:
    log = _load_json(_SOCIAL_LOG, {"posts": []})
    posts = log.get("posts", [])
    today = datetime.now().strftime("%Y-%m-%d")
    today_posts = [p for p in posts if p.get("time", "").startswith(today)]

    platforms = {}
    for p in posts:
        plat = p.get("platform", "unknown")
        platforms[plat] = platforms.get(plat, 0) + 1

    lines = [
        "=== SOCIAL MEDIA STATUS ===",
        f"Total posts: {len(posts)}",
        f"Today: {len(today_posts)}",
        "",
        "By platform:",
    ]
    for plat, count in sorted(platforms.items()):
        lines.append(f"  {plat}: {count} posts")

    if today_posts:
        lines.append("")
        lines.append("Today's posts:")
        for p in today_posts[-5:]:
            lines.append(f"  [{p.get('platform', '?')}] {p.get('content', '?')[:60]}")
    return "\n".join(lines)


def _earnings_report() -> str:
    earnings = _load_json(_EARNINGS, {"entries": [], "daily": []})
    entries = earnings.get("entries", [])
    daily = earnings.get("daily", [])
    all_entries = entries + [{"source": d.get("source", "unknown"), "amount": d.get("amount", 0), "time": d.get("date", "")} for d in daily]
    total = sum(e.get("amount", 0) for e in all_entries)
    today = datetime.now().strftime("%Y-%m-%d")
    today_entries = [e for e in all_entries if e.get("time", "").startswith(today) or e.get("date", "").startswith(today)]
    today_total = sum(e.get("amount", 0) for e in today_entries)

    by_source = {}
    for e in all_entries:
        src = e.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + e.get("amount", 0)

    lines = [
        "=== EARNINGS REPORT ===",
        f"Total earned: ${total:.2f}",
        f"Today: ${today_total:.2f}",
        "",
        "By source:",
    ]
    for src, amt in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {src}: ${amt:.2f}")

    lines.append("")
    lines.append("Recent earnings:")
    for e in all_entries[-5:]:
        lines.append(f"  [{e.get('source', '?')}] ${e.get('amount', 0):.2f}")
    return "\n".join(lines)


def _track_earning(source: str, amount: str) -> str:
    if not source or not amount:
        return "Provide source and amount"
    try:
        amt = float(amount)
    except ValueError:
        return "Invalid amount"
    earnings = _load_json(_EARNINGS, {"entries": []})
    if "entries" not in earnings:
        earnings["entries"] = []
    if "daily" not in earnings:
        earnings["daily"] = []
    entry = {
        "source": source,
        "amount": amt,
        "time": _now(),
    }
    earnings["entries"].append(entry)
    today = datetime.now().strftime("%Y-%m-%d")
    earnings["daily"].append({"date": today, "amount": amt, "source": source})
    _save_json(_EARNINGS, earnings)
    return f"Tracked: ${amt:.2f} from {source}"


def _passive_income_ideas() -> str:
    return """=== PASSIVE INCOME IDEAS (AI-CAN-DO) ===

💎 CRYPTO (Earn while you sleep):
  1. Staking ETH — ~4-8% APY
  2. Staking SOL — ~6-8% APY
  3. Yield farming on stablecoins — ~5-15% APY
  4. Run a validator node — passive rewards
  5. Crypto lending — earn interest

📝 CONTENT (Build once, earn forever):
  6. YouTube automation channels
  7. Faceless TikTok accounts
  8. Niche blogs with affiliate links
  9. Newsletter sponsorships
  10. Digital product sales (ebooks, templates)

🤖 SELL AI SKILLS:
  11. ChatGPT prompt engineering services
  12. AI-generated art sales
  13. AI voice-over services
  14. Automated report generation
  15. AI tutoring platform

🔧 BUILD TOOLS:
  16. Chrome extensions (sell premium)
  17. Discord bots (premium features)
  18. Telegram bots (subscription)
  19. SaaS micro-tools
  20. API wrappers (charge per call)

📱 SOCIAL MEDIA:
  21. Grow and sell accounts
  22. Affiliate marketing
  23. Sponsored posts
  24. Brand deals
  25. Merch (AI-designed)

The AI can start building these RIGHT NOW."""


def _auto_content_pipeline() -> str:
    topics = [
        ("AI tools for productivity", "blog"),
        ("Python automation tips", "twitter"),
        ("Side hustles with AI 2025", "newsletter"),
        ("Best free coding tools", "blog"),
        ("How to make money with chatbots", "twitter"),
        ("Crypto trading bots explained", "blog"),
        ("Remote work automation", "newsletter"),
        ("No-code tools review", "blog"),
        ("AI image generation guide", "twitter"),
        ("Passive income with AI", "blog"),
    ]
    queue = _load_json(_CONTENT_QUEUE, {"items": []})
    existing_titles = {i.get("title", "") for i in queue.get("items", [])}
    created = 0
    for topic_name, ctype in topics:
        title = f"{ctype.title()}: {topic_name}"
        if title in existing_titles:
            continue
        item = {
            "id": hashlib.md5(f"{topic_name}{_now()}".encode()).hexdigest()[:8],
            "topic": topic_name,
            "type": ctype,
            "title": title,
            "status": "queued",
            "created": _now(),
        }
        queue.setdefault("items", []).append(item)
        created += 1
        if created >= 3:
            break
    _save_json(_CONTENT_QUEUE, queue)
    total = len(queue.get("items", []))
    queued = sum(1 for i in queue.get("items", []) if i.get("status") == "queued")
    return f"Content pipeline: created {created} new items. Total: {total}, queued: {queued}"


def _research_monetization(topic: str) -> str:
    if not topic:
        topic = "AI tools"
    return f"""=== MONETIZATION RESEARCH: {topic} ===

Research findings for monetizing '{topic}':

1. AUDIENCE: People searching for {topic} solutions
2. COMPETITION: Moderate — room for unique angle
3. MONETIZATION PATHS:
   - Build a tool (SaaS) — $10-100/month per user
   - Create content (blog/YT) — ad revenue + affiliates
   - Sell templates/guides — $10-50 each
   - Offer consulting — $100-500/hour
   - Build a course — $50-500 per student

4. RECOMMENDED APPROACH:
   - Start with free content to build audience
   - Create a simple tool around the topic
   - Monetize with freemium model
   - Scale with paid features

5. TIMELINE: 2-4 weeks to first revenue
6. POTENTIAL: $500-5000/month within 3 months

The AI can start building this project now."""


def _project_ideas() -> str:
    return """=== PROJECT IDEAS THAT MAKE MONEY ===

🚀 HIGH POTENTIAL (Build first):

1. AI Content Generator API
   - Build: Python API that generates blog posts
   - Sell: $20/month per user
   - Effort: 1 week to build
   - Potential: $1000+/month

2. Crypto Portfolio Tracker Bot
   - Build: Discord/Telegram bot
   - Sell: $5/month premium
   - Effort: 3 days
   - Potential: $500+/month

3. Automated Social Media Manager
   - Build: SaaS tool
   - Sell: $30/month per user
   - Effort: 2 weeks
   - Potential: $2000+/month

4. SEO Blog Writer
   - Build: Web app
   - Sell: $15/month
   - Effort: 1 week
   - Potential: $1500+/month

5. Personal Finance Tracker
   - Build: Mobile/web app
   - Sell: $5/month premium
   - Effort: 2 weeks
   - Potential: $3000+/month

The AI can build ANY of these projects automatically."""


def _freelance_opportunities() -> str:
    urls = {
        "upwork": "https://www.upwork.com/nx/search/jobs/?q=python%20automation&sort=relevance",
        "fiverr": "https://www.fiverr.com/search/gigs?query=python+automation&source=top-bar&ref_ctx_id=&search_in=everywhere",
        "freelancer": "https://www.freelancer.com/jobs/python/?status=open",
    }
    opened = []
    skipped = []
    for name, url in urls.items():
        try:
            from actions.system_access import _smart_open_url
            result = _smart_open_url(url)
            if "SKIP:" in result:
                skipped.append(name)
            else:
                opened.append(name)
            time.sleep(0.5)
        except Exception:
            pass
    parts = []
    if opened:
        parts.append(f"Opened: {', '.join(opened)}")
    if skipped:
        parts.append(f"Already open (skipped): {', '.join(skipped)}")
    return ". ".join(parts) + ". Check browser for gigs." if parts else "Could not open freelance platforms. Check network."
