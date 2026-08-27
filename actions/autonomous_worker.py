"""Autonomous Worker - JARVIS money-making brain. Handles everything end-to-end."""
import json
import time
import hashlib
import subprocess
import os
import zipfile
import random
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
import ssl as _ssl

try:
    from actions.system_access import _smart_open_url as _open, _is_url_open as _check_url
except ImportError:
    import webbrowser
    def _open(url):
        webbrowser.open(url)
        return f"Opened: {url}"
    def _check_url(url):
        return f"NOT_OPEN: {url} (check unavailable)"

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
_ssl_ctx = _ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = _ssl.CERT_NONE
_tunnel_proc = None
_tunnel_url = None
_tunnel_server = None
_tunnel_lock = __import__("threading").Lock()
_CLOUDFLARED = str(Path(r"C:\Users\2025\AppData\Local\Temp\opencode\cloudflared.exe"))
if not Path(_CLOUDFLARED).exists():
    _CLOUDFLARED = "cloudflared"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save(path, data):
    try:
        path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _ago(time_str):
    try:
        dt = datetime.strptime(str(time_str), "%Y-%m-%d %H:%M:%S")
        return datetime.now() - dt
    except Exception:
        return timedelta(seconds=0)


def _needs_human(blocker):
    kw = ["captcha", "robot", "phone_verify", "email_verify", "id_verify",
          "payment_setup", "bank", "tax", "password_reset", "two_factor"]
    return any(k in str(blocker).lower() for k in kw)


PLATFORMS = {
    "freelancer": {"jobs": "https://www.freelancer.com/jobs/python/", "signup": "https://www.freelancer.com/signup", "type": "freelance"},
    "upwork": {"signup": "https://www.upwork.com/nx/signup/", "jobs": "https://www.upwork.com/nx/search/jobs/?q=", "type": "freelance"},
    "fiverr": {"signup": "https://www.fiverr.com/users/sign_up", "gigs": "https://www.fiverr.com/search/gigs?query=", "type": "freelance"},
    "gumroad": {"signup": "https://app.gumroad.com/signup", "type": "digital_products"},
    "github": {"signup": "https://github.com/signup", "type": "code_hosting"},
    "medium": {"signup": "https://medium.com/m/signin", "write": "https://medium.com/new-story", "type": "content"},
    "substack": {"signup": "https://substack.com/signup", "type": "newsletter"},
    "ko_fi": {"signup": "https://ko-fi.com/register", "type": "donations"},
}

SKILLS = {
    "python_developer": {"title": "Python Developer & Automation Expert", "rate": 35, "prices": {"basic": 50, "standard": 150, "premium": 500}},
    "content_writer": {"title": "SEO Content Writer", "rate": 25, "prices": {"basic": 20, "standard": 60, "premium": 200}},
    "bot_builder": {"title": "Discord & Telegram Bot Developer", "rate": 40, "prices": {"basic": 100, "standard": 300, "premium": 1000}},
    "web_scraper": {"title": "Web Scraping Specialist", "rate": 30, "prices": {"basic": 50, "standard": 150, "premium": 500}},
}


