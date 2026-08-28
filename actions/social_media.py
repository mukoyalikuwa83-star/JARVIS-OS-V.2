"""Social Media Posting — real Twitter/Reddit posts, not just logs."""
import json
import os
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_LOG = _DATA_DIR / "social_log.json"


def _log_post(platform, content, status="posted"):
    log = []
    if _LOG.exists():
        try:
            log = json.loads(_LOG.read_text(encoding="utf-8"))
        except Exception:
            log = []
    log.append({"platform": platform, "content": content[:200], "status": status, "time": datetime.now().isoformat()})
    _LOG.write_text(json.dumps(log[-100:], indent=2), encoding="utf-8")


def _load_config():
    p = _DATA_DIR / "config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _save_config(cfg):
    p = _DATA_DIR / "config.json"
    p.write_text(json.dumps(cfg, indent=2, default=str), encoding="utf-8")


def post_to_twitter(content, api_key=None, api_secret=None, access_token=None, access_secret=None):
    cfg = _load_config()
    ak = api_key or cfg.get("twitter_api_key", "")
    as_ = api_secret or cfg.get("twitter_api_secret", "")
    at = access_token or cfg.get("twitter_access_token", "")
    ats = access_secret or cfg.get("twitter_access_secret", "")
    if not all([ak, as_, at, ats]):
        return ("No Twitter API credentials. Configure:\n"
                "  twitter_api_key, twitter_api_secret, twitter_access_token, twitter_access_secret\n"
                "  in .jarvis/config.json")
    try:
        import tweepy
        auth = tweepy.OAuth1UserHandler(ak, as_, at, ats)
        api = tweepy.API(auth)
        tweet = api.update_status(content[:280])
        _log_post("twitter", content, "posted")
        return f"Posted to Twitter: {tweet.id}\n{content[:100]}"
    except Exception as e:
        _log_post("twitter", content, f"error: {e}")
        return f"Twitter post failed: {e}"


def post_to_reddit(content, subreddit="python", client_id=None, client_secret=None, username=None, password=None):
    cfg = _load_config()
    cid = client_id or cfg.get("reddit_client_id", "")
    cs = client_secret or cfg.get("reddit_client_secret", "")
    un = username or cfg.get("reddit_username", "")
    pw = password or cfg.get("reddit_password", "")
    if not all([cid, cs, un, pw]):
        return ("No Reddit API credentials. Configure:\n"
                "  reddit_client_id, reddit_client_secret, reddit_username, reddit_password\n"
                "  in .jarvis/config.json")
    if not requests:
        return "requests library not installed"
    try:
        auth = requests.auth.HTTPBasicAuth(cid, cs)
        data = {"grant_type": "password", "username": un, "password": pw}
        headers = {"User-Agent": "JARVIS-OS/2.0"}
        r = requests.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers, timeout=10)
        token = r.json().get("access_token")
        if not token:
            return f"Reddit auth failed: {r.json()}"
        headers["Authorization"] = f"Bearer {token}"
        payload = {"sr": subreddit, "kind": "self", "title": content[:100], "text": content}
        r = requests.post("https://oauth.reddit.com/api/submit", headers=headers, data=payload, timeout=15)
        result = r.json()
        _log_post("reddit", content, "posted" if result.get("success") else f"error: {result}")
        return f"Posted to r/{subreddit}: {result.get('jquery', [['', '']])[0][0] if result.get('success') else result}"
    except Exception as e:
        _log_post("reddit", content, f"error: {e}")
        return f"Reddit post failed: {e}"


def share_store(products_count=0, total_value=0, store_url=""):
    if not store_url:
        store_url = "https://mukoyalikuwa83-star.github.io/JARVIS-OS-V.2/"
    tweet = f"Check out {products_count} production-quality Python tools available now! Total value: ${total_value}. Instant download. {store_url}"
    reddit_post = f"I built {products_count} production-ready Python tools — APIs, bots, scrapers, dashboards. Available for instant download at {store_url}"
    return {"tweet": tweet, "reddit": reddit_post, "store_url": store_url}


def get_status():
    log = []
    if _LOG.exists():
        try:
            log = json.loads(_LOG.read_text(encoding="utf-8"))
        except Exception:
            log = []
    cfg = _load_config()
    twitter_ok = bool(cfg.get("twitter_api_key"))
    reddit_ok = bool(cfg.get("reddit_client_id"))
    return (f"=== SOCIAL MEDIA ===\n"
            f"Twitter API: {'configured' if twitter_ok else 'NOT configured'}\n"
            f"Reddit API: {'configured' if reddit_ok else 'NOT configured'}\n"
            f"Posts logged: {len(log)}")


def handle(parameters=None):
    params = parameters or {}
    action = params.get("action", "status")
    target = params.get("target", "")
    value = params.get("value", "")
    if action == "status":
        return get_status()
    elif action == "twitter":
        return post_to_twitter(target or value or "Testing JARVIS social media integration")
    elif action == "reddit":
        return post_to_reddit(target or value or "Testing JARVIS social media integration")
    elif action == "share":
        cfg = _load_config()
        return share_store(cfg.get("products_count", 0), cfg.get("total_value", 0))
    elif action == "log":
        log = []
        if _LOG.exists():
            try:
                log = json.loads(_LOG.read_text(encoding="utf-8"))
            except Exception:
                log = []
        return "\n".join(f"  {l['platform']}: {l['content'][:60]} ({l['status']})" for l in log[-10:]) or "No posts logged"
    return f"Unknown action: {action}. Available: status, twitter, reddit, share, log"