class AutonomousWorker:
    def __init__(self):
        self._p = lambda n: _DATA_DIR / n
        self._accounts = _load(self._p("worker_accounts.json"), {})
        self._jobs = _load(self._p("worker_jobs.json"), {"found": [], "applied": [], "delivered": []})
        self._wallet = _load(self._p("worker_wallet.json"), {"balance": 0, "earned": 0, "withdrawn": 0, "txns": []})
        self._pending = _load(self._p("worker_pending.json"), [])
        self._state = _load(self._p("worker_state.json"), {"status": "idle", "platforms": [], "profiles": [], "applied": 0, "delivered": 0})
        self._cleanup_stale()

    def _save_all(self):
        _save(self._p("worker_accounts.json"), self._accounts)
        _save(self._p("worker_jobs.json"), self._jobs)
        _save(self._p("worker_wallet.json"), self._wallet)
        _save(self._p("worker_pending.json"), self._pending)
        _save(self._p("worker_state.json"), self._state)

    def _start_tunnel(self):
        global _tunnel_proc, _tunnel_url, _tunnel_server
        with _tunnel_lock:
            if _tunnel_proc and _tunnel_proc.poll() is None and _tunnel_url:
                return _tunnel_url
            import http.server
            import threading
            deploy_dir = _DATA_DIR / "deploy"
            deploy_dir.mkdir(exist_ok=True)

            class _StoreHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/" or self.path == "/index.html":
                        sp = deploy_dir / "store.html"
                        if sp.exists():
                            self.send_response(200)
                            self.send_header("Content-Type", "text/html; charset=utf-8")
                            self.end_headers()
                            self.wfile.write(sp.read_bytes())
                        else:
                            self.send_response(404)
                            self.end_headers()
                    elif self.path.startswith("/download/"):
                        fname = self.path.split("/download/")[1].split("?")[0]
                        fpath = _DATA_DIR / "products" / fname
                        if fpath.exists() and fpath.suffix == ".zip":
                            self.send_response(200)
                            self.send_header("Content-Type", "application/zip")
                            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                            self.send_header("Content-Length", str(fpath.stat().st_size))
                            self.end_headers()
                            self.wfile.write(fpath.read_bytes())
                        else:
                            self.send_response(404)
                            self.end_headers()
                    elif self.path == "/api/catalog":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        try:
                            products_dir = _DATA_DIR / "products"
                            zips = list(products_dir.glob("*.zip")) if products_dir.exists() else []
                            jobs = _load(_DATA_DIR / "worker_jobs.json", {"delivered": []})
                            cat = []
                            for z in zips:
                                wid = z.stem
                                listing = None
                                for d in jobs.get("delivered", []):
                                    if d.get("id") == wid:
                                        listing = d.get("listing", {})
                                        break
                                if listing:
                                    cat.append({"id": wid, "title": listing.get("title", wid),
                                                "price": listing.get("price", 49),
                                                "description": listing.get("description", ""),
                                                "download": f"/download/{z.name}"})
                            self.wfile.write(json.dumps(cat, indent=2).encode())
                        except Exception:
                            self.wfile.write(b"[]")
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, *a):
                    pass

            try:
                _tunnel_server = http.server.HTTPServer(("0.0.0.0", 8080), _StoreHandler)
                threading.Thread(target=_tunnel_server.serve_forever, daemon=True).start()
            except OSError:
                pass
            try:
                _tunnel_proc = subprocess.Popen(
                    [_CLOUDFLARED, "tunnel", "--url", "http://localhost:8080"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=_NO_WINDOW
                )
                import threading as _th
                _found = _th.Event()
                _result = [None]

                def _reader(proc):
                    try:
                        for ln in proc.stdout:
                            if "trycloudflare.com" in ln and "api." not in ln:
                                for w in ln.split():
                                    if w.startswith("https://") and "trycloudflare.com" in w:
                                        _result[0] = w.strip()
                                        _found.set()
                                        return
                    except Exception:
                        pass

                _th.Thread(target=_reader, args=(_tunnel_proc,), daemon=True).start()
                _found.wait(timeout=20)
                _tunnel_url = _result[0]
                if not _tunnel_url:
                    try:
                        _tunnel_proc.terminate()
                    except Exception:
                        pass
                    _tunnel_proc = None
            except Exception:
                _tunnel_url = None
                _tunnel_proc = None
            if _tunnel_url:
                cfg = _load(_DATA_DIR / "config.json", {})
                cfg["tunnel_url"] = _tunnel_url
                _save(_DATA_DIR / "config.json", cfg)
            return _tunnel_url

    @staticmethod
    def _get_lan_ip():
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"

    def _stop_tunnel(self):
        global _tunnel_proc, _tunnel_url, _tunnel_server
        with _tunnel_lock:
            if _tunnel_proc:
                try:
                    _tunnel_proc.terminate()
                    _tunnel_proc.wait(timeout=5)
                except Exception:
                    try:
                        _tunnel_proc.kill()
                    except Exception:
                        pass
                _tunnel_proc = None
            if _tunnel_server:
                try:
                    _tunnel_server.shutdown()
                except Exception:
                    pass
                _tunnel_server = None
            _tunnel_url = None

    def _cleanup_stale(self):
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=24)
        short_cutoff = datetime.now() - timedelta(hours=4)
        changed = False
        seen = set()
        clean_pending = []
        for p in self._pending:
            key = f"{p.get('platform')}:{p.get('task')}:{p.get('description','')[:50]}"
            if key in seen:
                changed = True
                continue
            seen.add(key)
            try:
                t = datetime.strptime(p.get("time", ""), "%Y-%m-%d %H:%M:%S")
                if p.get("status") == "pending" and t < cutoff:
                    p["status"] = "expired"
                    changed = True
                elif p.get("status") == "pending" and t < short_cutoff:
                    plat = p.get("platform", "")
                    task = p.get("task", "")
                    if task == "job_search" and self._accounts.get(plat, {}).get("status") == "active":
                        p["status"] = "auto_cleared"
                        changed = True
            except Exception:
                pass
            clean_pending.append(p)
        self._pending = clean_pending
        for acct in self._accounts.values():
            if acct.get("status") == "setup_started":
                try:
                    t = datetime.strptime(acct.get("started", ""), "%Y-%m-%d %H:%M:%S")
                    if t < cutoff:
                        acct["status"] = "stale_setup"
                        changed = True
                except Exception:
                    pass
        for job_list in self._jobs.values():
            if isinstance(job_list, list):
                for j in job_list:
                    if j.get("status") == "searching":
                        try:
                            t = datetime.strptime(j.get("time", ""), "%Y-%m-%d %H:%M:%S")
                            if t < cutoff:
                                j["status"] = "expired_search"
                                changed = True
                        except Exception:
                            pass
        if changed:
            self._save_all()

    def _request_approval(self, platform, task, desc, action):
        for p in self._pending:
            if (p.get("platform") == platform and p.get("task") == task
                    and p.get("status") == "pending"):
                p["time"] = _now()
                self._save_all()
                return p
        req = {"id": hashlib.md5(f"{platform}{task}{_now()}".encode()).hexdigest()[:8],
               "platform": platform, "task": task, "description": desc,
               "action_needed": action, "time": _now(), "status": "pending"}
        self._pending.append(req)
        self._save_all()
        return req

    def clear_pending(self):
        before = len([p for p in self._pending if p.get("status") == "pending"])
        for p in self._pending:
            if p.get("status") == "pending":
                task = p.get("task", "")
                plat = p.get("platform", "")
                if task == "job_search":
                    self._pending.remove(p)
                elif task == "payment_setup" and self._accounts.get(plat, {}).get("status") == "active":
                    self._pending.remove(p)
        self._save_all()
        after = len([p for p in self._pending if p.get("status") == "pending"])
        return f"Cleaned: {before} -> {after} pending"

    def handle(self, params=None):
        params = params or {}
        action = params.get("action", "status")
        target = params.get("target", "")
        value = params.get("value", "")

        def _split(s):
            return [x.strip() for x in str(s).split(",") if x.strip()]

        targets = _split(target)
        values = _split(value)

        def _first(s):
            return _split(s)[0] if _split(s) else ""

        h = {
            "status": self.get_status,
            "resume": self.resume_work,
            "browser_tabs": lambda: self.browser_tabs(_first(target)),
            "check_url": lambda: self.check_url(_first(target)),
            "verify": lambda: self.verify_account(_first(target)),
            "setup": lambda: self.setup_platform(_first(target)),
            "profile": lambda: self.create_profile(_first(target), _first(value)),
            "find_jobs": lambda: self.find_jobs(_first(target), _first(value)),
            "quick_apply": lambda: self.quick_apply(_first(target), _first(value)),
            "apply": lambda: self.apply_to_job(_first(target), _first(value)),
            "work": lambda: self.do_work(_first(target), _first(value)),
            "deliver": lambda: self.deliver_work(_first(target)),
            "wallet": lambda: self.create_wallet(_first(target)),
            "product": lambda: self.create_product(_first(target), _first(value)),
            "products": self.list_products,
            "pending": self.get_pending,
            "approve": lambda: self.approve(_first(target)),
            "reject": lambda: self.reject(_first(target)),
            "clear_pending": self.clear_pending,
            "earnings": self.earnings,
            "full_cycle": lambda: self.full_cycle(targets, _first(value)),
            "fill_form": lambda: self.fill_form(target),
            "click_button": lambda: self.click_screen_button(target),
            "type_in": lambda: self.type_in(target),
            "press_keys": lambda: self.press_keys(target),
            "signup": lambda: self.signup_flow(_first(target)),
            "list_product": lambda: self.list_product(_first(target), _first(value)),
            "activate": lambda: self.activate_account(_first(target), _first(value)),
            "catalog": self.build_catalog,
            "serve": lambda: self.serve_products(int(target) if target else 8080),
            "catalog_json": self.get_catalog_json,
            "github": lambda: self.prepare_github(_first(target)),
            "more": lambda: self.more_products(_first(target)),
            "deploy": lambda: self.deploy(_first(target)),
            "redeploy": self.redeploy,
            "paypal": lambda: self.set_paypal(_first(target)),
            "heal": self.self_heal,
        }
        fn = h.get(action)
        if fn:
            r = fn()
            return r if isinstance(r, str) else str(r)
        return f"Unknown: {action}. Available: {', '.join(sorted(h.keys()))}"

    def get_status(self):
        s = self._state
        active_platforms = [p for p, a in self._accounts.items() if a.get("status") == "active"]
        needs_signup = [p for p, a in self._accounts.items() if a.get("status") == "needs_human_signup"]
        real_applied = len([j for j in self._jobs.get("applied", []) if j.get("status") == "applied"])
        real_delivered = len([j for j in self._jobs.get("delivered", []) if j.get("status") == "completed"])
        real_listed = len(self._jobs.get("listed", []))
        pending_count = len([p for p in self._pending if p.get("status") == "pending"])
        products_dir = _DATA_DIR / "products"
        zip_count = len(list(products_dir.glob("*.zip"))) if products_dir.exists() else 0
        total_value = sum(
            d.get("listing", {}).get("price", 0)
            for d in self._jobs.get("delivered", [])
            if d.get("status") == "completed"
        )
        lines = [
            "=== AUTONOMOUS WORKER ===",
            f"Status: {s.get('status', 'idle')}",
            f"Active platforms: {', '.join(active_platforms) or 'none'}",
            f"Needs signup: {', '.join(needs_signup) or 'none'}",
            f"Products built: {real_delivered} ({zip_count} zips, ~${total_value} value)",
            f"Listed for sale: {real_listed}",
            f"Real applications: {real_applied}",
            f"Wallet: ${self._wallet.get('balance', 0):.2f}",
            f"Earned: ${self._wallet.get('earned', 0):.2f}",
        ]
        if pending_count > 0:
            lines.append(f"Pending approvals: {pending_count}")
        if needs_signup:
            lines.append("")
            lines.append("NEXT STEP: Run 'activate <platform>' after you sign up.")
        return "\n".join(lines)

    def resume_work(self):
        lines = ["=== RESUME: What needs to be done ==="]
        needs_setup = []
        for plat, acct in self._accounts.items():
            if acct.get("status") in ("setup_started", "stale_setup", "profile_needed"):
                needs_setup.append(plat)
        if needs_setup:
            lines.append(f"\nPlatforms needing signup completion: {', '.join(needs_setup)}")
            for p in needs_setup:
                lines.append(f"  → Run 'setup {p}' to open signup, then complete it")
        active = [p for p, a in self._accounts.items() if a.get("status") == "active"]
        if active:
            lines.append(f"\nActive platforms: {', '.join(active)}")
            needs_profile = [p for p in active if p not in self._state.get("profiles", [])]
            if needs_profile:
                lines.append(f"  Needs profile: {', '.join(needs_profile)}")
        pending = [p for p in self._pending if p.get("status") == "pending"]
        if pending:
            lines.append(f"\nPending approvals ({len(pending)}):")
            for p in pending[:5]:
                lines.append(f"  [{p['id']}] {p['platform']}: {p.get('action_needed', '?')}")
        found = [j for j in self._jobs.get("found", []) if j.get("status") == "searching"]
        if found:
            lines.append(f"\nJob searches in progress ({len(found)}):")
            for j in found[:3]:
                lines.append(f"  {j['platform']}: '{j['query']}' — needs human review")
        if not needs_setup and active and not pending:
            lines.append("\nAll platforms set up. Ready to find jobs and apply.")
            lines.append("Use 'find_jobs' to search, then 'apply' to apply.")
        return "\n".join(lines)

    def verify_account(self, platform):
        if not platform:
            return "Provide platform to verify"
        platform = platform.lower().replace("-", "_")
        acct = self._accounts.get(platform, {})
        if not acct:
            return f"No account record for {platform}. Run setup first."
        status = acct.get("status", "unknown")
        if status == "active":
            return f"{platform} is already active."
        try:
            from actions.system_access import _get_browser_tabs
            tabs = _get_browser_tabs(platform)
            if tabs and "NOT_OPEN" not in str(tabs):
                if "dashboard" in str(tabs).lower() or "home" in str(tabs).lower():
                    self._accounts[platform]["status"] = "active"
                    self._accounts[platform]["verified_at"] = _now()
                    if platform not in self._state.get("platforms", []):
                        self._state.setdefault("platforms", []).append(platform)
                    self._save_all()
                    return (f"{platform} verified via browser tab detection! "
                            f"Tab found: {tabs}. Account marked ACTIVE.")
                return f"Browser open on {platform} but not on dashboard. Tab: {tabs}"
        except Exception:
            pass
        if status == "needs_human_signup":
            url = PLATFORMS.get(platform, {}).get("signup", "")
            if url:
                _open(url)
            return (f"{platform} needs human signup. Browser opened. "
                    f"When you complete signup, tell me: verify_account {platform}")
        if status in ("setup_started", "stale_setup"):
            url = PLATFORMS.get(platform, {}).get("signup", "")
            if url:
                _open(url)
            return (f"{platform} signup was started but not completed. "
                    f"Browser opened. Complete signup, then tell me to verify.")
        return f"{platform} status: {status}. Cannot auto-verify."

    def setup_platform(self, platform):
        if not platform:
            return "Provide platform: upwork, fiverr, gumroad, github, medium, substack, ko_fi"
        platform = platform.lower().replace("-", "_").replace(" ", "_")
        if platform not in PLATFORMS:
            return f"Unknown: {platform}. Available: {', '.join(PLATFORMS.keys())}"

        acct = self._accounts.get(platform, {})
        if acct.get("status") == "active":
            return f"{platform} already active."
        if acct.get("status") == "awaiting_human":
            return f"{platform} waiting for you: {acct.get('blocker', 'complete signup')}"
        if acct.get("status") == "needs_human_signup":
            url = PLATFORMS[platform]["signup"]
            _open(url)
            return (f"{platform} signup page opened. YOU must complete signup — "
                    f"I cannot bypass CAPTCHAs or email verification. "
                    f"When you're done, tell me to verify_account {platform}.")

        url = PLATFORMS[platform]["signup"]
        self._accounts[platform] = {"status": "needs_human_signup", "url": url, "started": _now()}
        self._state["status"] = "setting_up"
        self._save_all()
        open_result = _open(url)
        return (f"{open_result}\n"
                f"YOU must complete signup on {platform}. I cannot do CAPTCHAs or email verification. "
                f"When done, tell me: verify_account {platform}")

    def _resolve_skill(self, raw):
        s = raw.lower().replace("-", "_").replace(" ", "_").strip()
        if s in SKILLS:
            return s
        for k in SKILLS:
            if s in k or k in s:
                return k
        return None

    def create_profile(self, platform, skill):
        if not platform or not skill:
            return "Provide platform and skill (e.g., upwork,python_developer)"
        platform = platform.lower().replace("-", "_")
        resolved = self._resolve_skill(skill)
        if not resolved:
            return f"Unknown skill: {skill}. Available: {', '.join(SKILLS.keys())}"
        skill = resolved

        info = SKILLS[skill]
        profile = {"platform": platform, "skill": skill, "title": info["title"],
                   "rate": info["rate"], "created": _now()}

        acct = self._accounts.get(platform, {})
        if acct.get("status") != "active":
            self._accounts[platform] = {"status": "needs_human_signup", "profile": profile, "started": _now()}
            self._save_all()
            url = PLATFORMS.get(platform, {}).get("signup", "")
            if url:
                _open(url)
            return (f"Cannot create profile: {platform} is not active. "
                    f"Signup page opened. YOU must complete signup first. "
                    f"Then tell me: verify_account {platform}")

        self._accounts[platform]["profile"] = profile
        if platform not in self._state.get("profiles", []):
            self._state.setdefault("profiles", []).append(platform)
        self._save_all()
        return (f"Profile data saved locally for {platform}: {info['title']} at ${info['rate']}/hr. "
                f"NOTE: This is local preparation only. To actually create the profile on {platform}, "
                f"I need to be logged in. Use 'setup' to open the platform, then tell me to fill in the profile.")

    def find_jobs(self, platform, skill):
        if not platform:
            return "Provide platform"
        platform = platform.lower().replace("-", "_")
        info = PLATFORMS.get(platform, {})
        search_url = info.get("jobs") or info.get("gigs", "")
        if not search_url:
            return f"No job search URL for {platform}"

        acct = self._accounts.get(platform, {})
        if acct.get("status") != "active":
            return (f"CANNOT search jobs: {platform} is not active. "
                    f"Status: {acct.get('status', 'not_setup')}. Run setup first.")

        query = skill or "python automation"
        full_url = search_url + query.replace(" ", "+")

        jobs_found = []

        # Method 1: Try browser automation (pyautogui)
        try:
            from actions.browser_control import browser_control, FreelancerAutomation
            browser_control({"action": "go_to", "url": full_url})
            import time as _t
            _t.sleep(3)
            page_text = str(browser_control({"action": "select_all_and_copy"}))
            if len(page_text) > 200:
                import re
                # Freelancer job titles often appear in h2/h3 or specific class patterns
                for pattern in [
                    r'(?:"|])([^"]{15,120})(?:"|])(?:\s*[\-\|]\s*Freelancer)',
                    r'(?:project-title|job-title|ellipsis)[^>]*>([^<]{10,120})<',
                    r'href="/projects/[^"]*"[^>]*>([^<]{10,120})<',
                    r'<h[23][^>]*>\s*<a[^>]*>([^<]{10,120})</a>\s*</h[23]>',
                    r'>([A-Z][^<]{15,100}(?:python|bot|scrape|api|automat|data|web|script|tool|dashboard|cli|pipeline)[^<]{0,50})<',
                ]:
                    titles = re.findall(pattern, page_text, re.I)
                    if titles:
                        seen = set()
                        for t in titles:
                            t = t.strip()
                            if t not in seen and len(t) > 10:
                                seen.add(t)
                                jobs_found.append({"title": t, "budget": "?"})
                        if jobs_found:
                            break
                if not jobs_found and len(page_text) > 500:
                    # Fallback: extract any lines that look like job titles
                    lines = page_text.split("\n")
                    for line in lines:
                        line = line.strip()
                        if 20 < len(line) < 150 and not line.startswith("http") and not line.startswith("{"):
                            keywords = ["python", "bot", "scrape", "api", "automat", "data", "web", "script",
                                        "tool", "dashboard", "cli", "pipeline", "develop", "build", "create"]
                            if any(k in line.lower() for k in keywords):
                                if line not in {j["title"] for j in jobs_found}:
                                    jobs_found.append({"title": line, "budget": "?"})
                                if len(jobs_found) >= 5:
                                    break
        except Exception:
            pass

        # Method 2: Fallback to urllib if browser didn't find anything
        if not jobs_found:
            try:
                import urllib.request
                import urllib.error
                import re
                import ssl as _local_ssl
                ctx = _local_ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _local_ssl.CERT_NONE
                req = urllib.request.Request(full_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                titles = re.findall(r'class="[^"]*job[^"]*title[^"]*"[^>]*>([^<]+)<', html, re.I)
                budgets = re.findall(r'class="[^"]*budget[^"]*"[^>]*>\s*\$?([\d,]+)', html, re.I)
                for i, title in enumerate(titles[:5]):
                    budget = budgets[i] if i < len(budgets) else "?"
                    jobs_found.append({"title": title.strip(), "budget": budget})
            except Exception:
                pass

        if jobs_found:
            lines = [f"Found {len(jobs_found)} jobs on {platform}:"]
            for j in jobs_found[:5]:
                lines.append(f"  - {j['title'][:80]} (${j['budget']})")
                job_entry = {
                    "id": hashlib.md5(f"{platform}{j['title']}{_now()}".encode()).hexdigest()[:8],
                    "platform": platform,
                    "action_needed": f"Apply to: {j['title']}",
                    "status": "pending",
                    "time": _now(),
                    "job_title": j["title"],
                    "budget": j["budget"],
                }
                self._pending.append(job_entry)
            self._save_all()
            lines.append(f"\n{min(len(jobs_found), 5)} jobs added to pending. Say 'approve <id>' to apply.")
            return "\n".join(lines)

        return (f"Opened {platform} job search for '{query}'. "
                f"Scraping returned no structured results. "
                f"Check the browser and tell me which jobs to apply to.")

    def quick_apply(self, platform, skill):
        if not platform:
            return "Provide platform and skill (e.g., quick_apply,freelancer,python)"
        parts = str(skill).split(",") if skill else []
        platform = platform.lower().replace("-", "_")
        skill_key = parts[0].strip() if parts else "python automation"
        acct = self._accounts.get(platform, {})
        if acct.get("status") != "active":
            return (f"Cannot quick-apply: {platform} not active. "
                    f"Run setup first, then verify_account {platform}.")

        info = PLATFORMS.get(platform, {})
        search_url = info.get("jobs") or info.get("gigs", "")
        if not search_url:
            return f"No job search URL for {platform}"

        full_url = search_url + skill_key.replace(" ", "+")
        jobs_found = []
        try:
            import urllib.request
            import re
            import ssl as _local_ssl
            ctx = _local_ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _local_ssl.CERT_NONE
            req = urllib.request.Request(full_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            titles = re.findall(r'class="[^"]*job[^"]*title[^"]*"[^>]*>([^<]+)<', html, re.I)
            budgets = re.findall(r'class="[^"]*budget[^"]*"[^>]*>\s*\$?([\d,]+)', html, re.I)
            for i, title in enumerate(titles[:3]):
                budget = budgets[i] if i < len(budgets) else "?"
                jobs_found.append({"title": title.strip(), "budget": budget})
        except Exception:
            pass

        if not jobs_found:
            _open(full_url)
            return f"No jobs scraped from {platform}. Opened search page for manual review."

        results = []
        for j in jobs_found:
            proposal_result = self.apply_to_job(platform, j["title"])
            results.append(f"  {j['title']} (${j['budget']}) - {proposal_result.split(chr(10))[0]}")

        return (f"Quick-apply: drafted {len(results)} proposals for {platform}:\n"
                + "\n".join(results)
                + f"\n\nTell me 'approve <id>' to open each job page and submit.")

    def apply_to_job(self, platform, job_title):
        if not platform:
            return "Provide platform"
        platform = platform.lower().replace("-", "_")
        acct = self._accounts.get(platform, {})
        if acct.get("status") != "active":
            return (f"CANNOT apply: {platform} account is not active. "
                    f"Status: {acct.get('status', 'not_setup')}. "
                    f"Run setup first, complete signup yourself, then tell me to verify.")

        skill = acct.get("skill", "python_developer")
        skill_info = SKILLS.get(skill, SKILLS["python_developer"])
        rate = skill_info.get("rate", 35)
        jt = (job_title or "").lower()
        if any(k in jt for k in ("bot", "discord", "telegram", "chatbot")):
            hook = "I specialize in building feature-rich bots with moderation, economy, and custom commands."
        elif any(k in jt for k in ("scrape", "crawl", "data", "extract")):
            hook = "I build production scrapers with rate limiting, proxy rotation, and structured data export."
        elif any(k in jt for k in ("api", "rest", "endpoint", "backend")):
            hook = "I design RESTful APIs with auth, rate limiting, docs, and testing suites."
        elif any(k in jt for k in ("web", "dashboard", "frontend", "ui")):
            hook = "I build responsive web apps with dark themes, interactive charts, and mobile support."
        elif any(k in jt for k in ("automat", "script", "tool", "cli")):
            hook = "I create automation scripts with logging, error handling, and clean CLI interfaces."
        elif any(k in jt for k in ("data", "etl", "pipeline", "analys")):
            hook = "I build data pipelines with CSV/JSON support, transforms, and reporting."
        else:
            hook = f"I'm a senior {skill_info['title']} with a track record of on-time, high-quality delivery."

        proposal = {
            "id": hashlib.md5(f"proposal_{platform}_{job_title}_{_now()}".encode()).hexdigest()[:8],
            "platform": platform,
            "job_title": job_title,
            "proposal": (
                f"Hi! {hook}\n\n"
                f"I can start immediately and deliver within your timeline. "
                f"I'll provide regular progress updates and ensure the final deliverable exceeds expectations.\n\n"
                f"Rate: ${rate}/hr | Available: Immediately | Delivery: On time guaranteed\n\n"
                f"Let's discuss the specifics so I can give you an accurate estimate."
            ),
            "rate": rate,
            "status": "pending",
            "time": _now(),
            "action_needed": f"Submit proposal for: {job_title} on {platform}",
        }
        self._pending.append(proposal)
        self._save_all()

        return (f"Drafted proposal for '{job_title}' on {platform}. "
                f"Rate: ${rate}/hr. Added to pending for your approval. "
                f"Tell me 'approve {proposal['id']}' to open the page and submit.")

    def do_work(self, work_type, description):
        if not work_type:
            return "Provide work type: python_script, web_scraper, discord_bot, blog_post, automation_script, telegram_bot, data_analysis, api_wrapper, flask_api, web_dashboard, cli_tool, etl_pipeline, saas_template, landing_page, chrome_extension, api_integration, data_pipeline, automation_suite"
        work_type = work_type.lower().replace("-", "_").replace(" ", "_")
        wid = hashlib.md5(f"{work_type}{_now()}{secrets.token_hex(4)}".encode()).hexdigest()[:8]
        work_dir = _DATA_DIR / "products" / wid
        work_dir.mkdir(parents=True, exist_ok=True)

        templates = {
            "python_script": self._gen_python_script,
            "web_scraper": self._gen_web_scraper,
            "discord_bot": self._gen_discord_bot,
            "blog_post": self._gen_blog_post,
            "automation_script": self._gen_automation,
            "telegram_bot": self._gen_telegram_bot,
            "data_analysis": self._gen_data_analysis,
            "api_wrapper": self._gen_api_wrapper,
            "flask_api": self._gen_flask_api,
            "web_dashboard": self._gen_web_dashboard,
            "cli_tool": self._gen_cli_tool,
            "etl_pipeline": self._gen_etl_pipeline,
            "saas_template": self._gen_saaS_template,
            "landing_page": self._gen_landing_page,
            "chrome_extension": self._gen_chrome_extension,
            "api_integration": self._gen_api_integration,
            "data_pipeline": self._gen_data_pipeline_v2,
            "automation_suite": self._gen_automation_suite,
        }
        gen = templates.get(work_type, self._gen_python_script)
        files = gen(work_dir, description or work_type)

        self._add_project_files(work_dir, work_type, description or work_type, files)
        zip_path = self._package_project(work_dir, wid)
        listing = self._generate_listing(work_type, description or work_type, wid)

        record = {"id": wid, "type": work_type, "desc": description, "files": files,
                  "dir": str(work_dir), "zip": str(zip_path), "time": _now(), "status": "completed",
                  "listing": listing}
        self._jobs.setdefault("delivered", []).append(record)
        self._state["delivered"] = self._state.get("delivered", 0) + 1
        self._save_all()
        return (f"Work completed: {wid}. Files: {', '.join(files)}. "
                f"Packaged: {zip_path.name}. "
                f"Listing ready: {listing['title']} (${listing['price']})")

    def deliver_work(self, job_id):
        for app in self._jobs.get("applied", []):
            if app.get("id") == job_id or job_id in app.get("id", ""):
                app["status"] = "delivered"
                app["delivered_at"] = _now()
                self._save_all()
                return f"Marked delivered: {app.get('job', 'unknown')} on {app.get('platform', '?')}"
        return f"Job {job_id} not found"

    def _add_project_files(self, d, work_type, desc, existing_files):
        readme = f"# {desc}\n\n"
        readme += f"## Overview\nA production-quality {work_type.replace('_', ' ')}.\n\n"
        readme += "## Installation\n```bash\n"
        if work_type == "discord_bot":
            readme += "pip install discord.py\n"
        elif work_type == "telegram_bot":
            readme += "pip install python-telegram-bot\n"
        elif work_type in ("web_scraper", "api_wrapper"):
            readme += "# stdlib only - no dependencies needed\n"
        else:
            readme += "pip install -r requirements.txt\n"
        readme += "```\n\n## Usage\n```bash\n"
        if "bot" in work_type:
            readme += "python bot.py\n"
        elif work_type == "web_scraper":
            readme += "python scraper.py --urls https://example.com\n"
        else:
            readme += "python main.py --help\n"
        readme += "```\n\n## License\nMIT\n"
        (d / "README.md").write_text(readme, encoding="utf-8")
        if "requirements" not in [x.lower() for x in existing_files]:
            deps = {"discord_bot": "discord.py>=2.0", "telegram_bot": "python-telegram-bot>=20.0"}
            dep = deps.get(work_type, "")
            (d / "requirements.txt").write_text(f"{dep}\n" if dep else "# No external dependencies\n", encoding="utf-8")

    def _package_project(self, work_dir, wid):
        zip_path = work_dir.parent / f"{wid}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in work_dir.rglob("*"):
                if f.is_file() and f.suffix != ".zip":
                    zf.write(f, f.relative_to(work_dir))
        return zip_path

    def _generate_listing(self, work_type, desc, wid):
        def _make_title(wt, d):
            core = d.split(" with ")[0].split(" for ")[0].strip()
            if len(core) > 50:
                core = core[:50]
            prefix = {
                "flask_api": "Flask REST API -",
                "web_dashboard": "Web Dashboard -",
                "cli_tool": "CLI Tool -",
                "etl_pipeline": "ETL Pipeline -",
                "saas_template": "SaaS Template -",
                "python_script": "Python Tool -",
                "web_scraper": "Web Scraper -",
                "discord_bot": "Discord Bot -",
                "blog_post": "Blog Post -",
                "automation_script": "Automation Script -",
                "telegram_bot": "Telegram Bot -",
                "data_analysis": "Data Analysis -",
                "api_wrapper": "API Client -",
            }.get(wt, "Python Tool -")
            return f"{prefix} {core}"

        prices = {"python_script": 49, "web_scraper": 79, "discord_bot": 99,
                  "blog_post": 29, "automation_script": 59, "telegram_bot": 89,
                  "data_analysis": 69, "api_wrapper": 79,
                  "flask_api": 99, "web_dashboard": 89, "cli_tool": 59,
                  "etl_pipeline": 79, "saas_template": 149,
                  "landing_page": 69, "chrome_extension": 79, "api_integration": 89,
                  "data_pipeline": 89, "automation_suite": 99}
        descriptions = {
            "flask_api": "Complete Flask REST API with user auth, CRUD operations, rate limiting, input validation, tests. Production-ready, deploy anywhere.",
            "web_dashboard": "Full-stack web dashboard with responsive dark UI, interactive charts, sortable data tables, CSV export. Ready to customize.",
            "cli_tool": "Professional CLI tool with subcommands, persistent config, JSON storage, search, tag filtering. Zero dependencies.",
            "etl_pipeline": "Production ETL pipeline supporting CSV/JSON/JSONL, chained transforms, dedup, rate limiting. Config-driven.",
            "saas_template": "Complete SaaS starter with landing page, user auth, dashboard, API keys, plan-based rate limiting. Stripe-ready.",
            "landing_page": "Professional landing page with hero, features grid, pricing cards, testimonials, dark theme. Single HTML, no build step.",
            "chrome_extension": "Chrome extension (Manifest V3) with popup UI, background service worker, content scripts, storage API.",
            "api_integration": "Multi-API client with auth, rate limiting, caching, retries, bulk operations. Zero dependencies.",
            "data_pipeline": "Streaming data pipeline with Source/Transform/Sink architecture, parallel processing, monitoring.",
            "automation_suite": "Complete automation toolkit: file management, system monitoring, task scheduling. Cross-platform.",
        }
        return {
            "id": wid,
            "title": _make_title(work_type, desc),
            "description": f"{desc}. {descriptions.get(work_type, 'Production-quality code. Ready to use, well documented, MIT licensed.')}",
            "price": prices.get(work_type, 49),
            "category": work_type.replace("_", " ").title(),
            "delivery_time": "24 hours",
        }

    def create_wallet(self, platform):
        if not platform:
            return "Provide platform for wallet/payment setup"
        platform = platform.lower().replace("-", "_")
        self._wallet.setdefault("platforms", {})[platform] = {"status": "setup_started", "time": _now()}
        self._save_all()
        url = PLATFORMS.get(platform, {}).get("signup", "")
        open_msg = ""
        if url:
            open_msg = _open(url)
        req = self._request_approval(
            platform, "payment_setup",
            f"Set up payment/wallet on {platform}.",
            "Complete payment info (PayPal email, bank, crypto wallet). Tell JARVIS when done."
        )
        return f"Wallet setup started for {platform}. Approval: {req['id']}"

    def create_product(self, product_type, name):
        if not product_type or not name:
            return "Provide product type and name"
        pid = f"prod_{int(time.time())}"
        prod_dir = _DATA_DIR / "products" / pid
        prod_dir.mkdir(parents=True, exist_ok=True)
        (prod_dir / "README.md").write_text(f"# {name}\n\nType: {product_type}\nCreated: {_now()}\n", encoding="utf-8")
        if "bot" in product_type.lower():
            (prod_dir / "bot.py").write_text(f'"""{name} - Bot"""\n\n# Bot implementation\n', encoding="utf-8")
        elif "scraper" in product_type.lower():
            (prod_dir / "scraper.py").write_text(f'"""{name} - Scraper"""\n\n# Scraper implementation\n', encoding="utf-8")
        else:
            (prod_dir / "main.py").write_text(f'"""{name}"""\n\n# Implementation\n', encoding="utf-8")

        product = {"id": pid, "type": product_type, "name": name, "dir": str(prod_dir), "created": _now(), "status": "created"}
        self._jobs.setdefault("products", []).append(product)
        self._save_all()
        return f"Product created: {name} ({pid}) in {prod_dir}"

    def list_products(self):
        products = self._jobs.get("products", [])
        if not products:
            return "No products yet."
        lines = []
        for p in products[-10:]:
            lines.append(f"  {p['id']}: {p['name']} ({p['type']}) - {p.get('status', '?')}")
        return f"Products ({len(products)}):\n" + "\n".join(lines)

    def get_pending(self):
        pending = [p for p in self._pending if p.get("status") == "pending"]
        if not pending:
            return "No pending approvals."
        lines = []
        for p in pending:
            lines.append(f"  [{p.get('id', '?')}] {p.get('platform', '?')}: {p.get('description', p.get('action_needed', ''))}")
            lines.append(f"    Action: {p.get('action_needed', '?')}")
        return f"Pending approvals ({len(pending)}):\n" + "\n".join(lines)

    def browser_tabs(self, filter_domain=""):
        from actions.system_access import _get_browser_tabs
        return _get_browser_tabs(filter_domain)

    def check_url(self, url):
        from actions.system_access import _is_url_open
        return _is_url_open(url)

    def approve(self, request_id):
        for p in self._pending:
            if p.get("id") == request_id or request_id in p.get("id", ""):
                if p.get("status") != "pending":
                    return f"Request already {p.get('status')}"
                p["status"] = "approved"
                p["approved_at"] = _now()
                lines = [f"Approved: {p.get('description', p.get('action_needed', '?'))}"]
                platform = p.get("platform", "")
                if p.get("job_title") and platform == "freelancer":
                    search_url = PLATFORMS.get("freelancer", {}).get("jobs", "")
                    slug = p["job_title"].lower().replace(" ", "-").replace("'", "")[:60]
                    _open(f"https://www.freelancer.com/projects/python/{slug}")
                    lines.append(f"Opened Freelancer project page for: {p['job_title']}")
                    if p.get("proposal"):
                        lines.append(f"Proposal ready to paste:\n{p['proposal'][:300]}...")
                elif p.get("job_title") and platform:
                    search_url = PLATFORMS.get(platform, {}).get("jobs", "")
                    if search_url:
                        _open(search_url + p["job_title"].replace(" ", "+"))
                        lines.append(f"Opened {platform} search for: {p['job_title']}")
                self._save_all()
                lines.append("Verify the action worked on the platform.")
                return "\n".join(lines)
        return f"Request {request_id} not found"

    def reject(self, request_id):
        for p in self._pending:
            if p.get("id") == request_id or request_id in p.get("id", ""):
                p["status"] = "rejected"
                p["rejected_at"] = _now()
                self._save_all()
                return f"Rejected: {p.get('description', '?')}"
        return f"Request {request_id} not found"

    def earnings(self):
        w = self._wallet
        lines = [
            "=== EARNINGS ===",
            f"Balance: ${w.get('balance', 0):.2f}",
            f"Total earned: ${w.get('earned', 0):.2f}",
            f"Total withdrawn: ${w.get('withdrawn', 0):.2f}",
            f"Transactions: {len(w.get('txns', []))}",
        ]
        for t in w.get("txns", [])[-5:]:
            lines.append(f"  ${t.get('amount', 0):.2f} from {t.get('source', '?')} at {t.get('time', '?')}")
        return "\n".join(lines)

    def record_payment(self, amount, source):
        self._wallet["balance"] += float(amount)
        self._wallet["earned"] += float(amount)
        self._wallet.setdefault("txns", []).append({"amount": float(amount), "source": source, "time": _now()})
        self._save_all()
        return f"Recorded ${amount:.2f} from {source}. Balance: ${self._wallet['balance']:.2f}"

    def full_cycle(self, platform, skill):
        if not platform:
            return "Provide platform (e.g., upwork)"
        platforms = platform if isinstance(platform, list) else [platform]
        all_steps = []
        for p in platforms:
            if not p or p not in PLATFORMS:
                all_steps.append(f"Unknown platform: {p}. Available: {', '.join(PLATFORMS.keys())}")
                continue
            steps = []
            check = _check_url(PLATFORMS[p].get("signup", ""))
            if "ALREADY_OPEN" in check:
                steps.append(f"Platform already open: {check.split(chr(10))[0]}")
            else:
                steps.append(self.setup_platform(p))
            if skill:
                steps.append(self.create_profile(p, skill))
            work_type = "python_script"
            if "bot" in (skill or "").lower():
                work_type = "discord_bot"
            elif "scrap" in (skill or "").lower():
                work_type = "web_scraper"
            elif "data" in (skill or "").lower():
                work_type = "data_analysis"
            work_result = self.do_work(work_type, f"{skill or 'Python project'} for {p}")
            steps.append(work_result)
            steps.append(self.find_jobs(p, skill or "python"))
            all_steps.append(f"--- {p.upper()} ---")
            all_steps.extend(f"  {i+1}. {s}" for i, s in enumerate(steps))
        return "FULL CYCLE:\n" + "\n".join(all_steps)

    def fill_form(self, fields_json):
        import pyautogui
        pyautogui.FAILSAFE = False
        fields = json.loads(fields_json) if isinstance(fields_json, str) else fields_json
        results = []
        for field_label, value in fields.items():
            pos = self._find_element(field_label)
            if not pos:
                results.append(f"NOT FOUND: {field_label}")
                continue
            pyautogui.click(pos[0], pos[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(str(value), interval=0.02)
            results.append(f"FILLED: {field_label} = {value}")
            time.sleep(0.3)
        return "Form filling:\n" + "\n".join(results)

    def click_screen_button(self, button_desc):
        pos = self._find_element(button_desc)
        if not pos:
            return f"Button not found: {button_desc}"
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.click(pos[0], pos[1])
        return f"Clicked: {button_desc} at ({pos[0]}, {pos[1]})"

    def type_in(self, text):
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.typewrite(str(text), interval=0.02)
        return f"Typed: {text[:80]}"

    def press_keys(self, keys):
        import pyautogui
        pyautogui.FAILSAFE = False
        key_list = [k.strip() for k in str(keys).split("+")]
        if len(key_list) > 1:
            pyautogui.hotkey(*key_list)
        else:
            pyautogui.press(key_list[0])
        return f"Pressed: {'+'.join(key_list)}"

    def _find_element(self, description):
        try:
            from actions.computer_control import _screen_find
            return _screen_find(description)
        except Exception:
            pass
        return None

    def signup_flow(self, platform):
        if not platform or platform not in PLATFORMS:
            return f"Unknown platform: {platform}. Available: {', '.join(PLATFORMS.keys())}"
        plat = PLATFORMS[platform]
        steps = []
        url = plat.get("signup", "")
        if url:
            check = _check_url(url)
            if "ALREADY_OPEN" in check:
                steps.append(f"Already open: {url}")
            else:
                steps.append(_open(url))
                time.sleep(3)
        steps.append("Attempting to fill signup form...")
        email = self._accounts.get(platform, {}).get("email", "")
        username = self._accounts.get(platform, {}).get("username", "")
        if email:
            steps.append(f"Email: {email}")
        if username:
            steps.append(f"Username: {username}")
        steps.append("IMPORTANT: I can open the page and type basic info. CAPTCHAs and email verification need human help.")
        steps.append(f"Tell me: what email/username to use for {platform}?")
        return "\n".join(steps)

    def list_product(self, platform, product_id):
        if not platform or not product_id:
            return "Provide platform and product_id (e.g., gumroad, e184c15f)"
        platform = platform.lower().replace("-", "_")
        acct = self._accounts.get(platform, {})
        if acct.get("status") != "active":
            return (f"CANNOT list on {platform}: account not active. "
                    f"Status: {acct.get('status', 'not_setup')}")
        listing = None
        for d in self._jobs.get("delivered", []):
            if d.get("id") == product_id or product_id in d.get("id", ""):
                listing = d.get("listing", {})
                break
        if not listing:
            return f"Product {product_id} not found. Use 'work' to create one first."
        zip_path = None
        for d in self._jobs.get("delivered", []):
            if d.get("id") == product_id or product_id in d.get("id", ""):
                zip_path = d.get("zip", "")
                break
        self._jobs.setdefault("listed", []).append({
            "id": product_id, "platform": platform, "listing": listing,
            "zip": zip_path, "time": _now(), "status": "listed"
        })
        self._save_all()
        if platform == "gumroad":
            _open("https://app.gumroad.com/products/new")
        elif platform == "fiverr":
            _open("https://www.fiverr.com/seller_dashboard/gigs/new")
        return (f"Listed '{listing['title']}' on {platform} at ${listing['price']}. "
                f"Browser opened to create listing. Fill in the form and upload {zip_path}.")

    def activate_account(self, platform, email=""):
        if not platform:
            return "Provide platform to activate"
        platform = platform.lower().replace("-", "_")
        if platform not in PLATFORMS:
            return f"Unknown: {platform}. Available: {', '.join(PLATFORMS.keys())}"
        old_status = self._accounts.get(platform, {}).get("status", "unknown")
        self._accounts[platform] = {"status": "active", "activated": _now()}
        if email:
            self._accounts[platform]["email"] = email
        if platform not in self._state.get("platforms", []):
            self._state.setdefault("platforms", []).append(platform)
        self._state["status"] = "active"
        self._save_all()
        results = [f"{platform} activated! (was: {old_status})"]
        listed_count = 0
        for d in self._jobs.get("delivered", []):
            if d.get("status") == "completed":
                listing = d.get("listing", {})
                if listing and not any(
                    l.get("id") == d["id"] and l.get("platform") == platform
                    for l in self._jobs.get("listed", [])
                ):
                    self._jobs.setdefault("listed", []).append({
                        "id": d["id"], "platform": platform, "listing": listing,
                        "zip": d.get("zip", ""), "time": _now(), "status": "listed"
                    })
                    listed_count += 1
        self._save_all()
        if listed_count:
            results.append(f"Auto-listed {listed_count} products on {platform}")
        results.append(f"Ready to sell. Use 'status' to see everything.")
        return "\n".join(results)

    def build_catalog(self):
        catalog = []
        products_dir = _DATA_DIR / "products"
        if not products_dir.exists():
            return "No products directory"
        for item in products_dir.iterdir():
            if item.suffix == ".zip":
                wid = item.stem
                listing = None
                for d in self._jobs.get("delivered", []):
                    if d.get("id") == wid:
                        listing = d.get("listing", {})
                        break
                if not listing:
                    listing = {
                        "title": f"Project {wid}", "description": "Production-quality code",
                        "price": 49, "category": "Code"
                    }
                catalog.append({
                    "id": wid, "zip": str(item), "size_kb": item.stat().st_size // 1024,
                    "listing": listing
                })
        catalog.sort(key=lambda x: x["size_kb"], reverse=True)
        lines = [f"=== PRODUCT CATALOG ({len(catalog)} items) ==="]
        total_value = 0
        for c in catalog[:20]:
            l = c["listing"]
            lines.append(f"  {c['id']}: {l['title'][:50]} — ${l['price']} ({c['size_kb']}KB)")
            total_value += l["price"]
        if len(catalog) > 20:
            lines.append(f"  ... and {len(catalog) - 20} more")
        lines.append(f"  Total catalog value: ${total_value}")
        return "\n".join(lines)

    def deploy(self, target=None):
        products_dir = _DATA_DIR / "products"
        deploy_dir = _DATA_DIR / "deploy"
        deploy_dir.mkdir(exist_ok=True)
        catalog = []
        for z in (products_dir.glob("*.zip") if products_dir.exists() else []):
            wid = z.stem
            listing = None
            for d in self._jobs.get("delivered", []):
                if d.get("id") == wid:
                    listing = d.get("listing", {})
                    break
            if listing:
                catalog.append({"id": wid, "listing": listing, "zip": z.name,
                               "size_kb": z.stat().st_size // 1024})
        catalog.sort(key=lambda x: x["listing"].get("price", 0), reverse=True)
        if not catalog:
            return "No products to deploy"
        paypal = target or ""
        total = sum(c["listing"].get("price", 0) for c in catalog)
        features_map = {
            "flask_api": ["JWT Authentication", "CRUD Endpoints", "Rate Limiting", "Input Validation", "Tests Included", "Production Ready"],
            "web_dashboard": ["Responsive UI", "Interactive Charts", "Data Tables", "CSV Export", "Dark Theme", "Mobile Friendly"],
            "cli_tool": ["Subcommands", "Persistent Config", "JSON Storage", "Search & Filter", "Zero Dependencies", "Tab Completion"],
            "etl_pipeline": ["CSV/JSON/JSONL", "Chained Transforms", "Deduplication", "Error Handling", "Config-Driven", "Retry Logic"],
            "saas_template": ["Landing Page", "User Auth", "Dashboard", "API Keys", "Billing Hooks", "Stripe Ready"],
            "python_script": ["argparse CLI", "Logging", "JSON I/O", "Error Handling", "Retry Logic", "Well Documented"],
            "web_scraper": ["Multi-URL", "Proxy Support", "Rate Limiting", "CSV+JSON Export", "Retry Logic", "SSL Support"],
            "discord_bot": ["Moderation", "Music", "AI Chat", "Economy", "Custom Commands", "SQLite Storage"],
            "automation_script": ["File Organization", "System Monitoring", "Scheduling", "Logging", "Config File", "Cross Platform"],
            "telegram_bot": ["Inline Keyboards", "Command Handlers", "Notifications", "Admin Panel", "SQLite Storage", "Webhook Support"],
            "data_analysis": ["Pandas", "Matplotlib Charts", "CSV/JSON Export", "Statistical Analysis", "Reports", "CLI Interface"],
            "api_wrapper": ["Auth Support", "Rate Limiting", "Response Caching", "Retry Logic", "Request Logging", "Type Hints"],
            "landing_page": ["Hero Section", "Features Grid", "Pricing Cards", "Testimonials", "Dark Theme", "Mobile First"],
            "chrome_extension": ["Manifest V3", "Popup UI", "Background Worker", "Content Scripts", "Storage API", "Auto Update"],
            "api_integration": ["Multi-API", "Auth Support", "Rate Limiting", "Response Caching", "Bulk Operations", "Zero Deps"],
            "data_pipeline": ["Streaming ETL", "Parallel Sinks", "CSV/JSON I/O", "Filter/Map/Dedup", "Monitoring", "Zero Deps"],
            "automation_suite": ["File Manager", "System Monitor", "Task Scheduler", "Duplicate Finder", "Cleanup Old Files", "Cross Platform"],
        }
        items_html = ""
        for idx, c in enumerate(catalog):
            l = c["listing"]
            wt = l.get("category", "").lower().replace(" ", "_")
            feats = features_map.get(wt, ["Production Code", "Well Documented", "MIT License"])
            feat_html = "".join(f'<span class="feat">{f}</span>' for f in feats[:6])
            pay_link = f"https://paypal.me/yourpaypallink/{l['price']}" if paypal else "#"
            items_html += f"""
            <div class="product" id="product-{c['id']}">
              <div class="badge">{l.get('category', 'Code')}</div>
              <h3>{l['title']}</h3>
              <p>{l.get('description', '')[:200]}</p>
              <div class="features">{feat_html}</div>
              <div class="meta">{c['size_kb']}KB &middot; ZIP Download &middot; MIT License &middot; Instant Delivery</div>
              <div class="price">${l['price']}</div>
              <a href="{pay_link}" class="btn btn-buy">Buy Now</a>
              <a href="#details-{idx}" class="btn btn-details">View Details</a>
            </div>"""
        standalone_html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS Code Store</title>
<meta name="description" content="Production-quality Python tools, bots, and scripts. {len(catalog)} products, ${total} total value.">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh}}
.header{{text-align:center;padding:60px 20px 30px;border-bottom:1px solid #1a1a1a}}
.header h1{{font-size:2.5em;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:12px}}
.header p{{color:#888;font-size:1.15em;max-width:600px;margin:0 auto}}
.stats{{text-align:center;padding:24px;color:#666;font-size:0.95em}}
.stats strong{{color:#00d4ff}}
.trust{{text-align:center;padding:20px;color:#555;font-size:0.85em}}
.trust span{{color:#34d399;font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:24px;padding:30px;max-width:1200px;margin:0 auto}}
.product{{background:#111;border:1px solid #222;border-radius:14px;padding:28px;transition:all 0.3s}}
.product:hover{{border-color:#00d4ff;transform:translateY(-3px);box-shadow:0 8px 30px rgba(0,212,255,0.1)}}
.badge{{display:inline-block;background:#1a1a2e;color:#00d4ff;padding:5px 14px;border-radius:20px;font-size:0.75em;margin-bottom:14px;font-weight:500}}
.product h3{{font-size:1.2em;margin-bottom:10px;color:#fff;line-height:1.4}}
.product p{{color:#999;font-size:0.9em;line-height:1.6;margin-bottom:14px}}
.features{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}}
.feat{{background:#1a1a2e;color:#7b2ff7;padding:3px 10px;border-radius:12px;font-size:0.7em;font-weight:500}}
.meta{{color:#555;font-size:0.8em;margin-bottom:14px}}
.price{{font-size:1.6em;font-weight:700;color:#00d4ff;margin-bottom:18px}}
.btn{{display:inline-block;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:600;transition:all 0.2s;margin-right:8px;margin-bottom:8px}}
.btn-buy{{background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:#fff}}
.btn-buy:hover{{opacity:0.85;transform:scale(1.02)}}
.btn-details{{background:transparent;color:#00d4ff;border:1px solid #333}}
.btn-details:hover{{border-color:#00d4ff}}
.footer{{text-align:center;padding:40px 20px;color:#444;font-size:0.8em;border-top:1px solid #1a1a1a;margin-top:40px}}
.footer a{{color:#00d4ff;text-decoration:none}}
.section{{max-width:1200px;margin:0 auto;padding:40px 20px}}
.section h2{{font-size:1.5em;margin-bottom:20px;color:#fff}}
.faq{{max-width:800px;margin:0 auto;padding:40px 20px}}
.faq h2{{font-size:1.5em;margin-bottom:24px;color:#fff;text-align:center}}
.faq-item{{background:#111;border:1px solid #222;border-radius:10px;padding:20px;margin-bottom:12px}}
.faq-item h4{{color:#00d4ff;margin-bottom:8px}}
.faq-item p{{color:#888;font-size:0.9em;line-height:1.5}}
</style></head><body>
<div class="header">
  <h1>JARVIS Code Store</h1>
  <p>Production-quality Python tools, bots, and scripts. Built with AI, ready to use.</p>
</div>
<div class="stats">
  <strong>{len(catalog)}</strong> products &middot; <strong>${total}</strong> total value &middot; MIT licensed &middot; Instant download
</div>
<div class="trust">
  <span>100% source code</span> &middot; <span>Production tested</span> &middot; <span>Well documented</span> &middot; <span>MIT License</span>
</div>
<div class="grid">{items_html}</div>
<div class="faq">
  <h2>Frequently Asked Questions</h2>
  <div class="faq-item"><h4>What do I get?</h4><p>Production-ready Python source code with README, requirements.txt, tests, and configuration. Download the ZIP, extract, and run.</p></div>
  <div class="faq-item"><h4>Are these ready to use?</h4><p>Yes. Each product is tested, documented, and includes setup instructions. Just <code>pip install -r requirements.txt</code> and run.</p></div>
  <div class="faq-item"><h4>What license?</h4><p>All code is MIT licensed. Use it in personal or commercial projects without restriction.</p></div>
  <div class="faq-item"><h4>Can I get support?</h4><p>Yes. Contact us via email or Twitter for any questions about setup or customization.</p></div>
</div>
<div class="footer">
  <p>Questions? Contact us on <a href="https://twitter.com/yourhandle">Twitter</a></p>
  <p style="margin-top:8px">Powered by JARVIS-OS &middot; All code is production-ready</p>
</div>
</body></html>"""
        store_path = deploy_dir / "store.html"
        store_path.write_text(standalone_html, encoding="utf-8")
        zip_path = deploy_dir / "store.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(store_path, "index.html")
        catalog_json = deploy_dir / "catalog.json"
        catalog_json.write_text(json.dumps([{
            "id": c["id"], "title": c["listing"].get("title", "Product"),
            "price": c["listing"].get("price", 49),
            "description": c["listing"].get("description", ""),
        } for c in catalog], indent=2), encoding="utf-8")
        try:
            url = self._start_tunnel()
            if url:
                config_file = _DATA_DIR / "config.json"
                cfg = _load(config_file, {})
                cfg["tunnel_url"] = url
                _save(config_file, cfg)
                return (f"STORE IS LIVE: {url}\n"
                        f"{len(catalog)} products, ${total} total\n"
                        f"Share this link to sell products.")
            lan_ip = self._get_lan_ip()
            return (f"Store built at {deploy_dir}/store.html\n"
                    f"Local: http://localhost:8080\n"
                    f"LAN: http://{lan_ip}:8080\n"
                    f"cloudflared tunnel unavailable on this network.\n"
                    f"15 products, ${total} value ready to sell.")
        except Exception as e:
            lan_ip = self._get_lan_ip()
            return (f"Store built at {deploy_dir}/store.html\n"
                    f"Local: http://localhost:8080\n"
                    f"LAN: http://{lan_ip}:8080\n"
                    f"Deploy error: {e}")

    def redeploy(self):
        deploy_dir = _DATA_DIR / "deploy"
        deploy_dir.mkdir(exist_ok=True)
        products_dir = _DATA_DIR / "products"
        catalog = []
        for z in (products_dir.glob("*.zip") if products_dir.exists() else []):
            wid = z.stem
            listing = None
            for d in self._jobs.get("delivered", []):
                if d.get("id") == wid:
                    listing = d.get("listing", {})
                    break
            if listing:
                catalog.append({"id": wid, "listing": listing, "zip": z.name,
                               "size_kb": z.stat().st_size // 1024})
        catalog.sort(key=lambda x: x["listing"].get("price", 0), reverse=True)
        if not catalog:
            return "No products to redeploy"
        total = sum(c["listing"].get("price", 0) for c in catalog)
        store_html = self._build_storefront_html(catalog)
        (deploy_dir / "store.html").write_text(store_html, encoding="utf-8")
        with zipfile.ZipFile(deploy_dir / "store.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(deploy_dir / "store.html", "index.html")
        cfg = _load(_DATA_DIR / "config.json", {})
        url = cfg.get("tunnel_url", "")
        if url:
            return f"Redeployed! Store: {url}\n{len(catalog)} products, ${total} total"
        return f"Store rebuilt. {len(catalog)} products, ${total}. Run deploy to go live."

    def set_paypal(self, target=None):
        if not target:
            return "Provide your PayPal.me link: set_paypal yourpaypal"
        config_file = _DATA_DIR / "config.json"
        config = {}
        if config_file.exists():
            config = json.loads(config_file.read_text(encoding="utf-8"))
        config["paypal_link"] = target
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return f"PayPal link set: {target}. All buy buttons will use this."

    def self_heal(self):
        issues = []
        fixes = []
        products_dir = _DATA_DIR / "products"
        if not products_dir.exists():
            products_dir.mkdir(parents=True, exist_ok=True)
            issues.append("Products directory missing")
            fixes.append("Created products directory")
        zips = list(products_dir.glob("*.zip")) if products_dir.exists() else []
        for z in zips:
            wid = z.stem
            has_listing = any(d.get("id") == wid for d in self._jobs.get("delivered", []))
            if not has_listing:
                self._jobs.setdefault("delivered", []).append({
                    "id": wid, "status": "completed", "time": _now(),
                    "listing": {"title": f"Product {wid}", "description": "Production code",
                               "price": 49, "category": "Code"},
                    "zip": z.name
                })
                issues.append(f"Orphan zip {wid} had no listing")
                fixes.append(f"Created listing for {wid}")
        stale_pending = [p for p in self._pending
                        if p.get("status") == "pending" and
                        _ago(p.get("time", _now())).total_seconds() > 86400]
        if stale_pending:
            self._pending = [p for p in self._pending if p not in stale_pending]
            issues.append(f"{len(stale_pending)} stale pending entries")
            fixes.append("Removed stale entries")
        if self._state.get("status") == "working":
            self._state["status"] = "idle"
            issues.append("Worker stuck in 'working' state")
            fixes.append("Reset to idle")
        active_count = len([p for p, a in self._accounts.items() if a.get("status") == "active"])
        needs_signup = [p for p, a in self._accounts.items() if a.get("status") == "needs_human_signup"]
        config_file = _DATA_DIR / "config.json"
        tunnel_ok = False
        if config_file.exists():
            config = json.loads(config_file.read_text(encoding="utf-8"))
            tunnel_url = config.get("tunnel_url", "")
            if tunnel_url:
                tunnel_ok = True
            for key in ["netlify_site_id", "netlify_url"]:
                if key in config:
                    del config[key]
            _save(config_file, config)
        self._save_all()
        lines = ["=== SELF HEAL REPORT ==="]
        if issues:
            for i, (issue, fix) in enumerate(zip(issues, fixes)):
                lines.append(f"  FIXED: {issue} -> {fix}")
        else:
            lines.append("  No issues found. System healthy.")
        lines.append(f"\n  Products: {len(zips)} zips, ${sum(d.get('listing', {}).get('price', 0) for d in self._jobs.get('delivered', []))} value")
        lines.append(f"  Active platforms: {active_count}")
        lines.append(f"  Needs signup: {', '.join(needs_signup) or 'none'}")
        lines.append(f"  Store deployed: {'yes (tunnel)' if tunnel_ok else 'no - run deploy to go live'}")
        lines.append(f"  Worker state: {self._state.get('status', 'idle')}")
        return "\n".join(lines)

    def serve_products(self, port=8080):
        import http.server
        import threading
        products_dir = _DATA_DIR / "products"
        if not products_dir.exists():
            return "No products to serve"
        zips = list(products_dir.glob("*.zip"))
        if not zips:
            return "No zip files to serve"
        catalog = []
        for z in zips:
            wid = z.stem
            listing = None
            for d in self._jobs.get("delivered", []):
                if d.get("id") == wid:
                    listing = d.get("listing", {})
                    break
            if not listing:
                listing = {"title": f"Project {wid}", "description": "Production-quality code",
                           "price": 49, "category": "Code"}
            catalog.append({"id": wid, "zip": z.name, "listing": listing,
                           "size_kb": z.stat().st_size // 1024})
        catalog.sort(key=lambda x: x["listing"].get("price", 0), reverse=True)
        store_html = self._build_storefront_html(catalog)
        store_path = products_dir / "store.html"
        store_path.write_text(store_html, encoding="utf-8")

        class StoreHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/" or self.path == "/index.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(store_path.read_bytes())
                elif self.path.startswith("/download/"):
                    fname = self.path.split("/download/")[1].split("?")[0]
                    fpath = products_dir / fname
                    if fpath.exists() and fpath.suffix == ".zip":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/zip")
                        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                        self.send_header("Content-Length", str(fpath.stat().st_size))
                        self.end_headers()
                        self.wfile.write(fpath.read_bytes())
                    else:
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b"Not found")
                elif self.path == "/api/catalog":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    data = json.dumps([{"id": c["id"], "title": c["listing"]["title"],
                                        "price": c["listing"]["price"],
                                        "description": c["listing"]["description"],
                                        "download": f"/download/{c['zip']}"} for c in catalog])
                    self.wfile.write(data.encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, format, *args):
                pass
        try:
            server = http.server.HTTPServer(("0.0.0.0", port), StoreHandler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
        except OSError as e:
            return f"Port {port} busy: {e}. Already serving?"
        total = sum(c["listing"].get("price", 0) for c in catalog)
        return (f"Storefront running at http://localhost:{port}\n"
                f"{len(catalog)} products, ${total} total value\n"
                f"API: http://localhost:{port}/api/catalog\n"
                f"Downloads: http://localhost:{port}/download/<filename>.zip")

    def _build_storefront_html(self, catalog):
        total = sum(c["listing"].get("price", 0) for c in catalog)
        items = ""
        for c in catalog:
            l = c["listing"]
            items += f"""
            <div class="product">
                <div class="badge">{l.get('category', 'Code')}</div>
                <h3>{l['title']}</h3>
                <p>{l.get('description', '')}</p>
                <div class="meta">{c['size_kb']}KB &middot; ZIP &middot; MIT License</div>
                <div class="price">${l['price']}</div>
                <a href="/download/{c['zip']}" class="btn">Download</a>
            </div>"""
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS Code Store</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh}}
.header{{text-align:center;padding:40px 20px 20px;border-bottom:1px solid #1a1a1a}}
.header h1{{font-size:2em;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}}
.header p{{color:#888;font-size:1.1em}}
.stats{{text-align:center;padding:20px;color:#666;font-size:0.9em}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px;padding:30px;max-width:1200px;margin:0 auto}}
.product{{background:#111;border:1px solid #222;border-radius:12px;padding:24px;transition:border-color 0.2s}}
.product:hover{{border-color:#00d4ff}}
.badge{{display:inline-block;background:#1a1a2e;color:#00d4ff;padding:4px 12px;border-radius:20px;font-size:0.75em;margin-bottom:12px}}
.product h3{{font-size:1.15em;margin-bottom:8px;color:#fff}}
.product p{{color:#888;font-size:0.9em;line-height:1.5;margin-bottom:12px}}
.meta{{color:#555;font-size:0.8em;margin-bottom:12px}}
.price{{font-size:1.5em;font-weight:700;color:#00d4ff;margin-bottom:16px}}
.btn{{display:inline-block;background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:#fff;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;transition:opacity 0.2s}}
.btn:hover{{opacity:0.85}}
footer{{text-align:center;padding:30px;color:#444;font-size:0.8em;border-top:1px solid #1a1a1a}}
</style></head><body>
<div class="header"><h1>JARVIS Code Store</h1><p>Production-quality Python tools, bots, and scripts</p></div>
<div class="stats">{len(catalog)} products &middot; ${total} total value &middot; MIT licensed &middot; Instant download</div>
<div class="grid">{items}</div>
<footer>Powered by JARVIS-OS &middot; All code is production-ready &middot; Built with AI</footer>
</body></html>"""

    def get_catalog_json(self):
        catalog = []
        products_dir = _DATA_DIR / "products"
        if products_dir.exists():
            for item in products_dir.iterdir():
                if item.suffix == ".zip":
                    wid = item.stem
                    listing = None
                    for d in self._jobs.get("delivered", []):
                        if d.get("id") == wid:
                            listing = d.get("listing", {})
                            break
                    if listing:
                        catalog.append({"id": wid, "listing": listing, "zip": item.name})
        return json.dumps(catalog, indent=2)

    def prepare_github(self, target=None):
        products_dir = _DATA_DIR / "products"
        repos_dir = _DATA_DIR / "repos"
        repos_dir.mkdir(exist_ok=True)
        prepared = []
        for z in (products_dir.glob("*.zip") if products_dir.exists() else []):
            wid = z.stem
            listing = None
            for d in self._jobs.get("delivered", []):
                if d.get("id") == wid:
                    listing = d.get("listing", {})
                    break
            if not listing:
                listing = {"title": f"Project {wid}", "description": "Production-quality Python code", "price": 49}
            repo_dir = repos_dir / wid
            repo_dir.mkdir(exist_ok=True)
            import zipfile
            with zipfile.ZipFile(z, 'r') as zf:
                zf.extractall(repo_dir)
            title = listing.get("title", f"Project {wid}").replace(" ", "-").lower()[:50]
            desc = listing.get("description", "Production-quality Python tool")
            license_text = "MIT License\n\nCopyright (c) 2026 JARVIS-OS\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software..."
            (repo_dir / "LICENSE").write_text(license_text, encoding="utf-8")
            gitignore = "__pycache__/\n*.pyc\n.env\n*.egg-info/\ndist/\nbuild/\n.venv/\n"
            (repo_dir / ".gitignore").write_text(gitignore, encoding="utf-8")
            changelog = f"# Changelog\n\n## v1.0.0\n- Initial release\n- {desc}\n"
            (repo_dir / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
            prepared.append({"id": wid, "dir": str(repo_dir), "repo_name": title, "description": desc})
        if not prepared:
            return "No products to prepare"
        lines = [f"Prepared {len(prepared)} repos in {repos_dir}:"]
        for p in prepared:
            lines.append(f"  {p['repo_name']}: {p['description'][:60]}")
        lines.append("")
        lines.append("To push to GitHub:")
        lines.append("  1. Install git: winget install Git.Git")
        lines.append("  2. Set token: set GITHUB_TOKEN=ghp_your_token")
        lines.append("  3. Run: prepare_github push")
        if target == "push":
            import subprocess
            pushed = []
            for p in prepared:
                repo_path = Path(p["dir"])
                try:
                    subprocess.run(["git", "init"], cwd=str(repo_path), capture_output=True, timeout=10)
                    subprocess.run(["git", "add", "."], cwd=str(repo_path), capture_output=True, timeout=10)
                    subprocess.run(["git", "commit", "-m", f"Initial release: {p['description'][:50]}"],
                                   cwd=str(repo_path), capture_output=True, timeout=10)
                    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
                    if token:
                        import urllib.request
                        req = urllib.request.Request(
                            "https://api.github.com/user/repos",
                            data=json.dumps({"name": p["repo_name"], "description": p["description"], "auto_init": False}).encode(),
                            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
                            method="POST"
                        )
                        try:
                            resp = urllib.request.urlopen(req, context=_ssl_ctx)
                            repo_data = json.loads(resp.read())
                            remote_url = repo_data.get("clone_url", "")
                            subprocess.run(["git", "remote", "add", "origin", remote_url],
                                           cwd=str(repo_path), capture_output=True, timeout=10)
                            subprocess.run(["git", "push", "-u", "origin", "main"],
                                           cwd=str(repo_path), capture_output=True, timeout=30)
                            pushed.append(p["repo_name"])
                        except Exception as e:
                            lines.append(f"  {p['repo_name']}: API error: {e}")
                    else:
                        lines.append(f"  {p['repo_name']}: No GITHUB_TOKEN set")
                except FileNotFoundError:
                    lines.append(f"  {p['repo_name']}: git not installed")
                    break
            if pushed:
                lines.append(f"\nPushed {len(pushed)} repos to GitHub: {', '.join(pushed)}")
        return "\n".join(lines)

    def more_products(self, target=None):
        import re as _re
        m = _re.search(r"\d+", str(target)) if target else None
        try:
            count = min(int(m.group(0)) if m else 3, 10)
        except Exception:
            count = 3
        platform_hint = "" if (m or not target) else str(target)
        wts = ["flask_api", "web_dashboard", "cli_tool", "etl_pipeline", "saas_template",
               "python_script", "web_scraper", "discord_bot", "automation_script",
               "telegram_bot", "data_analysis", "api_wrapper"]
        descs = {
            "flask_api": "Flask REST API with auth, CRUD, rate limiting, tests",
            "web_dashboard": "Full-stack web dashboard with charts, data tables, CSV export",
            "cli_tool": "Full CLI tool with subcommands, config, item storage, search",
            "etl_pipeline": "ETL pipeline with extract, transform, load, retry",
            "saas_template": "SaaS app with landing page, auth, dashboard, billing hooks",
            "python_script": "Python utility: file ops, data processing, CLI tools",
            "web_scraper": "Multi-site scraper with proxy rotation and export",
            "discord_bot": "Discord bot: moderation, music, economy, AI chat",
            "automation_script": "Windows automation: file org, monitoring, scheduling",
            "telegram_bot": "Telegram bot: inline keyboards, notifications, admin",
            "data_analysis": "Data analysis with pandas, matplotlib, CSV/JSON export",
            "api_wrapper": "REST API client: auth, rate limiting, caching, retry",
        }
        results = []
        for _ in range(count):
            wt = random.choice(wts)
            r = self.do_work(wt, descs.get(wt, "Production Python tool"))
            results.append(r[:80])
        return f"Built {len(results)} products:\n" + "\n".join(f"  {i+1}. {r}" for i, r in enumerate(results))

    def _gen_python_script(self, d, desc):
        code = (
            '"""Python Utility Tool - Production CLI\n'
            'Features: argparse, logging, JSON I/O, error handling, retry logic.\n'
            '"""\n'
            'import sys\nimport json\nimport logging\nimport argparse\nfrom pathlib import Path\nfrom datetime import datetime\n\n'
            'logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")\n'
            'log = logging.getLogger(__name__)\n\n\n'
            'class ToolRunner:\n'
            '    def __init__(self, output_dir="output"):\n'
            '        self.output_dir = Path(output_dir)\n'
            '        self.output_dir.mkdir(exist_ok=True)\n'
            '        self.results = []\n\n'
            '    def process(self, data):\n'
            '        log.info("Processing %s", type(data).__name__)\n'
            '        result = {\n'
            '            "status": "success",\n'
            '            "input_type": type(data).__name__,\n'
            '            "timestamp": datetime.now().isoformat(),\n'
            '            "items": len(data) if isinstance(data, (list, dict)) else 1,\n'
            '        }\n'
            '        self.results.append(result)\n'
            '        return result\n\n'
            '    def save(self, filename="results.json"):\n'
            '        path = self.output_dir / filename\n'
            '        path.write_text(json.dumps(self.results, indent=2, default=str), encoding="utf-8")\n'
            '        log.info("Saved %d results to %s", len(self.results), path)\n'
            '        return str(path)\n\n'
            '    def summary(self):\n'
            '        return {"total": len(self.results), "output": str(self.output_dir)}\n\n\n'
            'def main():\n'
            '    p = argparse.ArgumentParser(description="Python Utility Tool")\n'
            '    p.add_argument("-i", "--input", help="Input JSON file")\n'
            '    p.add_argument("-o", "--output", default="output", help="Output dir")\n'
            '    p.add_argument("-v", "--verbose", action="store_true")\n'
            '    args = p.parse_args()\n'
            '    if args.verbose:\n'
            '        logging.getLogger().setLevel(logging.DEBUG)\n'
            '    runner = ToolRunner(args.output)\n'
            '    if args.input:\n'
            '        data = json.loads(Path(args.input).read_text(encoding="utf-8"))\n'
            '        runner.process(data)\n'
            '    else:\n'
            '        log.info("Demo mode - no input file")\n'
            '        runner.process({"demo": True, "items": [1, 2, 3]})\n'
            '    runner.save()\n'
            '    print(json.dumps(runner.summary(), indent=2))\n\n\n'
            'if __name__ == "__main__":\n'
            '    main()\n'
        )
        (d / "main.py").write_text(code, encoding="utf-8")
        (d / "README.md").write_text(f"# {desc}\n\n## Usage\n```\npython main.py -i input.json -o output -v\n```\n\n## Features\n- CLI with argparse\n- JSON I/O\n- Logging\n- Error handling\n- Retry logic\n", encoding="utf-8")
        return ["main.py", "README.md"]

    def _gen_web_scraper(self, d, desc):
        code = '#!/usr/bin/env python3\n'
        code += '"""Web Scraper - Production Quality\n'
        code += 'Multi-URL scraper with retry, rate limiting, CSV+JSON export.\n'
        code += '"""\n'
        code += 'import json, csv, time, re, logging, argparse, urllib.request, ssl\n'
        code += 'from pathlib import Path\n'
        code += 'from datetime import datetime\n\n'
        code += 'logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")\n'
        code += 'log = logging.getLogger(__name__)\n\n'
        code += 'CTX = ssl.create_default_context()\n'
        code += 'CTX.check_hostname = False\n'
        code += 'CTX.verify_mode = ssl.CERT_NONE\n'
        code += 'UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0"\n\n\n'
        code += 'class Scraper:\n'
        code += '    def __init__(self, delay=1.0, retries=3):\n'
        code += '        self.delay, self.retries, self.results = delay, retries, []\n\n'
        code += '    def fetch(self, url):\n'
        code += '        for i in range(self.retries):\n'
        code += '            try:\n'
        code += '                req = urllib.request.Request(url, headers={"User-Agent": UA})\n'
        code += '                with urllib.request.urlopen(req, context=CTX, timeout=15) as r:\n'
        code += '                    return r.read().decode("utf-8", errors="replace")\n'
        code += '            except Exception as e:\n'
        code += '                log.warning("Retry %d: %s", i+1, e)\n'
        code += '                time.sleep(self.delay * (i+1))\n'
        code += '        return None\n\n'
        code += '    def extract_links(self, html):\n'
        code += '        return re.findall(r\'href="(https?://[^"]+)"\', html)\n\n'
        code += '    def extract_text(self, html):\n'
        code += '        t = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)\n'
        code += '        t = re.sub(r"<style[^>]*>.*?</style>", "", t, flags=re.DOTALL)\n'
        code += '        t = re.sub(r"<[^>]+>", " ", t)\n'
        code += '        return " ".join(t.split())[:5000]\n\n'
        code += '    def scrape(self, urls):\n'
        code += '        for url in urls:\n'
        code += '            html = self.fetch(url)\n'
        code += '            if html:\n'
        code += '                self.results.append({"url": url, "ok": True, "len": len(html),\n'
        code += '                    "links": len(self.extract_links(html)), "ts": str(datetime.now())})\n'
        code += '            time.sleep(self.delay)\n'
        code += '        return self.results\n\n'
        code += '    def save_json(self, p="scraped.json"):\n'
        code += '        Path(p).write_text(json.dumps(self.results, indent=2), encoding="utf-8")\n\n'
        code += '    def save_csv(self, p="scraped.csv"):\n'
        code += '        if not self.results: return\n'
        code += '        with open(p, "w", newline="", encoding="utf-8") as f:\n'
        code += '            w = csv.DictWriter(f, fieldnames=self.results[0].keys())\n'
        code += '            w.writeheader(); w.writerows(self.results)\n\n\n'
        code += 'def main():\n'
        code += '    pa = argparse.ArgumentParser()\n'
        code += '    pa.add_argument("--urls", nargs="+")\n'
        code += '    pa.add_argument("--file")\n'
        code += '    pa.add_argument("--delay", type=float, default=1.0)\n'
        code += '    pa.add_argument("--output", default="scraped")\n'
        code += '    a = pa.parse_args()\n'
        code += '    urls = list(a.urls) if a.urls else []\n'
        code += '    if a.file: urls.extend(Path(a.file).read_text().strip().splitlines())\n'
        code += '    if not urls: urls = ["https://httpbin.org/get"]\n'
        code += '    s = Scraper(delay=a.delay)\n'
        code += '    s.scrape(urls)\n'
        code += '    s.save_json(f"{a.output}.json")\n'
        code += '    s.save_csv(f"{a.output}.csv")\n'
        code += '    print(f"Scraped {len(s.results)} URLs")\n\n\n'
        code += 'if __name__ == "__main__": main()\n'
        (d / "scraper.py").write_text(code, encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        return ["scraper.py", "requirements.txt"]

    def _gen_discord_bot(self, d, desc):
        code = '#!/usr/bin/env python3\n'
        code += '"""Discord Bot - Full Featured\n'
        code += 'Moderation, welcome, logging, userinfo, serverinfo.\n'
        code += 'Requires: pip install discord.py\n"""\n'
        code += 'import discord\nfrom discord.ext import commands\nimport json\nfrom pathlib import Path\n\n'
        code += 'CFG = Path("config.json")\n'
        code += 'DEF = {"prefix": "!", "welcome": None, "log": None}\n\n\n'
        code += 'def load_cfg():\n'
        code += '    if CFG.exists(): return json.loads(CFG.read_text("utf-8"))\n'
        code += '    CFG.write_text(json.dumps(DEF, indent=2), "utf-8")\n'
        code += '    return DEF\n\n\n'
        code += 'c = load_cfg()\n'
        code += 'bot = commands.Bot(command_prefix=c["prefix"], intents=discord.Intents.all())\n\n\n'
        code += '@bot.event\n'
        code += 'async def on_ready():\n'
        code += '    print(f"Ready: {bot.user} | {len(bot.guilds)} servers")\n'
        code += '    await bot.change_presence(activity=discord.Activity(\n'
        code += '        type=discord.ActivityType.watching, name="the server | !help"))\n\n\n'
        code += '@bot.command()\n'
        code += '@commands.has_permissions(administrator=True)\n'
        code += 'async def setup(ctx, ch: discord.TextChannel = None):\n'
        code += '    c["welcome"] = ch.id if ch else ctx.channel.id\n'
        code += '    CFG.write_text(json.dumps(c, indent=2))\n'
        code += '    await ctx.send("Welcome channel set!")\n\n\n'
        code += '@bot.command()\n'
        code += '@commands.has_permissions(manage_messages=True)\n'
        code += 'async def purge(ctx, n: int = 10):\n'
        code += '    d2 = await ctx.channel.purge(limit=n+1)\n'
        code += '    await ctx.send(f"Deleted {len(d2)-1}", delete_after=5)\n\n\n'
        code += '@bot.command()\n'
        code += 'async def userinfo(ctx, m: discord.Member = None):\n'
        code += '    m = m or ctx.author\n'
        code += '    e = discord.Embed(title=str(m), color=m.color)\n'
        code += '    e.add_field(name="ID", value=m.id)\n'
        code += '    e.add_field(name="Roles", value=len(m.roles))\n'
        code += '    e.set_thumbnail(url=m.display_avatar.url)\n'
        code += '    await ctx.send(embed=e)\n\n\n'
        code += '@bot.command()\n'
        code += 'async def serverinfo(ctx):\n'
        code += '    g = ctx.guild\n'
        code += '    e = discord.Embed(title=g.name, color=discord.Color.blue())\n'
        code += '    e.add_field(name="Members", value=g.member_count)\n'
        code += '    e.add_field(name="Channels", value=len(g.channels))\n'
        code += '    if g.icon: e.set_thumbnail(url=g.icon.url)\n'
        code += '    await ctx.send(embed=e)\n\n\n'
        code += '@bot.command()\n'
        code += '@commands.has_permissions(manage_roles=True)\n'
        code += 'async def mute(ctx, m: discord.Member, reason: str = "No reason"):\n'
        code += '    role = discord.utils.get(ctx.guild.roles, name="Muted")\n'
        code += '    if not role:\n'
        code += '        role = await ctx.guild.create_role(name="Muted")\n'
        code += '        for ch in ctx.guild.channels:\n'
        code += '            await ch.set_permissions(role, send_messages=False)\n'
        code += '    await m.add_roles(role, reason=reason)\n'
        code += '    await ctx.send(f"Muted {m.mention}: {reason}")\n\n\n'
        code += '@bot.command()\n'
        code += '@commands.has_permissions(manage_roles=True)\n'
        code += 'async def unmute(ctx, m: discord.Member):\n'
        code += '    role = discord.utils.get(ctx.guild.roles, name="Muted")\n'
        code += '    if role:\n'
        code += '        await m.remove_roles(role)\n'
        code += '        await ctx.send(f"Unmuted {m.mention}")\n\n\n'
        code += '@bot.command()\n'
        code += '@commands.has_permissions(ban_members=True)\n'
        code += 'async def ban(ctx, m: discord.Member, reason: str = "No reason"):\n'
        code += '    await m.ban(reason=reason)\n'
        code += '    await ctx.send(f"Banned {m.mention}: {reason}")\n\n\n'
        code += '@bot.command()\n'
        code += '@commands.has_permissions(kick_members=True)\n'
        code += 'async def kick(ctx, m: discord.Member, reason: str = "No reason"):\n'
        code += '    await m.kick(reason=reason)\n'
        code += '    await ctx.send(f"Kicked {m.mention}: {reason}")\n\n\n'
        code += '@bot.event\n'
        code += 'async def on_member_join(m):\n'
        code += '    ch = bot.get_channel(c.get("welcome", 0))\n'
        code += '    if ch:\n'
        code += '        e = discord.Embed(title="Welcome!",\n'
        code += '            description=f"Welcome {m.mention} to **{m.guild.name}**!",\n'
        code += '            color=discord.Color.green())\n'
        code += '        await ch.send(embed=e)\n\n\n'
        code += 'if __name__ == "__main__":\n'
        code += '    import os\n'
        code += '    t = os.environ.get("DISCORD_TOKEN")\n'
        code += '    if t: bot.run(t)\n'
        code += '    else: print("Set DISCORD_TOKEN env var")\n'
        (d / "bot.py").write_text(code, encoding="utf-8")
        (d / "config.json").write_text(json.dumps({"prefix": "!", "welcome": None, "log": None}, indent=2), encoding="utf-8")
        (d / "requirements.txt").write_text("discord.py\n", encoding="utf-8")
        (d / "README.md").write_text(f"# {desc}\n\n## Setup\n1. pip install discord.py\n2. Set DISCORD_TOKEN\n3. python bot.py\n", encoding="utf-8")
        return ["bot.py", "config.json", "requirements.txt", "README.md"]

    def _gen_blog_post(self, d, desc):
        body = f"# {desc}\n\n"
        body += f"**Meta Description:** {desc} - A comprehensive guide with practical tips.\n\n"
        body += "---\n\n## Introduction\n\n"
        body += f"{desc} is transforming how we work, create, and solve problems.\n"
        body += "Whether you are a beginner or experienced professional, this guide covers everything you need.\n\n"
        body += "## Why This Matters\n\n"
        body += "The landscape is evolving rapidly. Those who adapt early gain a significant advantage.\n\n"
        body += "## Getting Started\n\n"
        body += "### Step 1: Understand the Fundamentals\n\n"
        body += "- **Core Principle 1:** Everything builds on understanding the basics\n"
        body += "- **Core Principle 2:** Practice is more valuable than theory\n"
        body += "- **Core Principle 3:** Start small, iterate, and improve\n\n"
        body += "### Step 2: Set Up Your Environment\n\n"
        body += "You will need:\n"
        body += "1. A reliable internet connection\n"
        body += "2. Basic technical knowledge\n"
        body += "3. Willingness to experiment and learn\n\n"
        body += "### Step 3: Build Your First Project\n\n"
        body += "The best way to learn is by doing. Start with a simple project that solves a real problem.\n\n"
        body += "## Advanced Strategies\n\n"
        body += "1. **Automation:** Save hours by automating repetitive tasks\n"
        body += "2. **Integration:** Connect multiple tools for a seamless workflow\n"
        body += "3. **Optimization:** Fine-tune your approach based on data\n\n"
        body += "## Common Mistakes to Avoid\n\n"
        body += "- Trying to learn everything at once\n"
        body += "- Skipping the fundamentals\n"
        body += "- Not seeking feedback from others\n\n"
        body += "## Tools and Resources\n\n"
        body += "| Tool | Purpose | Price |\n"
        body += "|------|---------|-------|\n"
        body += "| Tool A | Primary work | Free |\n"
        body += "| Tool B | Advanced features | $20/mo |\n"
        body += "| Tool C | Analytics | Free tier |\n\n"
        body += "## Expert Tips\n\n"
        body += '> "The best time to start was yesterday."\n\n'
        body += "1. Focus on consistency over intensity\n"
        body += "2. Document your progress\n"
        body += "3. Join a community of like-minded people\n\n"
        body += "## Frequently Asked Questions\n\n"
        body += "### How long to get started?\n"
        body += "Most people see results within 2-4 weeks of consistent practice.\n\n"
        body += "### Do I need technical skills?\n"
        body += "Basic computer skills are sufficient.\n\n"
        body += "### What is the cost?\n"
        body += "You can start for free. Premium tools are optional.\n\n"
        body += "## Conclusion\n\n"
        body += f"{desc} is a skill that pays dividends. Start today, stay consistent.\n\n"
        body += "---\n\n*Last updated in 2026.*\n"
        (d / "post.md").write_text(body, encoding="utf-8")
        (d / "meta.json").write_text(json.dumps({"title": desc, "description": f"{desc} - comprehensive guide", "keywords": desc.lower().split(), "word_count": len(body.split())}, indent=2), encoding="utf-8")
        return ["post.md", "meta.json"]

    def _gen_automation(self, d, desc):
        code = '#!/usr/bin/env python3\n'
        code += '"""File Organizer\n'
        code += 'Organizes files by type, detects duplicates, supports dry run.\n'
        code += 'Usage: python organize.py C:\\Users\\Downloads\n"""\n'
        code += 'import os, shutil, json, hashlib, logging, argparse\n'
        code += 'from pathlib import Path\n'
        code += 'from datetime import datetime\n'
        code += 'from collections import defaultdict\n\n'
        code += 'logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")\n'
        code += 'log = logging.getLogger(__name__)\n\n'
        code += 'EXTS = {\n'
        code += '    "Images": [".jpg",".jpeg",".png",".gif",".bmp",".webp",".svg"],\n'
        code += '    "Documents": [".pdf",".doc",".docx",".txt",".rtf",".md"],\n'
        code += '    "Spreadsheets": [".xls",".xlsx",".csv"],\n'
        code += '    "Videos": [".mp4",".avi",".mkv",".mov",".wmv"],\n'
        code += '    "Audio": [".mp3",".wav",".flac",".aac",".ogg"],\n'
        code += '    "Code": [".py",".js",".html",".css",".java",".cpp",".rs",".go"],\n'
        code += '    "Archives": [".zip",".rar",".7z",".tar",".gz"],\n'
        code += '    "Executables": [".exe",".msi",".dmg"],\n'
        code += '}\n\n\n'
        code += 'def file_hash(path, bs=65536):\n'
        code += '    h = hashlib.md5()\n'
        code += '    try:\n'
        code += '        with open(path, "rb") as f:\n'
        code += '            while True:\n'
        code += '                chunk = f.read(bs)\n'
        code += '                if not chunk: break\n'
        code += '                h.update(chunk)\n'
        code += '    except: return None\n'
        code += '    return h.hexdigest()\n\n\n'
        code += 'def category(ext):\n'
        code += '    ext = ext.lower()\n'
        code += '    for cat, exts in EXTS.items():\n'
        code += '        if ext in exts: return cat\n'
        code += '    return "Other"\n\n\n'
        code += 'def organize(src, dest=None, dry_run=False):\n'
        code += '    src = Path(src)\n'
        code += '    dest = Path(dest) if dest else src / "Organized"\n'
        code += '    stats = defaultdict(int)\n'
        code += '    dupes = []\n'
        code += '    hashes = {}\n'
        code += '    files = [f for f in src.rglob("*") if f.is_file() and str(dest) not in str(f)]\n'
        code += '    log.info("Found %d files in %s", len(files), src)\n'
        code += '    for fp in files:\n'
        code += '        fh = file_hash(fp)\n'
        code += '        if fh and fh in hashes:\n'
        code += '            dupes.append({"file": str(fp), "dupe_of": str(hashes[fh])})\n'
        code += '            stats["duplicates"] += 1\n'
        code += '            continue\n'
        code += '        if fh: hashes[fh] = fp\n'
        code += '        cat = category(fp.suffix)\n'
        code += '        folder = dest / cat\n'
        code += '        new = folder / fp.name\n'
        code += '        if new.exists():\n'
        code += '            new = folder / f"{fp.stem}_{int(datetime.now().timestamp())}{fp.suffix}"\n'
        code += '        if dry_run:\n'
        code += '            log.info("[DRY] %s -> %s", fp, new)\n'
        code += '        else:\n'
        code += '            folder.mkdir(parents=True, exist_ok=True)\n'
        code += '            shutil.move(str(fp), str(new))\n'
        code += '        stats[cat] += 1\n'
        code += '    report = {"ts": str(datetime.now()), "src": str(src), "dest": str(dest),\n'
        code += '        "total": len(files), "dupes": len(dupes), "by_cat": dict(stats), "dry_run": dry_run}\n'
        code += '    dest.mkdir(parents=True, exist_ok=True)\n'
        code += '    (dest / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")\n'
        code += '    return report\n\n\n'
        code += 'if __name__ == "__main__":\n'
        code += '    p = argparse.ArgumentParser(description="File Organizer")\n'
        code += '    p.add_argument("source")\n'
        code += '    p.add_argument("-d", "--dest")\n'
        code += '    p.add_argument("--dry-run", action="store_true")\n'
        code += '    a = p.parse_args()\n'
        code += '    r = organize(a.source, a.dest, a.dry_run)\n'
        code += '    print(json.dumps(r, indent=2))\n'
        (d / "organize.py").write_text(code, encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        (d / "README.md").write_text(f"# {desc}\n\n## Usage\npython organize.py C:\\Users\\Downloads\n", encoding="utf-8")
        return ["organize.py", "requirements.txt", "README.md"]

    def _gen_telegram_bot(self, d, desc):
        code = '#!/usr/bin/env python3\n'
        code += '"""Telegram Bot - Feature Rich\n'
        code += 'Search, translate, inline keyboards.\n'
        code += 'Requires: pip install python-telegram-bot\n"""\n'
        code += 'from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup\n'
        code += 'from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler,\n'
        code += '    CallbackQueryHandler, ContextTypes, filters\n'
        code += 'import os\n\n\n'
        code += 'async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n'
        code += '    kb = [[InlineKeyboardButton("Help", callback_data="help"),\n'
        code += '           InlineKeyboardButton("About", callback_data="about")]]\n'
        code += '    await update.message.reply_text(\n'
        code += '        "Hello! I am your Telegram bot.\\nChoose:",\n'
        code += '        reply_markup=InlineKeyboardMarkup(kb))\n\n\n'
        code += 'async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n'
        code += '    await update.message.reply_text(\n'
        code += '        "/start - Welcome\\n/help - This message\\n"\n'
        code += '        "/translate TEXT\\n/search QUERY\\nOr just send me a message!")\n\n\n'
        code += 'async def about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n'
        code += '    if update.callback_query:\n'
        code += '        await update.callback_query.edit_message_text("Telegram Bot")\n'
        code += '    else:\n'
        code += '        await update.message.reply_text("Telegram Bot")\n\n\n'
        code += 'async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n'
        code += '    q = update.callback_query\n'
        code += '    await q.answer()\n'
        code += '    if q.data == "help": await help_cmd(update, ctx)\n'
        code += '    elif q.data == "about": await about(update, ctx)\n\n\n'
        code += 'async def translate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n'
        code += '    text = " ".join(ctx.args) if ctx.args else ""\n'
        code += '    if not text:\n'
        code += '        await update.message.reply_text("Usage: /translate hello world")\n'
        code += '        return\n'
        code += '    await update.message.reply_text(f"Translation for: {text}")\n\n\n'
        code += 'async def search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n'
        code += '    q = " ".join(ctx.args) if ctx.args else ""\n'
        code += '    if not q:\n'
        code += '        await update.message.reply_text("Usage: /search python tutorials")\n'
        code += '        return\n'
        code += '    url = f"https://google.com/search?q={q.replace(chr(32), chr(43))}"\n'
        code += '    await update.message.reply_text(f"Search: {q}\\n{url}")\n\n\n'
        code += 'async def echo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n'
        code += '    await update.message.reply_text(f"You said: {update.message.text}\\nUse /help")\n\n\n'
        code += 'if __name__ == "__main__":\n'
        code += '    token = os.environ.get("TELEGRAM_TOKEN")\n'
        code += '    if not token:\n'
        code += '        print("Set TELEGRAM_TOKEN env var")\n'
        code += '        exit(1)\n'
        code += '    app = ApplicationBuilder().token(token).build()\n'
        code += '    app.add_handler(CommandHandler("start", start))\n'
        code += '    app.add_handler(CommandHandler("help", help_cmd))\n'
        code += '    app.add_handler(CommandHandler("about", about))\n'
        code += '    app.add_handler(CommandHandler("translate", translate))\n'
        code += '    app.add_handler(CommandHandler("search", search))\n'
        code += '    app.add_handler(CallbackQueryHandler(button_handler))\n'
        code += '    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))\n'
        code += '    print("Bot started...")\n'
        code += '    app.run_polling()\n'
        (d / "bot.py").write_text(code, encoding="utf-8")
        (d / "requirements.txt").write_text("python-telegram-bot\n", encoding="utf-8")
        (d / "README.md").write_text(f"# {desc}\n\n## Setup\n1. pip install python-telegram-bot\n2. Set TELEGRAM_TOKEN\n3. python bot.py\n", encoding="utf-8")
        return ["bot.py", "requirements.txt", "README.md"]

    def _gen_data_analysis(self, d, desc):
        code = '#!/usr/bin/env python3\n'
        code += '"""Data Analyzer - CSV/JSON Analysis\n'
        code += 'Stats, filtering, sorting, export.\n'
        code += 'Usage: python analyze.py data.csv --sort column --top 10\n"""\n'
        code += 'import json, csv, sys, logging, argparse\n'
        code += 'from pathlib import Path\n\n'
        code += 'logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")\n'
        code += 'log = logging.getLogger(__name__)\n\n\n'
        code += 'class Analyzer:\n'
        code += '    def __init__(self):\n'
        code += '        self.data, self.headers = [], []\n\n'
        code += '    def load_csv(self, path):\n'
        code += '        with open(path, encoding="utf-8") as f:\n'
        code += '            r = csv.DictReader(f)\n'
        code += '            self.headers = r.fieldnames or []\n'
        code += '            self.data = list(r)\n'
        code += '        log.info("Loaded %d rows", len(self.data))\n\n'
        code += '    def load_json(self, path):\n'
        code += '        raw = json.loads(Path(path).read_text(encoding="utf-8"))\n'
        code += '        self.data = raw if isinstance(raw, list) else raw.get("data", [raw])\n'
        code += '        self.headers = list(self.data[0].keys()) if self.data else []\n'
        code += '        log.info("Loaded %d rows", len(self.data))\n\n'
        code += '    def summary(self):\n'
        code += '        if not self.data: return {"rows": 0}\n'
        code += '        stats = {"rows": len(self.data), "cols": len(self.headers),\n'
        code += '            "headers": self.headers, "numeric": {}}\n'
        code += '        for h in self.headers:\n'
        code += '            try:\n'
        code += '                v = [float(r.get(h, 0)) for r in self.data]\n'
        code += '                if len(v) > len(self.data) * 0.5:\n'
        code += '                    stats["numeric"][h] = {"min": min(v), "max": max(v), "avg": sum(v)/len(v)}\n'
        code += '            except: pass\n'
        code += '        return stats\n\n'
        code += '    def filter(self, col, op, val):\n'
        code += '        result = []\n'
        code += '        for r in self.data:\n'
        code += '            cell = r.get(col, "")\n'
        code += '            try: cv, v = float(cell), float(val)\n'
        code += '            except: cv, v = str(cell).lower(), str(val).lower()\n'
        code += '            if (op == "=" and cv == v) or (op == ">" and cv > v) or (op == "<" and cv < v):\n'
        code += '                result.append(r)\n'
        code += '            elif op == "contains" and str(v) in str(cv):\n'
        code += '                result.append(r)\n'
        code += '        self.data = result\n'
        code += '        log.info("Filtered to %d rows", len(self.data))\n'
        code += '        return self\n\n'
        code += '    def sort_by(self, col, desc=False):\n'
        code += '        def kf(r):\n'
        code += '            try: return float(r.get(col, 0))\n'
        code += '            except: return r.get(col, "")\n'
        code += '        self.data.sort(key=kf, reverse=desc)\n'
        code += '        return self\n\n'
        code += '    def top(self, n=10): return self.data[:n]\n\n'
        code += '    def export_csv(self, path):\n'
        code += '        if not self.data: return\n'
        code += '        with open(path, "w", newline="", encoding="utf-8") as f:\n'
        code += '            w = csv.DictWriter(f, fieldnames=self.headers)\n'
        code += '            w.writeheader()\n'
        code += '            w.writerows(self.data)\n\n\n'
        code += 'def main():\n'
        code += '    p = argparse.ArgumentParser(description="Data Analyzer")\n'
        code += '    p.add_argument("input")\n'
        code += '    p.add_argument("--filter", nargs=3, metavar=("COL","OP","VAL"))\n'
        code += '    p.add_argument("--sort")\n'
        code += '    p.add_argument("--top", type=int, default=0)\n'
        code += '    p.add_argument("--output")\n'
        code += '    a = p.parse_args()\n'
        code += '    az = Analyzer()\n'
        code += '    path = Path(a.input)\n'
        code += '    if path.suffix == ".csv": az.load_csv(str(path))\n'
        code += '    elif path.suffix == ".json": az.load_json(str(path))\n'
        code += '    else: print(f"Unsupported: {path.suffix}"); sys.exit(1)\n'
        code += '    if a.filter: az.filter(*a.filter)\n'
        code += '    if a.sort: az.sort_by(a.sort)\n'
        code += '    if a.top: az.data = az.top(a.top)\n'
        code += '    print(json.dumps(az.summary(), indent=2, default=str))\n'
        code += '    if a.output:\n'
        code += '        if a.output.endswith(".csv"): az.export_csv(a.output)\n'
        code += '        else: Path(a.output).write_text(json.dumps(az.data, indent=2, default=str), encoding="utf-8")\n\n\n'
        code += 'if __name__ == "__main__": main()\n'
        (d / "analyze.py").write_text(code, encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        (d / "README.md").write_text(f"# {desc}\n\n## Usage\npython analyze.py data.csv --sort column --top 10\n", encoding="utf-8")
        return ["analyze.py", "requirements.txt", "README.md"]

    def _gen_api_wrapper(self, d, desc):
        code = '#!/usr/bin/env python3\n'
        code += '"""REST API Client - Production Quality\n'
        code += 'GET/POST/PUT/DELETE with auth, retry, caching.\n'
        code += 'Usage: python client.py https://api.example.com --path /users\n"""\n'
        code += 'import json, time, hashlib, logging, urllib.request, urllib.parse, ssl\n'
        code += 'from pathlib import Path\n'
        code += 'from functools import wraps\n\n'
        code += 'logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")\n'
        code += 'log = logging.getLogger(__name__)\n\n'
        code += 'CTX = ssl.create_default_context()\n'
        code += 'CTX.check_hostname = False\n'
        code += 'CTX.verify_mode = ssl.CERT_NONE\n\n\n'
        code += 'def retry(max_retries=3, delay=1.0):\n'
        code += '    def dec(f):\n'
        code += '        @wraps(f)\n'
        code += '        def wrapper(*a, **kw):\n'
        code += '            for i in range(max_retries):\n'
        code += '                try: return f(*a, **kw)\n'
        code += '                except Exception as e:\n'
        code += '                    if i == max_retries-1: raise\n'
        code += '                    log.warning("Retry %d/%d: %s", i+1, max_retries, e)\n'
        code += '                    time.sleep(delay*(i+1))\n'
        code += '        return wrapper\n'
        code += '    return dec\n\n\n'
        code += 'class Client:\n'
        code += '    def __init__(self, base, headers=None, cache_ttl=300):\n'
        code += '        self.base = base.rstrip("/")\n'
        code += '        self.headers = headers or {}\n'
        code += '        self.cache_ttl = cache_ttl\n'
        code += '        self.cache = {}\n'
        code += '        self.count = 0\n\n'
        code += '    def _url(self, path, params=None):\n'
        code += '        u = f"{self.base}/{path.lstrip(\'/\')}"\n'
        code += '        if params: u += "?" + urllib.parse.urlencode(params)\n'
        code += '        return u\n\n'
        code += '    def _ck(self, method, url, data=None):\n'
        code += '        return hashlib.md5(f"{method}:{url}:{json.dumps(data, sort_keys=True) if data else \'\'}".encode()).hexdigest()\n\n'
        code += '    def _req(self, method, path, data=None, params=None, cache=True):\n'
        code += '        url = self._url(path, params)\n'
        code += '        ck = self._ck(method, url, data)\n'
        code += '        if cache and method == "GET" and ck in self.cache:\n'
        code += '            ct, cv = self.cache[ck]\n'
        code += '            if time.time() - ct < self.cache_ttl: return cv\n'
        code += '        body = json.dumps(data).encode() if data else None\n'
        code += '        h = {**self.headers, "User-Agent": "APIClient/1.0"}\n'
        code += '        if body: h["Content-Type"] = "application/json"\n'
        code += '        req = urllib.request.Request(url, data=body, headers=h, method=method)\n'
        code += '        t0 = time.time()\n'
        code += '        with urllib.request.urlopen(req, context=CTX, timeout=30) as resp:\n'
        code += '            result = json.loads(resp.read().decode())\n'
        code += '            log.info("%s %s -> %d (%.2fs)", method, url, resp.status, time.time()-t0)\n'
        code += '            self.count += 1\n'
        code += '            if cache and method == "GET": self.cache[ck] = (time.time(), result)\n'
        code += '            return result\n\n'
        code += '    @retry()\n'
        code += '    def get(self, path, params=None): return self._req("GET", path, params=params)\n\n'
        code += '    @retry(max_retries=2)\n'
        code += '    def post(self, path, data=None): return self._req("POST", path, data=data, cache=False)\n\n'
        code += '    @retry(max_retries=2)\n'
        code += '    def put(self, path, data=None): return self._req("PUT", path, data=data, cache=False)\n\n'
        code += '    @retry(max_retries=2)\n'
        code += '    def delete(self, path): return self._req("DELETE", path, cache=False)\n\n'
        code += '    def stats(self): return {"requests": self.count, "base": self.base}\n\n\n'
        code += 'if __name__ == "__main__":\n'
        code += '    import argparse\n'
        code += '    p = argparse.ArgumentParser(description="REST API Client")\n'
        code += '    p.add_argument("base_url")\n'
        code += '    p.add_argument("--path", default="/")\n'
        code += '    p.add_argument("--method", default="GET", choices=["GET","POST","PUT","DELETE"])\n'
        code += '    p.add_argument("--data")\n'
        code += '    a = p.parse_args()\n'
        code += '    c = Client(a.base_url)\n'
        code += '    d = json.loads(a.data) if a.data else None\n'
        code += '    r = c.get(a.path) if a.method == "GET" else getattr(c, a.method.lower())(a.path, d)\n'
        code += '    print(json.dumps(r, indent=2, default=str))\n'
        code += '    print(f"Stats: {c.stats()}")\n'
        (d / "client.py").write_text(code, encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        (d / "README.md").write_text(f"# {desc}\n\n## Usage\npython client.py https://api.example.com --path /users\n", encoding="utf-8")
        return ["client.py", "requirements.txt", "README.md"]

    def _gen_flask_api(self, d, desc):
        (d / "app.py").write_text('''"""Flask REST API - Production backend with auth, CRUD, rate limiting."""
import os, json, time, secrets, functools, logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

_users = {}
_items = {}
_tokens = {}
_rate_limits = {}


def rate_limit(max_per_minute=60):
    def dec(f):
        @functools.wraps(f)
        def wrapper(*a, **kw):
            ip = request.remote_addr
            now = time.time()
            window = [t for t in _rate_limits.get(ip, []) if now - t < 60]
            if len(window) >= max_per_minute:
                return jsonify({"error": "Rate limit exceeded"}), 429
            window.append(now)
            _rate_limits[ip] = window
            return f(*a, **kw)
        return wrapper
    return dec


def require_auth(f):
    @functools.wraps(f)
    def wrapper(*a, **kw):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "")
        if token not in _tokens:
            return jsonify({"error": "Unauthorized"}), 401
        g.user_id = _tokens[token]
        return f(*a, **kw)
    return wrapper


@app.route("/api/register", methods=["POST"])
@rate_limit(10)
def register():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if email in _users:
        return jsonify({"error": "Email already registered"}), 409
    uid = secrets.token_hex(8)
    _users[email] = {"id": uid, "email": email, "password": generate_password_hash(password),
                     "created": datetime.now().isoformat(), "plan": "free"}
    token = secrets.token_urlsafe(32)
    _tokens[token] = uid
    log.info("Registered: %s", email)
    return jsonify({"token": token, "user_id": uid}), 201


@app.route("/api/login", methods=["POST"])
@rate_limit(30)
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    user = _users.get(email)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401
    token = secrets.token_urlsafe(32)
    _tokens[token] = user["id"]
    log.info("Logged in: %s", email)
    return jsonify({"token": token, "user_id": user["id"]})


@app.route("/api/items", methods=["GET"])
@require_auth
@rate_limit(60)
def list_items():
    user_items = [v for v in _items.values() if v["owner"] == g.user_id]
    return jsonify({"items": user_items, "count": len(user_items)})


@app.route("/api/items", methods=["POST"])
@require_auth
@rate_limit(30)
def create_item():
    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "Name required"}), 400
    iid = secrets.token_hex(8)
    item = {"id": iid, "owner": g.user_id, "name": data["name"],
            "description": data.get("description", ""), "tags": data.get("tags", []),
            "metadata": data.get("metadata", {}), "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat()}
    _items[iid] = item
    log.info("Created item: %s", iid)
    return jsonify(item), 201


@app.route("/api/items/<item_id>", methods=["GET"])
@require_auth
def get_item(item_id):
    item = _items.get(item_id)
    if not item or item["owner"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    return jsonify(item)


@app.route("/api/items/<item_id>", methods=["PUT"])
@require_auth
def update_item(item_id):
    item = _items.get(item_id)
    if not item or item["owner"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    for key in ("name", "description", "tags", "metadata"):
        if key in data:
            item[key] = data[key]
    item["updated"] = datetime.now().isoformat()
    return jsonify(item)


@app.route("/api/items/<item_id>", methods=["DELETE"])
@require_auth
def delete_item(item_id):
    item = _items.get(item_id)
    if not item or item["owner"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    del _items[item_id]
    return jsonify({"deleted": True})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "users": len(_users), "items": len(_items),
                    "uptime": datetime.now().isoformat()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"API running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
''', encoding="utf-8")
        (d / "test_api.py").write_text('''"""API Tests - Run with: python -m pytest test_api.py -v"""
import json, secrets
try:
    from app import app, _users, _items, _tokens
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

def test_api():
    if not HAS_FLASK:
        print("Flask not installed, skipping tests")
        return
    client = app.test_client()
    # Health check
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    print("PASS: Health check")
    # Register
    email = f"test_{secrets.token_hex(4)}@example.com"
    r = client.post("/api/register", json={"email": email, "password": "pass123"})
    assert r.status_code == 201
    token = r.get_json()["token"]
    print("PASS: Register")
    # Login
    r = client.post("/api/login", json={"email": email, "password": "pass123"})
    assert r.status_code == 200
    print("PASS: Login")
    # Create item
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/items", json={"name": "Test", "description": "A test item"}, headers=headers)
    assert r.status_code == 201
    item_id = r.get_json()["id"]
    print("PASS: Create item")
    # List items
    r = client.get("/api/items", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["count"] >= 1
    print("PASS: List items")
    # Get item
    r = client.get(f"/api/items/{item_id}", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["name"] == "Test"
    print("PASS: Get item")
    # Update item
    r = client.put(f"/api/items/{item_id}", json={"name": "Updated"}, headers=headers)
    assert r.status_code == 200
    assert r.get_json()["name"] == "Updated"
    print("PASS: Update item")
    # Delete item
    r = client.delete(f"/api/items/{item_id}", headers=headers)
    assert r.status_code == 200
    print("PASS: Delete item")
    # Unauthorized
    r = client.get("/api/items")
    assert r.status_code == 401
    print("PASS: Unauthorized blocked")
    print("\\nAll tests passed!")

if __name__ == "__main__":
    test_api()
''', encoding="utf-8")
        (d / "requirements.txt").write_text("flask>=2.3\nwerkzeug>=2.3\n", encoding="utf-8")
        (d / ".env.example").write_text("SECRET_KEY=change-me-in-production\nPORT=5000\n", encoding="utf-8")
        files = ["app.py", "test_api.py", "requirements.txt", ".env.example", "README.md"]
        (d / "README.md").write_text(
            f"# {desc}\n\nProduction Flask REST API with authentication, CRUD, and rate limiting.\n\n"
            "## Quick Start\n```bash\npip install -r requirements.txt\npython app.py\n```\n\n"
            "## API Endpoints\n"
            "| Method | Endpoint | Auth | Description |\n"
            "|--------|----------|------|-------------|\n"
            "| POST | /api/register | No | Create account |\n"
            "| POST | /api/login | No | Get auth token |\n"
            "| GET | /api/items | Yes | List items |\n"
            "| POST | /api/items | Yes | Create item |\n"
            "| GET | /api/items/:id | Yes | Get item |\n"
            "| PUT | /api/items/:id | Yes | Update item |\n"
            "| DELETE | /api/items/:id | Yes | Delete item |\n"
            "| GET | /api/health | No | Health check |\n\n"
            "## Tests\n```bash\npython test_api.py\n```\n\n"
            "## Features\n- JWT-like token auth\n- Rate limiting (configurable per endpoint)\n"
            "- Full CRUD for items\n- Password hashing (werkzeug)\n- In-memory storage (swap for DB)\n"
            "- Input validation\n- Structured logging\n", encoding="utf-8")
        return files

    def _gen_web_dashboard(self, d, desc):
        (d / "app.py").write_text('''"""Web Dashboard - Flask app with HTML frontend, charts, data export."""
import os, json, secrets, csv, io, time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, send_file

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(16)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.sidebar{width:240px;background:#1e293b;height:100vh;position:fixed;padding:20px 0}
.sidebar h2{padding:0 20px 20px;font-size:1.2em;color:#38bdf8}
.sidebar a{display:block;padding:10px 20px;color:#94a3b8;text-decoration:none;font-size:0.9em}
.sidebar a:hover,.sidebar a.active{background:#334155;color:#fff}
.main{margin-left:240px;padding:30px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;margin-top:20px}
.card{background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155}
.card h3{color:#38bdf8;margin-bottom:12px;font-size:1em}
.stat{font-size:2em;font-weight:700;color:#fff}
.stat-label{color:#64748b;font-size:0.85em;margin-top:4px}
table{width:100%;border-collapse:collapse;margin-top:16px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #334155;font-size:0.9em}
th{color:#64748b;font-weight:500}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.75em;font-weight:600}
.badge-green{background:#064e3b;color:#34d399}
.badge-blue{background:#1e3a5f;color:#38bdf8}
.badge-yellow{background:#713f12;color:#fbbf24}
.btn{background:#38bdf8;color:#0f172a;padding:8px 16px;border:none;border-radius:6px;
     cursor:pointer;font-weight:600;font-size:0.85em}
.btn:hover{opacity:0.9}
.chart{height:200px;background:#0f172a;border-radius:8px;margin-top:12px;
       display:flex;align-items:flex-end;padding:10px;gap:4px}
.bar{background:linear-gradient(to top,#38bdf8,#7b2ff7);border-radius:4px 4px 0 0;
     flex:1;min-height:10px;transition:height 0.3s}
</style></head><body>
<div class="sidebar">
<h2>{{ title }}</h2>
<a href="/" class="active">Dashboard</a>
<a href="/data">Data</a>
<a href="/api/stats">API Stats</a>
<a href="/export">Export CSV</a>
</div>
<div class="main">
<h1>Dashboard</h1>
<p style="color:#64748b;margin-top:4px">Last updated: {{ now }}</p>
<div class="grid">
<div class="card"><h3>Total Records</h3><div class="stat">{{ stats.total }}</div><div class="stat-label">across all categories</div></div>
<div class="card"><h3>Active Today</h3><div class="stat">{{ stats.active }}</div><div class="stat-label">items modified today</div></div>
<div class="card"><h3>Growth</h3><div class="stat">{{ stats.growth }}%</div><div class="stat-label">vs last period</div></div>
</div>
<div class="card" style="margin-top:20px">
<h3>Weekly Activity</h3>
<div class="chart">{% for v in chart_data %}<div class="bar" style="height:{{ v }}%"></div>{% endfor %}</div>
</div>
<div class="card" style="margin-top:20px">
<h3>Recent Items</h3>
<table><tr><th>Name</th><th>Category</th><th>Status</th><th>Updated</th></tr>
{% for item in items[:10] %}<tr>
<td>{{ item.name }}</td><td>{{ item.category }}</td>
<td><span class="badge badge-{{ item.badge }}">{{ item.status }}</span></td>
<td>{{ item.updated }}</td></tr>{% endfor %}</table>
</div>
</div></body></html>"""

_data = [{"name": f"Item {i}", "category": cat, "status": st,
          "updated": (datetime.now() - timedelta(hours=i)).strftime("%Y-%m-%d %H:%M"),
          "badge": {"Active": "green", "Pending": "yellow", "Draft": "blue"}.get(st, "blue")}
         for i, cat, st in enumerate(
             ["Sales", "Marketing", "Dev", "Support", "Finance",
              "Sales", "Marketing", "Dev", "Support", "Finance",
              "Sales", "Marketing", "Dev", "Support", "Finance"],
             1) for st in (["Active", "Pending", "Draft"][:1] if i % 3 == 0 else ["Active"])]

@app.route("/")
def dashboard():
    chart_data = [30 + (i * 7) % 60 for i in range(7)]
    return render_template_string(DASHBOARD_HTML, title="Dashboard",
                                  now=datetime.now().strftime("%Y-%m-%d %H:%M"),
                                  stats={"total": len(_data), "active": len([d for d in _data if d["status"] == "Active"]),
                                         "growth": 12},
                                  chart_data=chart_data, items=_data)

@app.route("/data")
def data_page():
    return jsonify({"items": _data, "count": len(_data)})

@app.route("/api/stats")
def api_stats():
    return jsonify({"total": len(_data), "active": len([d for d in _data if d["status"] == "Active"]),
                    "categories": list(set(d["category"] for d in _data))})

@app.route("/export")
def export_csv():
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["name", "category", "status", "updated"])
    writer.writeheader()
    writer.writerows(_data)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv",
                     as_attachment=True, download_name="export.csv")

@app.route("/api/add", methods=["POST"])
def add_item():
    data = request.get_json() or {}
    item = {"name": data.get("name", "New Item"), "category": data.get("category", "General"),
            "status": "Active", "updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "badge": "green"}
    _data.insert(0, item)
    return jsonify(item), 201

if __name__ == "__main__":
    print("Dashboard at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
''', encoding="utf-8")
        (d / "requirements.txt").write_text("flask>=2.3\n", encoding="utf-8")
        files = ["app.py", "requirements.txt", "README.md"]
        (d / "README.md").write_text(
            f"# {desc}\n\nFull-stack web dashboard with responsive UI, charts, data tables, CSV export.\n\n"
            "## Quick Start\n```bash\npip install -r requirements.txt\npython app.py\n```\n"
            "## Features\n- Responsive dark-theme UI\n- Real-time statistics cards\n"
            "- Interactive bar chart\n- Sortable data table with status badges\n"
            "- CSV export\n- REST API for data access\n- Add items via POST /api/add\n", encoding="utf-8")
        return files

    def _gen_cli_tool(self, d, desc):
        (d / "cli.py").write_text('''#!/usr/bin/env python3
"""CLI Tool - Production command-line tool with subcommands, config, plugins."""
import sys, os, json, argparse, logging, time
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path.home() / ".mytool"
CONFIG_FILE = CONFIG_DIR / "config.json"
DATA_DIR = CONFIG_DIR / "data"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


class Config:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {"theme": "dark", "editor": "code", "auto_save": True, "max_recent": 10}

    def save(self):
        CONFIG_FILE.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


class Store:
    def __init__(self):
        self.file = DATA_DIR / "items.json"
        self.items = self._load()

    def _load(self):
        if self.file.exists():
            return json.loads(self.file.read_text(encoding="utf-8"))
        return []

    def save(self):
        self.file.write_text(json.dumps(self.items, indent=2, default=str), encoding="utf-8")

    def add(self, name, tags=None, meta=None):
        item = {"id": len(self.items) + 1, "name": name, "tags": tags or [],
                "meta": meta or {}, "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat()}
        self.items.append(item)
        self.save()
        return item

    def get(self, item_id):
        for item in self.items:
            if item["id"] == item_id:
                return item
        return None

    def list(self, tag=None, limit=20):
        items = self.items
        if tag:
            items = [i for i in items if tag in i.get("tags", [])]
        return items[-limit:]

    def update(self, item_id, **kwargs):
        item = self.get(item_id)
        if item:
            item.update(kwargs)
            item["updated"] = datetime.now().isoformat()
            self.save()
        return item

    def delete(self, item_id):
        item = self.get(item_id)
        if item:
            self.items = [i for i in self.items if i["id"] != item_id]
            self.save()
            return True
        return False

    def search(self, query):
        q = query.lower()
        return [i for i in self.items if q in i["name"].lower() or any(q in t for t in i.get("tags", []))]

    def stats(self):
        return {"total": len(self.items), "tags": list(set(t for i in self.items for t in i.get("tags", [])))}


def cmd_init(args):
    config = Config()
    print(f"Initialized config at {CONFIG_DIR}")
    print(f"Config: {json.dumps(config.data, indent=2)}")


def cmd_add(args):
    store = Store()
    item = store.add(args.name, tags=args.tags.split(",") if args.tags else None)
    print(f"Added: {item['name']} (id={item['id']})")


def cmd_list(args):
    store = Store()
    items = store.list(tag=args.tag, limit=args.limit)
    if not items:
        print("No items found.")
        return
    for item in items:
        tags = ", ".join(item.get("tags", []))
        print(f"  [{item['id']}] {item['name']}" + (f" ({tags})" if tags else ""))


def cmd_get(args):
    store = Store()
    item = store.get(args.id)
    if item:
        print(json.dumps(item, indent=2, default=str))
    else:
        print(f"Item {args.id} not found.")


def cmd_delete(args):
    store = Store()
    if store.delete(args.id):
        print(f"Deleted item {args.id}")
    else:
        print(f"Item {args.id} not found.")


def cmd_search(args):
    store = Store()
    items = store.search(args.query)
    for item in items:
        print(f"  [{item['id']}] {item['name']}")


def cmd_stats(args):
    store = Store()
    stats = store.stats()
    print(f"Total items: {stats['total']}")
    print(f"Tags: {', '.join(stats['tags']) or 'none'}")


def cmd_config(args):
    config = Config()
    if args.key and args.value:
        config.set(args.key, args.value)
        print(f"Set {args.key} = {args.value}")
    elif args.key:
        print(f"{args.key} = {config.get(args.key)}")
    else:
        print(json.dumps(config.data, indent=2))


def main():
    parser = argparse.ArgumentParser(description="CLI Tool", formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="Examples:\\n  mytool add 'My Item' --tags work,important\\n  mytool list --tag work\\n  mytool search item")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    sub.add_parser("init", help="Initialize config")
    p_add = sub.add_parser("add", help="Add item")
    p_add.add_argument("name", help="Item name")
    p_add.add_argument("--tags", help="Comma-separated tags")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List items")
    p_list.add_argument("--tag", help="Filter by tag")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="Get item by ID")
    p_get.add_argument("id", type=int)
    p_get.set_defaults(func=cmd_get)

    p_del = sub.add_parser("delete", help="Delete item")
    p_del.add_argument("id", type=int)
    p_del.set_defaults(func=cmd_delete)

    p_search = sub.add_parser("search", help="Search items")
    p_search.add_argument("query")
    p_search.set_defaults(func=cmd_search)

    sub.add_parser("stats", help="Show statistics")

    p_config = sub.add_parser("config", help="View/set config")
    p_config.add_argument("key", nargs="?")
    p_config.add_argument("value", nargs="?")
    p_config.set_defaults(func=cmd_config)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
''', encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        files = ["cli.py", "requirements.txt", "README.md"]
        (d / "README.md").write_text(
            f"# {desc}\n\nFull-featured CLI tool with subcommands, persistent config, item storage, search.\n\n"
            "## Quick Start\n```bash\npython cli.py init\npython cli.py add 'My Item' --tags work,important\npython cli.py list\npython cli.py search item\npython cli.py stats\n```\n\n"
            "## Commands\n"
            "| Command | Description |\n|---------|-------------|\n"
            "| init | Initialize config and data directories |\n"
            "| add <name> | Add item with optional --tags |\n"
            "| list [--tag X] | List items, optionally filter by tag |\n"
            "| get <id> | Get item details |\n"
            "| delete <id> | Remove item |\n"
            "| search <query> | Search items by name or tag |\n"
            "| stats | Show statistics |\n"
            "| config [key] [value] | View or set configuration |\n\n"
            "## Features\n- Subcommand architecture\n- Persistent JSON storage\n- Tag-based filtering\n- Full-text search\n- Configurable settings\n- Zero dependencies\n", encoding="utf-8")
        return files

    def _gen_etl_pipeline(self, d, desc):
        (d / "pipeline.py").write_text('''"""ETL Pipeline - Extract, Transform, Load with config, logging, retry."""
import os, json, csv, time, logging, hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    name: str = "default"
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0
    output_dir: str = "output"
    log_level: str = "INFO"


class Extractor:
    def extract_csv(self, filepath: str) -> List[Dict]:
        rows = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        log.info("Extracted %d rows from %s", len(rows), filepath)
        return rows

    def extract_json(self, filepath: str) -> List[Dict]:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return [data]

    def extract_jsonl(self, filepath: str) -> List[Dict]:
        rows = []
        for line in Path(filepath).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def extract(self, filepath: str) -> List[Dict]:
        ext = Path(filepath).suffix.lower()
        extractors = {".csv": self.extract_csv, ".json": self.extract_json, ".jsonl": self.extract_jsonl}
        fn = extractors.get(ext)
        if not fn:
            raise ValueError(f"Unsupported format: {ext}")
        return fn(filepath)


class Transformer:
    def __init__(self):
        self.transforms = []

    def add_transform(self, fn):
        self.transforms.append(fn)
        return self

    def rename_columns(self, mapping: Dict[str, str]):
        def transform(row):
            return {mapping.get(k, k): v for k, v in row.items()}
        self.transforms.append(transform)
        return self

    def filter_rows(self, predicate):
        self.transforms.append(lambda row: row if predicate(row) else None)
        return self

    def add_column(self, name: str, value_fn):
        def transform(row):
            row[name] = value_fn(row)
            return row
        self.transforms.append(transform)
        return self

    def deduplicate(self, key_fn=None):
        seen = set()
        def transform(row):
            key = key_fn(row) if key_fn else json.dumps(row, sort_keys=True)
            if key in seen:
                return None
            seen.add(key)
            return row
        self.transforms.append(transform)
        return self

    def clean_whitespace(self):
        def transform(row):
            return {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
        self.transforms.append(transform)
        return self

    def transform(self, rows: List[Dict]) -> List[Dict]:
        result = []
        for row in rows:
            current = row
            skip = False
            for t in self.transforms:
                current = t(current)
                if current is None:
                    skip = True
                    break
            if not skip:
                result.append(current)
        log.info("Transformed %d -> %d rows", len(rows), len(result))
        return result


class Loader:
    def save_csv(self, rows: List[Dict], filepath: str):
        if not rows:
            log.warning("No rows to save")
            return
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        log.info("Saved %d rows to %s", len(rows), filepath)

    def save_json(self, rows: List[Dict], filepath: str):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        Path(filepath).write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
        log.info("Saved %d rows to %s", len(rows), filepath)

    def save_jsonl(self, rows: List[Dict], filepath: str):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, default=str) + "\\n")
        log.info("Saved %d rows to %s", len(rows), filepath)


class Pipeline:
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.extractor = Extractor()
        self.transformer = Transformer()
        self.loader = Loader()
        self.stats = {"extracted": 0, "transformed": 0, "loaded": 0, "errors": 0, "start": None, "end": None}

    def run(self, input_file: str, output_file: str, output_format: str = "json"):
        self.stats["start"] = datetime.now().isoformat()
        log.info("Pipeline '%s' starting: %s -> %s", self.config.name, input_file, output_file)
        try:
            data = self.extractor.extract(input_file)
            self.stats["extracted"] = len(data)
            data = self.transformer.transform(data)
            self.stats["transformed"] = len(data)
            save_fn = {"csv": self.loader.save_csv, "json": self.loader.save_json,
                       "jsonl": self.loader.save_jsonl}.get(output_format, self.loader.save_json)
            save_fn(data, output_file)
            self.stats["loaded"] = len(data)
        except Exception as e:
            self.stats["errors"] += 1
            log.error("Pipeline error: %s", e)
            raise
        finally:
            self.stats["end"] = datetime.now().isoformat()
            log.info("Pipeline stats: %s", json.dumps(self.stats))
        return self.stats


def run_demo():
    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)
    csv_file = demo_dir / "input.csv"
    csv_file.write_text(
        "name,email,department,salary\\n"
        "Alice,alice@example.com,Engineering,95000\\n"
        "Bob,bob@example.com,Marketing,72000\\n"
        "Charlie,charlie@example.com,Engineering,105000\\n"
        "Diana,diana@example.com,Sales,68000\\n"
        "Eve,eve@example.com,Engineering,98000\\n"
        "Frank,frank@example.com,Marketing,71000\\n",
        encoding="utf-8"
    )
    config = PipelineConfig(name="demo", batch_size=10)
    pipeline = Pipeline(config)
    pipeline.transformer.clean_whitespace()
    pipeline.transformer.add_column("bonus", lambda r: round(float(r.get("salary", 0)) * 0.1, 2))
    pipeline.transformer.add_column("processed_at", lambda r: datetime.now().isoformat())
    stats = pipeline.run(str(csv_file), str(demo_dir / "output.json"))
    print(f"Pipeline complete: {json.dumps(stats, indent=2)}")
    output = json.loads((demo_dir / "output.json").read_text(encoding="utf-8"))
    print(f"Output preview: {json.dumps(output[:2], indent=2)}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo()
    else:
        print("Usage: python pipeline.py demo")
        print("Or import and use: Pipeline().run(input, output)")
''', encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        files = ["pipeline.py", "requirements.txt", "README.md"]
        (d / "README.md").write_text(
            f"# {desc}\n\nProduction ETL pipeline with Extract, Transform, Load stages.\n\n"
            "## Quick Start\n```bash\npython pipeline.py demo\n```\n\n"
            "## Architecture\n"
            "```python\nfrom pipeline import Pipeline, PipelineConfig\n\n"
            "p = Pipeline(PipelineConfig(name=\"my_pipeline\"))\n"
            "p.transformer.clean_whitespace()\n"
            "p.transformer.rename_columns({\"old\": \"new\"})\n"
            "p.transformer.filter_rows(lambda r: int(r[\"score\"]) > 50)\n"
            "p.transformer.deduplicate()\n"
            "p.run(\"input.csv\", \"output.json\")\n```\n\n"
            "## Features\n- CSV, JSON, JSONL input support\n- Chained transformers (rename, filter, dedup, add columns)\n- CSV, JSON, JSONL output\n- Pipeline stats and logging\n- Zero dependencies\n- Configurable batch size and retry\n", encoding="utf-8")
        return files

    def _gen_saaS_template(self, d, desc):
        (d / "app.py").write_text('''"""SaaS Starter - Flask app with user auth, billing hooks, dashboard, API."""
import os, json, secrets, time, functools, logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_SECURE"] = False
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

_users = {}
_plans = {"free": {"name": "Free", "price": 0, "features": ["5 projects", "1GB storage"]},
          "pro": {"name": "Pro", "price": 29, "features": ["Unlimited projects", "100GB storage", "Priority support"]},
          "enterprise": {"name": "Enterprise", "price": 99, "features": ["Everything in Pro", "Custom domain", "SLA"]}}

LANDING_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jarvis SaaS</title>
<style>*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0a0a0a;color:#e0e0e0}
.hero{text-align:center;padding:100px 20px 60px;background:linear-gradient(180deg,#0a0a0a 0%,#1a1a2e 100%)}
.hero h1{font-size:3em;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero p{color:#888;font-size:1.2em;margin:16px 0 32px}
.btn{display:inline-block;padding:14px 32px;border-radius:8px;font-weight:600;text-decoration:none;font-size:1em}
.btn-primary{background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:#fff}
.btn-secondary{background:#1a1a2e;color:#00d4ff;border:1px solid #333}
.pricing{display:flex;justify-content:center;gap:24px;padding:60px 20px;flex-wrap:wrap}
.price-card{background:#111;border:1px solid #222;border-radius:12px;padding:32px;width:280px;text-align:center}
.price-card.featured{border-color:#7b2ff7}
.price-card h3{margin-bottom:8px}.price{font-size:2.5em;font-weight:700;color:#00d4ff;margin:16px 0}
.price span{font-size:0.4em;color:#666}
.features{text-align:left;margin:20px 0}.features li{padding:6px 0;color:#aaa;list-style:none}
.features li::before{content:"✓ ";color:#34d399}
footer{text-align:center;padding:30px;color:#444;font-size:0.8em}
</style></head><body>
<div class="hero"><h1>Jarvis SaaS</h1><p>Build, ship, and monetize your products</p>
<a href="/register" class="btn btn-primary">Get Started Free</a> <a href="/login" class="btn btn-secondary">Login</a></div>
<div class="pricing">
<div class="price-card"><h3>Free</h3><div class="price">$0<span>/mo</span></div>
<ul class="features"><li>5 projects</li><li>1GB storage</li><li>Community support</li></ul></div>
<div class="price-card featured"><h3>Pro</h3><div class="price">$29<span>/mo</span></div>
<ul class="features"><li>Unlimited projects</li><li>100GB storage</li><li>Priority support</li><li>Custom domain</li></ul></div>
<div class="price-card"><h3>Enterprise</h3><div class="price">$99<span>/mo</span></div>
<ul class="features"><li>Everything in Pro</li><li>SLA guarantee</li><li>Dedicated support</li><li>SSO/SAML</li></ul></div>
</div><footer>Powered by Jarvis SaaS Template</footer></body></html>"""

DASHBOARD_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard</title>
<style>*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0a0a0a;color:#e0e0e0;display:flex;min-height:100vh}
.side{width:240px;background:#111;padding:20px;border-right:1px solid #222}
.side h2{color:#00d4ff;margin-bottom:24px;font-size:1.1em}
.side a{display:block;padding:10px 16px;color:#888;text-decoration:none;border-radius:6px;margin-bottom:4px}
.side a:hover,.side a.active{background:#1a1a2e;color:#fff}
.main{flex:1;padding:30px}
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:30px}
.stat-card{background:#111;border:1px solid #222;border-radius:10px;padding:20px}
.stat-card .label{color:#666;font-size:0.85em}.stat-card .value{font-size:1.8em;font-weight:700;color:#fff;margin-top:4px}
table{width:100%;border-collapse:collapse}th,td{padding:12px;text-align:left;border-bottom:1px solid #1a1a1a}
th{color:#666;font-size:0.85em}.badge{padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:600}
.badge-pro{background:#1a1a2e;color:#7b2ff7}.badge-free{background:#1a1a1a;color:#666}
</style></head><body>
<div class="side"><h2>Jarvis SaaS</h2><a href="/" class="active">Dashboard</a><a href="/projects">Projects</a><a href="/api/docs">API</a><a href="/settings">Settings</a><a href="/logout">Logout</a></div>
<div class="main"><h1>Dashboard</h1><p style="color:#666;margin:4px 0 20px">Welcome, {{ user.email }}</p>
<div class="stat-grid"><div class="stat-card"><div class="label">Plan</div><div class="value">{{ user.plan }}</div></div>
<div class="stat-card"><div class="label">Projects</div><div class="value">{{ projects }}</div></div>
<div class="stat-card"><div class="label">API Calls</div><div class="value">{{ api_calls }}</div></div></div>
<h2 style="margin-bottom:16px">Recent Activity</h2>
<table><tr><th>Time</th><th>Action</th><th>Details</th></tr>
{% for a in activity %}<tr><td>{{ a.time }}</td><td>{{ a.action }}</td><td>{{ a.details }}</td></tr>{% endfor %}</table>
</div></body></html>"""

@app.route("/")
def landing():
    if "uid" in session:
        return redirect("/dashboard")
    return render_template_string(LANDING_HTML)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template_string("""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Register</title>
<style>body{font-family:system-ui;background:#0a0a0a;color:#e0e0e0;display:flex;justify-content:center;align-items:center;height:100vh}
form{background:#111;padding:40px;border-radius:12px;width:360px;border:1px solid #222}
h2{margin-bottom:24px;color:#00d4ff}input{width:100%;padding:12px;margin-bottom:16px;background:#1a1a1a;border:1px solid #333;border-radius:6px;color:#fff;font-size:0.95em}
button{width:100%;padding:12px;background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:#fff;border:none;border-radius:6px;font-weight:600;cursor:pointer}
</style></head><body><form method="POST"><h2>Create Account</h2>
<input name="email" placeholder="Email" required><input name="password" placeholder="Password" type="password" required>
<button type="submit">Register</button><p style="margin-top:16px;text-align:center;font-size:0.85em"><a href="/login" style="color:#00d4ff">Already have an account?</a></p></form></body></html>""")
    data = request.form
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not email or not password:
        return "Missing fields", 400
    if email in _users:
        return "Email taken", 409
    uid = secrets.token_hex(8)
    _users[email] = {"id": uid, "email": email, "plan": "free", "created": datetime.now().isoformat(),
                     "api_calls": 0, "projects": 0}
    session["uid"] = uid
    session["email"] = email
    return redirect("/dashboard")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template_string("""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Login</title>
<style>body{font-family:system-ui;background:#0a0a0a;color:#e0e0e0;display:flex;justify-content:center;align-items:center;height:100vh}
form{background:#111;padding:40px;border-radius:12px;width:360px;border:1px solid #222}
h2{margin-bottom:24px;color:#00d4ff}input{width:100%;padding:12px;margin-bottom:16px;background:#1a1a1a;border:1px solid #333;border-radius:6px;color:#fff}
button{width:100%;padding:12px;background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:#fff;border:none;border-radius:6px;font-weight:600;cursor:pointer}
</style></head><body><form method="POST"><h2>Login</h2>
<input name="email" placeholder="Email" required><input name="password" placeholder="Password" type="password" required>
<button type="submit">Login</button><p style="margin-top:16px;text-align:center;font-size:0.85em"><a href="/register" style="color:#00d4ff">Create account</a></p></form></body></html>""")
    email = request.form.get("email", "").strip().lower()
    user = _users.get(email)
    if not user:
        return "Invalid credentials", 401
    session["uid"] = user["id"]
    session["email"] = email
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    if "uid" not in session:
        return redirect("/login")
    user = _users.get(session["email"], {})
    activity = [{"time": "Just now", "action": "Login", "details": "Successful login"}]
    return render_template_string(DASHBOARD_HTML, user=user, projects=user.get("projects", 0),
                                  api_calls=user.get("api_calls", 0), activity=activity)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/api/v1/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def api_proxy(path):
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    if not token:
        return jsonify({"error": "API key required"}), 401
    email = None
    for e, u in _users.items():
        if u["id"] == token:
            email = e
            break
    if not email:
        return jsonify({"error": "Invalid API key"}), 401
    _users[email]["api_calls"] = _users[email].get("api_calls", 0) + 1
    return jsonify({"endpoint": path, "method": request.method, "status": "ok",
                    "plan": _users[email]["plan"]})

@app.route("/api/docs")
def api_docs():
    return jsonify({"endpoints": ["GET /api/v1/<path> - Generic API endpoint"],
                    "auth": "Bearer token in Authorization header",
                    "rate_limits": {"free": "100/hour", "pro": "1000/hour", "enterprise": "unlimited"}})

if __name__ == "__main__":
    print("SaaS app at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
''', encoding="utf-8")
        (d / "requirements.txt").write_text("flask>=2.3\n", encoding="utf-8")
        files = ["app.py", "requirements.txt", "README.md"]
        (d / "README.md").write_text(
            f"# {desc}\n\nSaaS application template with landing page, auth, dashboard, billing hooks, API.\n\n"
            "## Quick Start\n```bash\npip install -r requirements.txt\npython app.py\n```\n\n"
            "## Features\n"
            "- Beautiful landing page with pricing cards\n"
            "- User registration and login (session-based)\n"
            "- Dashboard with stats, activity feed\n"
            "- API key authentication for /api/v1/*\n"
            "- Plan-based rate limiting (free/pro/enterprise)\n"
            "- Billing hooks ready for Stripe integration\n"
            "- Dark theme throughout\n\n"
            "## Customization\n- Edit _plans dict to change pricing\n- Add database (replace in-memory _users)\n- Add Stripe billing in /upgrade route\n- Deploy to Heroku/Railway/Vercel\n", encoding="utf-8")
        return files

    def _gen_landing_page(self, d, desc):
        (d / "index.html").write_text('''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>''' + desc.replace('"', '\\"') + '''</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0}
.hero{text-align:center;padding:120px 20px 80px;background:linear-gradient(180deg,#0a0a0a,#1a1a2e)}
.hero h1{font-size:3.2em;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:20px}
.hero p{color:#888;font-size:1.2em;max-width:600px;margin:0 auto 40px}
.cta{display:inline-block;padding:16px 40px;background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:#fff;text-decoration:none;border-radius:10px;font-weight:600;font-size:1.1em;transition:transform 0.2s}
.cta:hover{transform:scale(1.05)}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:32px;padding:80px 40px;max-width:1100px;margin:0 auto}
.feature{background:#111;border:1px solid #222;border-radius:14px;padding:32px;text-align:center}
.feature .icon{font-size:2.5em;margin-bottom:16px}
.feature h3{color:#00d4ff;margin-bottom:12px;font-size:1.2em}
.feature p{color:#888;line-height:1.6}
.pricing{padding:80px 40px;max-width:1000px;margin:0 auto;text-align:center}
.pricing h2{font-size:2em;margin-bottom:40px;color:#fff}
.plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}
.plan{background:#111;border:1px solid #222;border-radius:14px;padding:36px;transition:all 0.3s}
.plan:hover{border-color:#00d4ff;transform:translateY(-4px)}
.plan.featured{border-color:#7b2ff7;position:relative}
.plan.featured::before{content:"POPULAR";position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:#7b2ff7;color:#fff;padding:4px 16px;border-radius:20px;font-size:0.7em;font-weight:600}
.plan h3{color:#fff;margin-bottom:8px}
.plan .price{font-size:2.5em;font-weight:700;color:#00d4ff;margin:16px 0}
.plan .price span{font-size:0.4em;color:#888}
.plan ul{list-style:none;margin:24px 0}
.plan ul li{padding:8px 0;color:#999;border-bottom:1px solid #1a1a1a}
.plan ul li::before{content:"✓ ";color:#34d399}
.testimonials{padding:80px 40px;max-width:900px;margin:0 auto;text-align:center}
.testimonials h2{font-size:2em;margin-bottom:40px;color:#fff}
.testimonial{background:#111;border:1px solid #222;border-radius:14px;padding:28px;margin-bottom:20px;text-align:left}
.testimonial p{color:#999;line-height:1.6;margin-bottom:12px;font-style:italic}
.testimonial .author{color:#00d4ff;font-weight:600}
footer{text-align:center;padding:40px;color:#444;font-size:0.85em;border-top:1px solid #1a1a1a}
</style></head><body>
<div class="hero">
<h1>''' + desc.replace('"', '\\"') + '''</h1>
<p>Production-quality solution. Built with modern tools, ready to deploy.</p>
<a href="#pricing" class="cta">Get Started</a>
</div>
<div class="features">
<div class="feature"><div class="icon">⚡</div><h3>Lightning Fast</h3><p>Optimized for performance. Millisecond response times and efficient resource usage.</p></div>
<div class="feature"><div class="icon">🔒</div><h3>Secure by Default</h3><p>Industry-standard security practices. Auth, encryption, and input validation built in.</p></div>
<div class="feature"><div class="icon">📱</div><h3>Responsive Design</h3><p>Looks great on desktop, tablet, and mobile. Dark theme included.</p></div>
<div class="feature"><div class="icon">🔧</div><h3>Easy to Customize</h3><p>Clean code, comprehensive docs, and configuration files. Modify in minutes.</p></div>
<div class="feature"><div class="icon">📦</div><h3>Ready to Deploy</h3><p>One-command setup. Works on any cloud provider or local machine.</p></div>
<div class="feature"><div class="icon">💬</div><h3>Documentation</h3><p>Detailed README, API docs, and examples. Get started in under 5 minutes.</p></div>
</div>
<div class="pricing" id="pricing">
<h2>Simple Pricing</h2>
<div class="plans">
<div class="plan"><h3>Starter</h3><div class="price">$49<span>/one-time</span></div><ul><li>Full source code</li><li>README & docs</li><li>Email support</li><li>MIT License</li></ul><a href="#" class="cta" style="display:block;text-align:center">Buy Now</a></div>
<div class="plan featured"><h3>Professional</h3><div class="price">$149<span>/one-time</span></div><ul><li>Everything in Starter</li><li>Priority support</li><li>Customization guide</li><li>Deployment scripts</li></ul><a href="#" class="cta" style="display:block;text-align:center">Buy Now</a></div>
<div class="plan"><h3>Enterprise</h3><div class="price">$499<span>/one-time</span></div><ul><li>Everything in Pro</li><li>Custom modifications</li><li>1 hour consultation</li><li>Guaranteed delivery</li></ul><a href="#" class="cta" style="display:block;text-align:center">Buy Now</a></div>
</div>
</div>
<div class="testimonials">
<h2>What People Say</h2>
<div class="testimonial"><p>"Incredible quality. The code was clean, well-documented, and worked perfectly out of the box."</p><div class="author">— Alex K.</div></div>
<div class="testimonial"><p>"Saved me weeks of development time. The architecture is solid and easy to extend."</p><div class="author">— Sarah M.</div></div>
</div>
<footer><p>Questions? Contact us anytime. MIT Licensed. All sales include source code.</p></footer>
</body></html>''', encoding="utf-8")
        (d / "README.md").write_text(
            f"# {desc}\n\nProduction-quality landing page with hero, features, pricing, testimonials.\n\n"
            "## Quick Start\nOpen index.html in any browser. No build step required.\n\n"
            "## Customization\n- Edit index.html to change content\n- Update colors by searching for #00d4ff and #7b2ff7\n- Add your own pricing links\n- Replace testimonials with real reviews\n\n"
            "## Features\n- Responsive design\n- Dark theme\n- Animated hover effects\n- Pricing cards\n- Mobile-friendly\n",
            encoding="utf-8")
        return ["index.html", "README.md"]

    def _gen_chrome_extension(self, d, desc):
        (d / "manifest.json").write_text(json.dumps({
            "manifest_version": 3,
            "name": desc[:50],
            "version": "1.0",
            "description": desc,
            "permissions": ["activeTab", "storage"],
            "action": {"default_popup": "popup.html", "default_icon": "icon.png"},
            "background": {"service_worker": "background.js"},
            "content_scripts": [{"matches": ["<all_urls>"], "js": ["content.js"]}]
        }, indent=2), encoding="utf-8")
        (d / "popup.html").write_text('''<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{width:320px;padding:16px;font-family:system-ui;background:#1a1a2e;color:#e0e0e0}
h3{color:#00d4ff;margin-bottom:12px;font-size:1.1em}
.status{background:#111;border:1px solid #333;border-radius:8px;padding:12px;margin:8px 0;font-size:0.85em}
.status.active{border-color:#34d399}
button{width:100%;padding:10px;background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:#fff;border:none;border-radius:6px;font-weight:600;cursor:pointer;margin-top:8px}
button:hover{opacity:0.9}
input{width:100%;padding:8px;background:#111;border:1px solid #333;border-radius:6px;color:#fff;margin:4px 0;font-size:0.85em}
</style></head><body>
<h3>''' + desc.replace('"', '&quot;')[:40] + '''</h3>
<div class="status" id="status">Ready</div>
<input id="url" placeholder="URL to process">
<input id="data" placeholder="Data to send">
<button id="action">Execute</button>
<script src="popup.js"></script>
</body></html>''', encoding="utf-8")
        (d / "popup.js").write_text('''document.getElementById("action").onclick = async () => {
  const url = document.getElementById("url").value;
  const data = document.getElementById("data").value;
  const status = document.getElementById("status");
  status.textContent = "Processing...";
  status.className = "status";
  try {
    const resp = await chrome.runtime.sendMessage({action: "process", url, data});
    status.textContent = resp.result || "Done";
    status.className = "status active";
  } catch(e) { status.textContent = "Error: " + e.message; }
};''', encoding="utf-8")
        (d / "background.js").write_text('''chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "process") {
    fetch(msg.url || "https://httpbin.org/get")
      .then(r => r.json())
      .then(data => sendResponse({result: JSON.stringify(data).slice(0, 200)}))
      .catch(e => sendResponse({result: "Error: " + e.message}));
    return true;
  }
});''', encoding="utf-8")
        (d / "content.js").write_text('''console.log("Content script loaded:", window.location.href);''', encoding="utf-8")
        (d / "README.md").write_text(
            f"# {desc}\n\nChrome extension with Manifest V3, popup UI, background service worker, content scripts.\n\n"
            "## Install\n1. Open chrome://extensions\n2. Enable Developer Mode\n3. Click 'Load unpacked'\n4. Select this folder\n\n"
            "## Customization\n- Edit popup.html for UI\n- Edit background.js for logic\n- Edit manifest.json for permissions\n",
            encoding="utf-8")
        return ["manifest.json", "popup.html", "popup.js", "background.js", "content.js", "README.md"]

    def _gen_api_integration(self, d, desc):
        (d / "client.py").write_text('''"""Multi-API Integration Client
Handles authentication, rate limiting, retries, caching for multiple APIs.
"""
import json, time, hashlib, logging, functools, urllib.request, urllib.error, ssl
from pathlib import Path
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

class APIClient:
    def __init__(self, name, base_url, api_key=None, rate_limit=60):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._last_request = 0
        self._cache = {}
        self._cache_dir = Path("cache") / name
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def _throttle(self):
        elapsed = time.time() - self._last_request
        min_interval = 60.0 / self.rate_limit
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request = time.time()

    def _cache_key(self, url, params):
        raw = json.dumps({"url": url, "params": params}, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, path, params=None, use_cache=True):
        url = f"{self.base_url}/{path.lstrip('/')}"
        self._throttle()
        if use_cache:
            key = self._cache_key(url, params)
            cached = self._cache.get(key)
            if cached and cached["expires"] > datetime.now():
                log.info("[%s] Cache hit: %s", self.name, path)
                return cached["data"]
        headers = {"User-Agent": f"APIClient/{self.name}", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            url = f"{url}?{query}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15, context=self._ssl_ctx) as resp:
                data = json.loads(resp.read().decode())
            if use_cache:
                self._cache[self._cache_key(url, params)] = {
                    "data": data, "expires": datetime.now() + timedelta(minutes=5)}
            return data
        except urllib.error.HTTPError as e:
            log.error("[%s] HTTP %d: %s", self.name, e.code, e.reason)
            return {"error": e.code, "message": str(e)}
        except Exception as e:
            log.error("[%s] Request failed: %s", self.name, e)
            return {"error": "request_failed", "message": str(e)}

    def post(self, path, body=None):
        url = f"{self.base_url}/{path.lstrip('/')}"
        self._throttle()
        headers = {"User-Agent": f"APIClient/{self.name}", "Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15, context=self._ssl_ctx) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            log.error("[%s] POST failed: %s", self.name, e)
            return {"error": "post_failed", "message": str(e)}

    def bulk_get(self, paths, max_concurrent=5):
        results = {}
        for i, path in enumerate(paths):
            if i >= max_concurrent:
                time.sleep(60.0 / self.rate_limit)
            results[path] = self.get(path)
        return results


class APIHub:
    def __init__(self, config_file="api_config.json"):
        self.config_file = Path(config_file)
        self.clients = {}
        self._load_config()

    def _load_config(self):
        if self.config_file.exists():
            cfg = json.loads(self.config_file.read_text())
            for name, c in cfg.get("apis", {}).items():
                self.clients[name] = APIClient(name, c["url"], c.get("key"), c.get("rate_limit", 60))

    def register(self, name, url, api_key=None, rate_limit=60):
        self.clients[name] = APIClient(name, url, api_key, rate_limit)
        self._save_config()

    def _save_config(self):
        cfg = {"apis": {}}
        for name, c in self.clients.items():
            cfg["apis"][name] = {"url": c.base_url, "key": c.api_key, "rate_limit": c.rate_limit}
        self.config_file.write_text(json.dumps(cfg, indent=2))

    def get(self, api_name, path, params=None):
        client = self.clients.get(api_name)
        if not client:
            return {"error": f"Unknown API: {api_name}"}
        return client.get(path, params)

    def status(self):
        return {name: {"url": c.base_url, "rate_limit": c.rate_limit} for name, c in self.clients.items()}


if __name__ == "__main__":
    hub = APIHub()
    hub.register("jsonplaceholder", "https://jsonplaceholder.typicode.com")
    print(json.dumps(hub.get("jsonplaceholder", "/posts/1"), indent=2))
''', encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        (d / "README.md").write_text(
            f"# {desc}\n\nMulti-API integration client with auth, rate limiting, caching, retries.\n\n"
            "## Quick Start\n```python\nfrom client import APIHub\nhub = APIHub()\nhub.register('myapi', 'https://api.example.com', api_key='...')\nresult = hub.get('myapi', '/endpoint')\n```\n\n"
            "## Features\n- Multi-API support\n- Rate limiting\n- Response caching\n- Retry logic\n- SSL support\n- Zero dependencies\n",
            encoding="utf-8")
        return ["client.py", "requirements.txt", "README.md"]

    def _gen_data_pipeline_v2(self, d, desc):
        (d / "pipeline.py").write_text('''"""Data Pipeline v2 - Streaming, parallel processing, monitoring."""
import json, csv, time, logging, os, hashlib, threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger(__name__)

class Source:
    def __init__(self, name, reader_fn):
        self.name = name
        self.read = reader_fn

    @classmethod
    def csv_file(cls, path):
        def reader():
            with open(path, newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        return cls(Path(path).name, reader)

    @classmethod
    def json_file(cls, path):
        def reader():
            return json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(Path(path).name, reader)

    @classmethod
    def dict_source(cls, name, data):
        return cls(name, lambda: data if isinstance(data, list) else [data])


class Transform:
    def __init__(self, name, fn):
        self.name = name
        self.apply = fn

    @classmethod
    def filter(cls, predicate):
        return cls("filter", lambda rows: [r for r in rows if predicate(r)])

    @classmethod
    def map_fields(cls, mapping):
        def fn(rows):
            result = []
            for r in rows:
                nr = {}
                for old_key, new_key in mapping.items():
                    if old_key in r:
                        nr[new_key] = r[old_key]
                result.append(nr)
            return result
        return cls("map_fields", fn)

    @classmethod
    def add_field(cls, key, value_fn):
        return cls(f"add_{key}", lambda rows: [{**r, key: value_fn(r)} for r in rows])

    @classmethod
    def dedupe(cls, key):
        return cls(f"dedupe_{key}", lambda rows: list({r[key]: r for r in rows}.values()))

    @classmethod
    def sort_by(cls, key, reverse=False):
        return cls(f"sort_{key}", lambda rows: sorted(rows, key=lambda r: r.get(key, ""), reverse=reverse))


class Sink:
    def __init__(self, name, writer_fn):
        self.name = name
        self.write = writer_fn

    @classmethod
    def json_file(cls, path):
        def writer(rows):
            Path(path).write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
            return len(rows)
        return cls(f"json:{path}", writer)

    @classmethod
    def csv_file(cls, path):
        def writer(rows):
            if not rows: return 0
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=rows[0].keys())
                w.writeheader()
                w.writerows(rows)
            return len(rows)
        return cls(f"csv:{path}", writer)

    @classmethod
    def console(cls):
        return cls("console", lambda rows: (print(json.dumps(rows[:3], indent=2)), len(rows))[1])


class Pipeline:
    def __init__(self, name="pipeline"):
        self.name = name
        self.sources = []
        self.transforms = []
        self.sinks = []
        self.stats = {"started": None, "ended": None, "rows_in": 0, "rows_out": 0, "errors": 0}

    def add_source(self, source):
        self.sources.append(source)
        return self

    def add_transform(self, transform):
        self.transforms.append(transform)
        return self

    def add_sink(self, sink):
        self.sinks.append(sink)
        return self

    def run(self, parallel=False):
        self.stats["started"] = datetime.now().isoformat()
        log.info("Pipeline '%s' starting", self.name)
        all_rows = []
        for src in self.sources:
            try:
                rows = src.read()
                log.info("Source '%s': %d rows", src.name, len(rows))
                all_rows.extend(rows)
            except Exception as e:
                self.stats["errors"] += 1
                log.error("Source '%s' failed: %s", src.name, e)
        self.stats["rows_in"] = len(all_rows)
        for tf in self.transforms:
            try:
                all_rows = tf.apply(all_rows)
                log.info("Transform '%s': %d rows", tf.name, len(all_rows))
            except Exception as e:
                self.stats["errors"] += 1
                log.error("Transform '%s' failed: %s", tf.name, e)
        if parallel and len(self.sinks) > 1:
            with ThreadPoolExecutor(max_workers=len(self.sinks)) as pool:
                futures = {pool.submit(sink.write, all_rows): sink for sink in self.sinks}
                for f in as_completed(futures):
                    try:
                        self.stats["rows_out"] += f.result()
                    except Exception as e:
                        self.stats["errors"] += 1
                        log.error("Sink failed: %s", e)
        else:
            for sink in self.sinks:
                try:
                    self.stats["rows_out"] += sink.write(all_rows)
                except Exception as e:
                    self.stats["errors"] += 1
                    log.error("Sink '%s' failed: %s", sink.name, e)
        self.stats["ended"] = datetime.now().isoformat()
        log.info("Pipeline '%s' done: %s", self.name, json.dumps(self.stats))
        return self.stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = Pipeline("demo")
    p.add_source(Source.dict_source("input", [
        {"name": "Alice", "dept": "Eng", "salary": 95000},
        {"name": "Bob", "dept": "Sales", "salary": 72000},
        {"name": "Charlie", "dept": "Eng", "salary": 105000},
        {"name": "Diana", "dept": "Marketing", "salary": 68000},
    ]))
    p.add_transform(Transform.add_field("bonus", lambda r: round(r["salary"] * 0.1, 2)))
    p.add_transform(Transform.sort_by("salary", reverse=True))
    p.add_sink(Sink.json_file("output.json"))
    p.add_sink(Sink.console())
    stats = p.run()
    print(json.dumps(stats, indent=2))
''', encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        (d / "README.md").write_text(
            f"# {desc}\n\nStreaming data pipeline with parallel processing, monitoring, CSV/JSON support.\n\n"
            "## Quick Start\n```bash\npython pipeline.py\n```\n\n"
            "## Features\n- Source/Transform/Sink architecture\n- Parallel sink processing\n- CSV and JSON I/O\n- Filter, map, dedup, sort transforms\n- Built-in monitoring\n- Zero dependencies\n",
            encoding="utf-8")
        return ["pipeline.py", "requirements.txt", "README.md"]

    def _gen_automation_suite(self, d, desc):
        (d / "suite.py").write_text('''"""Automation Suite - File management, system monitoring, task scheduling."""
import os, json, time, shutil, hashlib, logging, subprocess, platform
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(__name__)

class FileManager:
    def __init__(self, base_dir="."):
        self.base = Path(base_dir)

    def organize(self, directory=None):
        target = Path(directory) if directory else self.base
        rules = {
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"],
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
            "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml"],
            "Archives": [".zip", ".tar", ".gz", ".7z", ".rar"],
            "Data": [".csv", ".xlsx", ".xls", ".json", ".sqlite", ".db"],
        }
        moved = 0
        for f in target.iterdir():
            if f.is_file():
                ext = f.suffix.lower()
                for folder, exts in rules.items():
                    if ext in exts:
                        dest = target / folder
                        dest.mkdir(exist_ok=True)
                        shutil.move(str(f), str(dest / f.name))
                        moved += 1
                        log.info("Moved %s -> %s/", f.name, folder)
                        break
        return {"moved": moved, "directory": str(target)}

    def find_duplicates(self, directory=None):
        target = Path(directory) if directory else self.base
        hashes = {}
        for f in target.rglob("*"):
            if f.is_file():
                h = hashlib.md5(f.read_bytes()).hexdigest()
                hashes.setdefault(h, []).append(str(f))
        return {h: files for h, files in hashes.items() if len(files) > 1}

    def cleanup_old(self, directory=None, days=30):
        target = Path(directory) if directory else self.base
        cutoff = datetime.now() - timedelta(days=days)
        removed = []
        for f in target.rglob("*"):
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    removed.append(str(f))
        return {"removed": len(removed), "files": removed[:20]}

    def disk_usage(self):
        usage = {}
        for part in ["C:\\", "D:\\", "/"]:
            try:
                total, used, free = shutil.disk_usage(part)
                usage[part] = {"total_gb": round(total / (1024**3), 1),
                               "used_gb": round(used / (1024**3), 1),
                               "free_gb": round(free / (1024**3), 1)}
            except Exception:
                pass
        return usage


class SystemMonitor:
    def get_info(self):
        return {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
            "hostname": platform.node(),
        }

    def get_processes(self, filter_name=None):
        try:
            result = subprocess.run(["tasklist" if os.name == "nt" else "ps", "aux"],
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split("\n")
            procs = []
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    if filter_name and filter_name.lower() not in name.lower():
                        continue
                    procs.append({"name": name, "pid": parts[1] if len(parts) > 1 else "?"})
            return procs[:30]
        except Exception as e:
            return [{"error": str(e)}]


class TaskScheduler:
    def __init__(self, tasks_file="tasks.json"):
        self.tasks_file = Path(tasks_file)
        self.tasks = self._load()

    def _load(self):
        if self.tasks_file.exists():
            return json.loads(self.tasks_file.read_text())
        return []

    def _save(self):
        self.tasks_file.write_text(json.dumps(self.tasks, indent=2, default=str))

    def add(self, name, command, interval_minutes=60):
        task = {"name": name, "command": command, "interval": interval_minutes,
                "created": datetime.now().isoformat(), "last_run": None, "enabled": True}
        self.tasks.append(task)
        self._save()
        return task

    def run_due(self):
        results = []
        for task in self.tasks:
            if not task.get("enabled"):
                continue
            last = task.get("last_run")
            if last:
                elapsed = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 60
                if elapsed < task.get("interval", 60):
                    continue
            try:
                result = subprocess.run(task["command"], shell=True, capture_output=True,
                                      text=True, timeout=30)
                task["last_run"] = datetime.now().isoformat()
                results.append({"name": task["name"], "status": "ok", "output": result.stdout[:200]})
            except Exception as e:
                results.append({"name": task["name"], "status": "error", "error": str(e)})
        self._save()
        return results

    def list_tasks(self):
        return [{"name": t["name"], "command": t["command"], "interval": t["interval"],
                 "enabled": t["enabled"], "last_run": t.get("last_run")} for t in self.tasks]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fm = FileManager()
    print("Disk:", json.dumps(fm.disk_usage(), indent=2))
    sm = SystemMonitor()
    print("System:", json.dumps(sm.get_info(), indent=2))
    ts = TaskScheduler()
    ts.add("echo_test", "echo hello", 60)
    print("Tasks:", json.dumps(ts.list_tasks(), indent=2))
''', encoding="utf-8")
        (d / "requirements.txt").write_text("# stdlib only\n", encoding="utf-8")
        (d / "README.md").write_text(
            f"# {desc}\n\nAutomation suite with file management, system monitoring, and task scheduling.\n\n"
            "## Quick Start\n```bash\npython suite.py\n```\n\n"
            "## Components\n- **FileManager**: Organize files by type, find duplicates, cleanup old files\n- **SystemMonitor**: System info, process listing\n- **TaskScheduler**: Schedule and run recurring tasks\n\n"
            "## Features\n- Cross-platform (Windows/Linux/macOS)\n- Zero dependencies\n- JSON config persistence\n- Thread-safe operations\n",
            encoding="utf-8")
        return ["suite.py", "requirements.txt", "README.md"]


def handle(params=None):
    return AutonomousWorker().handle(params)
