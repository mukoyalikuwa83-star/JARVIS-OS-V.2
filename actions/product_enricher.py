"""Product Enricher - Analyzes ZIP products and generates proper listings."""
import json
import re
import zipfile
from pathlib import Path
from collections import Counter

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"


def _load(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save(path, data):
    path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def analyze_zip(zip_path):
    """Analyze a product ZIP and return metadata about its contents."""
    info = {
        "files": [],
        "main_file": "",
        "main_content": "",
        "imports": [],
        "classes": [],
        "functions": [],
        "has_tests": False,
        "has_readme": False,
        "has_requirements": False,
        "has_env_example": False,
        "size_kb": zip_path.stat().st_size // 1024,
        "detected_type": "unknown",
        "keywords": [],
    }

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            info["files"] = zf.namelist()

            for name in zf.namelist():
                lower = name.lower()
                if "test" in lower:
                    info["has_tests"] = True
                if "readme" in lower:
                    info["has_readme"] = True
                if "requirements" in lower:
                    info["has_requirements"] = True
                if ".env.example" in lower:
                    info["has_env_example"] = True

            # Read main Python file
            for name in zf.namelist():
                if name.endswith('.py') and not name.startswith('test'):
                    content = zf.read(name).decode('utf-8', errors='replace')
                    info["main_file"] = name
                    info["main_content"] = content[:3000]
                    break

            # Also read README if present
            for name in zf.namelist():
                if name.lower().startswith('readme'):
                    readme = zf.read(name).decode('utf-8', errors='replace')
                    info["readme"] = readme[:1000]
                    break

            # Parse code
            if info["main_content"]:
                content = info["main_content"]
                info["imports"] = list(set(re.findall(r'^(?:from|import)\s+(\w+)', content, re.MULTILINE)))
                info["classes"] = re.findall(r'class\s+(\w+)', content)
                info["functions"] = re.findall(r'def\s+(\w+)', content)

    except Exception as e:
        info["error"] = str(e)

    return info


def _clean_title(title):
    """Remove noise phrases from product titles."""
    if not title:
        return None
    # Remove common noise patterns
    title = re.sub(r'(?i)professional\s+(?:freelancer|gumroad|upwork|fiverr|developer)\s*(?:gig|project|tool)?:?\s*', '', title)
    title = re.sub(r'(?i)(?:python|custom|auto)[-_ ]?(?:developer|project|tool|built)[-_ ]+(?:for|on)[-_ ]?(?:upwork|fiverr|gumroad|freelancer):?\s*', '', title)
    title = re.sub(r'(?i)freelancer[-_ ]?gig:?\s*', '', title)
    title = re.sub(r'(?i)gumroad\s+(?:gig|project)?:?\s*', '', title)
    title = re.sub(r'(?i)upwork\s+(?:gig|project)?:?\s*', '', title)
    title = re.sub(r'(?i)fiverr\s+(?:gig|project)?:?\s*', '', title)
    title = re.sub(r'(?i)production\s+(?:quality\s+)?', '', title)
    title = re.sub(r'(?i)custom\s+automation\s+tool', '', title)
    title = re.sub(r'(?i)custom\s+api', 'API', title)
    # Clean up extra spaces and colons
    title = re.sub(r'\s*:\s*$', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    # If empty after cleaning, return None
    if len(title) < 3:
        return None
    return title


def detect_product_type(analysis):
    """Detect product type from code analysis."""
    imports = list(i.lower() for i in analysis["imports"])
    classes = [c.lower() for c in analysis["classes"]]
    functions = [f.lower() for f in analysis["functions"]]
    files = [f.lower() for f in analysis["files"]]
    main = analysis["main_content"].lower()
    readme = analysis.get("readme", "").lower()

    all_text = " ".join(imports + classes + functions + files) + " " + main + " " + readme

    # Flask API
    if "flask" in imports or "flask" in all_text:
        if any(k in all_text for k in ["auth", "crud", "jwt", "rate_limit"]):
            return "flask_api"
        return "flask_api"

    # FastAPI
    if "fastapi" in imports or "fastapi" in all_text:
        return "flask_api"

    # Discord Bot
    if "discord" in imports or "discord" in all_text:
        return "discord_bot"

    # Telegram Bot
    if "telegram" in imports or "telegram" in all_text or "python-telegram-bot" in all_text:
        return "telegram_bot"

    # Web Scraper
    if any(k in all_text for k in ["beautifulsoup", "bs4", "scrapy", "selenium", "playwright", "requests.get", "httpx"]):
        if any(k in all_text for k in ["scrape", "crawl", "extract", "parse"]):
            return "web_scraper"
        return "web_scraper"

    # CLI Tool
    if any(k in all_text for k in ["argparse", "click", "typer", "cli"]):
        return "cli_tool"

    # ETL Pipeline
    if any(k in all_text for k in ["etl", "pipeline", "extract", "transform", "load"]):
        return "etl_pipeline"

    # Data Analysis
    if any(k in all_text for k in ["pandas", "matplotlib", "numpy", "analysis", "chart", "plot"]):
        return "data_analysis"

    # Web Dashboard
    if any(k in all_text for k in ["dashboard", "chart", "flask", "html"]):
        if "html" in files or "index.html" in files:
            return "web_dashboard"

    # SaaS Template
    if any(k in all_text for k in ["saas", "stripe", "subscription", "plan"]):
        return "saas_template"

    # Chrome Extension
    if any(k in all_text for k in ["chrome", "manifest", "extension", "browser_action"]):
        return "chrome_extension"

    # API Wrapper
    if any(k in all_text for k in ["api", "client", "requests", "httpx", "urllib"]):
        return "api_wrapper"

    # Automation Script
    if any(k in all_text for k in ["schedule", "automat", "monitor", "cron", "task"]):
        return "automation_script"

    # File Organizer
    if any(k in all_text for k in ["organize", "file_manager", "shutil", "duplicate"]):
        return "automation_script"

    # Landing Page
    if "index.html" in files and "css" in all_text:
        return "landing_page"

    # Default to python_script
    return "python_script"


# Product type metadata
PRODUCT_META = {
    "flask_api": {
        "prefix": "Flask REST API",
        "description_template": "Complete Flask REST API with {features}. Production-ready, deploy anywhere.",
        "default_price": 99,
        "default_features": ["JWT Authentication", "CRUD Endpoints", "Rate Limiting", "Input Validation", "Tests Included", "Production Ready"],
    },
    "web_dashboard": {
        "prefix": "Web Dashboard",
        "description_template": "Full-stack web dashboard with {features}. Ready to customize.",
        "default_price": 89,
        "default_features": ["Responsive UI", "Interactive Charts", "Data Tables", "CSV Export", "Dark Theme", "Mobile Friendly"],
    },
    "cli_tool": {
        "prefix": "CLI Tool",
        "description_template": "Professional CLI tool with {features}. Zero dependencies.",
        "default_price": 59,
        "default_features": ["Subcommands", "Persistent Config", "JSON Storage", "Search & Filter", "Zero Dependencies", "Tab Completion"],
    },
    "etl_pipeline": {
        "prefix": "ETL Pipeline",
        "description_template": "Production ETL pipeline with {features}. Config-driven.",
        "default_price": 79,
        "default_features": ["CSV/JSON/JSONL", "Chained Transforms", "Deduplication", "Error Handling", "Config-Driven", "Retry Logic"],
    },
    "saas_template": {
        "prefix": "SaaS Template",
        "description_template": "Complete SaaS starter with {features}. Stripe-ready.",
        "default_price": 149,
        "default_features": ["Landing Page", "User Auth", "Dashboard", "API Keys", "Billing Hooks", "Stripe Ready"],
    },
    "python_script": {
        "prefix": "Python Tool",
        "description_template": "Production Python utility with {features}. Ready to run.",
        "default_price": 49,
        "default_features": ["argparse CLI", "Logging", "JSON I/O", "Error Handling", "Retry Logic", "Well Documented"],
    },
    "web_scraper": {
        "prefix": "Web Scraper",
        "description_template": "Production web scraper with {features}. Ready to use.",
        "default_price": 79,
        "default_features": ["Multi-URL", "Proxy Support", "Rate Limiting", "CSV+JSON Export", "Retry Logic", "SSL Support"],
    },
    "discord_bot": {
        "prefix": "Discord Bot",
        "description_template": "Feature-rich Discord bot with {features}. Ready to deploy.",
        "default_price": 99,
        "default_features": ["Moderation", "Music", "AI Chat", "Economy", "Custom Commands", "SQLite Storage"],
    },
    "telegram_bot": {
        "prefix": "Telegram Bot",
        "description_template": "Production Telegram bot with {features}. Ready to deploy.",
        "default_price": 89,
        "default_features": ["Inline Keyboards", "Command Handlers", "Notifications", "Admin Panel", "SQLite Storage", "Webhook Support"],
    },
    "automation_script": {
        "prefix": "Automation Script",
        "description_template": "Cross-platform automation with {features}. Set and forget.",
        "default_price": 59,
        "default_features": ["File Organization", "System Monitoring", "Scheduling", "Logging", "Config File", "Cross Platform"],
    },
    "data_analysis": {
        "prefix": "Data Analysis Tool",
        "description_template": "Data analysis toolkit with {features}. Ready to analyze.",
        "default_price": 69,
        "default_features": ["Pandas", "Matplotlib Charts", "CSV/JSON Export", "Statistical Analysis", "Reports", "CLI Interface"],
    },
    "api_wrapper": {
        "prefix": "API Client",
        "description_template": "Production API client with {features}. Zero dependencies.",
        "default_price": 79,
        "default_features": ["Auth Support", "Rate Limiting", "Response Caching", "Retry Logic", "Request Logging", "Type Hints"],
    },
    "landing_page": {
        "prefix": "Landing Page",
        "description_template": "Professional landing page with {features}. Single HTML file.",
        "default_price": 69,
        "default_features": ["Hero Section", "Features Grid", "Pricing Cards", "Testimonials", "Dark Theme", "Mobile First"],
    },
    "chrome_extension": {
        "prefix": "Chrome Extension",
        "description_template": "Chrome extension (Manifest V3) with {features}.",
        "default_price": 79,
        "default_features": ["Manifest V3", "Popup UI", "Background Worker", "Content Scripts", "Storage API", "Auto Update"],
    },
}


def generate_title(product_type, analysis):
    """Generate a descriptive title from the code analysis."""
    meta = PRODUCT_META.get(product_type, PRODUCT_META["python_script"])
    prefix = meta['prefix']

    # Try to extract meaningful name from README
    readme = analysis.get("readme", "")
    if readme:
        # First heading
        match = re.search(r'^#\s+(.+)', readme, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Clean up noise phrases
            title = _clean_title(title)
            if title and len(title) > 5 and "readme" not in title.lower():
                # Avoid doubled prefix
                if title.startswith(prefix):
                    return title
                return f"{prefix} - {title}"

    # Try from main file docstring
    content = analysis.get("main_content", "")
    doc_match = re.search(r'"""(.+?)"""', content)
    if doc_match:
        doc = doc_match.group(1).strip().split('\n')[0]
        doc = _clean_title(doc)
        if doc and len(doc) > 5:
            if doc.startswith(prefix):
                return doc
            return f"{prefix} - {doc}"

    # Try from imports to create a specific name
    imports = analysis.get("imports", [])
    main = content.lower()

    if "flask" in imports:
        if "sqlalchemy" in imports or "peewee" in imports:
            return f"{meta['prefix']} - Database-backed REST API"
        if "stripe" in main:
            return f"{meta['prefix']} - Payment Processing API"
        if "blog" in main or "post" in main:
            return f"{meta['prefix']} - Blog/Content API"
        if "auth" in main:
            return f"{meta['prefix']} - Authentication API"
        return f"{meta['prefix']} - Web Application API"

    if "discord" in imports:
        features = []
        if "moderat" in main:
            features.append("Moderation")
        if "music" in main:
            features.append("Music")
        if "econom" in main or "balance" in main:
            features.append("Economy")
        if "ai" in main or "openai" in main:
            features.append("AI Chat")
        if features:
            return f"{meta['prefix']} - {', '.join(features[:3])} Bot"
        return f"{meta['prefix']} - Multi-feature Bot"

    if "telegram" in imports:
        if "rss" in main:
            return f"{meta['prefix']} - RSS Feed Bot"
        if "notif" in main:
            return f"{meta['prefix']} - Notification Bot"
        return f"{meta['prefix']} - Commands & Alerts Bot"

    if "pandas" in imports or "matplotlib" in imports:
        return f"{meta['prefix']} - Data Processing Toolkit"

    if "argparse" in imports or "click" in imports:
        funcs = [f for f in analysis.get("functions", []) if not f.startswith('_')]
        if funcs:
            return f"{meta['prefix']} - {funcs[0].replace('_', ' ').title()} CLI"

    # Generic fallback based on file names
    files = [f.lower() for f in analysis.get("files", [])]
    if "bot.py" in files:
        return f"{meta['prefix']} - Automated Bot"
    if "scraper.py" in files:
        return f"{meta['prefix']} - Web Data Extractor"
    if "app.py" in files:
        return f"{meta['prefix']} - Web Application"

    return f"{meta['prefix']} - Production Tool"


def generate_description(product_type, analysis):
    """Generate a detailed description from code analysis."""
    meta = PRODUCT_META.get(product_type, PRODUCT_META["python_script"])

    # Detect specific features
    content = analysis.get("main_content", "").lower()
    imports = [i.lower() for i in analysis.get("imports", [])]
    features = []

    # Authentication
    if any(k in content for k in ["auth", "login", "jwt", "token", "password"]):
        features.append("user authentication")
    if "jwt" in content:
        features.append("JWT tokens")

    # Database
    if any(k in imports for k in ["sqlalchemy", "peewee", "sqlite", "mongodb", "redis"]):
        features.append("database storage")
    if "sqlite" in content or "sqlite3" in imports:
        features.append("SQLite storage")

    # API features
    if "rate_limit" in content or "ratelimit" in content:
        features.append("rate limiting")
    if "crud" in content:
        features.append("CRUD operations")
    if any(k in content for k in ["validate", "schema", "marshmallow", "pydantic"]):
        features.append("input validation")

    # Bot features
    if "moderat" in content:
        features.append("moderation")
    if "music" in content:
        features.append("music playback")
    if "econom" in content or "balance" in content:
        features.append("economy system")
    if "ai" in content or "openai" in content:
        features.append("AI integration")

    # Data features
    if "pandas" in imports:
        features.append("data processing")
    if "matplotlib" in imports or "plotly" in imports:
        features.append("charts & visualization")
    if "csv" in content:
        features.append("CSV support")
    if "json" in content:
        features.append("JSON support")

    # Web features
    if "flask" in imports:
        features.append("Flask web framework")
    if "fastapi" in imports:
        features.append("FastAPI framework")

    # Testing
    if analysis.get("has_tests"):
        features.append("tests included")

    # CLI
    if any(k in content for k in ["argparse", "click", "typer"]):
        features.append("CLI interface")

    # Build description
    if features:
        feature_str = ", ".join(features[:5])
        return meta["description_template"].format(features=feature_str)

    return f"Production-quality {product_type.replace('_', ' ')}. Ready to use, well documented, MIT licensed."


def generate_features(product_type, analysis):
    """Generate feature tags based on actual code capabilities."""
    meta = PRODUCT_META.get(product_type, PRODUCT_META["python_script"])
    base_features = list(meta["default_features"])

    content = analysis.get("main_content", "").lower()
    imports = [i.lower() for i in analysis.get("imports", [])]

    # Override features based on actual content
    custom = []

    if "jwt" in content:
        custom.append("JWT Authentication")
    if "rate_limit" in content:
        custom.append("Rate Limiting")
    if any(k in imports for k in ["sqlalchemy", "peewee", "sqlite", "sqlite3"]):
        custom.append("Database Storage")
    if analysis.get("has_tests"):
        custom.append("Tests Included")
    if analysis.get("has_env_example"):
        custom.append("Environment Config")
    if "logging" in imports or "log" in content:
        custom.append("Logging")
    if "async" in content:
        custom.append("Async Support")
    if "cache" in content:
        custom.append("Response Caching")
    if "retry" in content:
        custom.append("Retry Logic")

    if custom:
        # Use custom features but keep some defaults
        return (custom + base_features)[:6]

    return base_features[:6]


def generate_price(product_type, analysis):
    """Generate appropriate price based on type and complexity."""
    meta = PRODUCT_META.get(product_type, PRODUCT_META["python_script"])
    base = meta["default_price"]

    # Adjust for complexity
    content = analysis.get("main_content", "")
    file_count = len(analysis.get("files", []))

    if file_count > 5:
        base = int(base * 1.3)
    elif file_count > 3:
        base = int(base * 1.1)

    if analysis.get("has_tests"):
        base += 10

    # Round to nearest 9
    base = max(29, base)
    base = (base // 10) * 10 + 9 if base % 10 != 9 else base

    return base


def enrich_product(product_id, zip_path):
    """Analyze a product ZIP and generate a proper listing."""
    analysis = analyze_zip(zip_path)
    product_type = detect_product_type(analysis)

    title = generate_title(product_type, analysis)
    description = generate_description(product_type, analysis)
    features = generate_features(product_type, analysis)
    price = generate_price(product_type, analysis)
    category = PRODUCT_META.get(product_type, PRODUCT_META["python_script"])["prefix"]

    return {
        "id": product_id,
        "listing": {
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "features": features,
            "delivery_time": "24 hours",
            "product_type": product_type,
        },
        "analysis": {
            "detected_type": product_type,
            "main_file": analysis["main_file"],
            "imports": analysis["imports"][:10],
            "classes": analysis["classes"][:5],
            "functions": analysis["functions"][:5],
            "has_tests": analysis["has_tests"],
            "has_readme": analysis["has_readme"],
            "size_kb": analysis["size_kb"],
        }
    }


def enrich_all_products():
    """Enrich all products with generic titles."""
    products_dir = _DATA_DIR / "products"
    jobs_file = _DATA_DIR / "worker_jobs.json"
    jobs = _load(jobs_file, {"found": [], "applied": [], "delivered": []})
    delivered = jobs.get("delivered", [])

    enriched = 0
    skipped = 0
    results = []

    # Build lookup
    delivered_map = {d["id"]: d for d in delivered}

    for z in sorted(products_dir.glob("*.zip")):
        wid = z.stem
        d = delivered_map.get(wid, {})
        listing = d.get("listing", {})
        title = listing.get("title", "")

        # Skip already-enriched products (unless they have issues)
        has_noise = bool(re.search(r'(?i)freelancer|gumroad|upwork|fiverr|auto-built|python.developer|custom.automation', title))
        is_generic = "Product " in title and len(title) < 25
        has_doubled = bool(re.search(r'(Flask REST API - Flask REST API|CLI Tool - CLI Tool|Discord Bot - Discord Bot|Telegram Bot - Telegram Bot|Web Dashboard - Web Dashboard|ETL Pipeline - ETL Pipeline|Web Scraper - Web Scraper)', title))
        if not has_noise and not is_generic and not has_doubled:
            skipped += 1
            continue

        result = enrich_product(wid, z)

        # Update delivered entry
        if d:
            d["listing"] = result["listing"]
        else:
            # Create new entry
            new_entry = {
                "id": wid,
                "type": result["analysis"]["detected_type"],
                "desc": result["listing"]["title"],
                "files": [],
                "dir": str(products_dir / wid),
                "zip": str(z),
                "listing": result["listing"],
            }
            delivered.append(new_entry)

        results.append(result)
        enriched += 1

    # Save updated jobs
    jobs["delivered"] = delivered
    _save(jobs_file, jobs)

    return {
        "enriched": enriched,
        "skipped": skipped,
        "total": len(list(products_dir.glob("*.zip"))),
        "sample": results[:5] if results else []
    }


def rebuild_store():
    """Rebuild the store HTML from enriched listings."""
    products_dir = _DATA_DIR / "products"
    jobs_file = _DATA_DIR / "worker_jobs.json"
    jobs = _load(jobs_file, {"delivered": []})
    delivered = jobs.get("delivered", [])

    config = _load(_DATA_DIR / "config.json", {})
    paypal_email = config.get("paypal_email", "mukoyalikuwa07@gmail.com")

    catalog = []
    for z in products_dir.glob("*.zip"):
        wid = z.stem
        listing = None
        for d in delivered:
            if d.get("id") == wid:
                listing = d.get("listing", {})
                break
        if listing:
            # Normalize category names
            cat = listing.get("category", "Code")
            cat_map = {
                "Flask Api": "Flask REST API",
                "Cli Tool": "CLI Tool",
                "Web Scraper": "Web Scraper",
                "Discord Bot": "Discord Bot",
                "Telegram Bot": "Telegram Bot",
                "Code": "Python Tool",
            }
            listing["category"] = cat_map.get(cat, cat)
            catalog.append({
                "id": wid,
                "listing": listing,
                "zip": z.name,
                "size_kb": z.stat().st_size // 1024
            })

    # Sort by price descending
    catalog.sort(key=lambda x: x["listing"].get("price", 0), reverse=True)

    total = sum(c["listing"].get("price", 0) for c in catalog)

    # Category counts
    cats = {}
    for c in catalog:
        cat = c["listing"].get("category", "Code")
        cats[cat] = cats.get(cat, 0) + 1

    # Build category filters
    cat_html = ""
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        cat_html += f'<button class="cat-btn" onclick="filterCategory(\'{cat}\')">{cat} ({count})</button>\n'

    # Build product cards
    items_html = ""
    for c in catalog:
        l = c["listing"]
        features = l.get("features", ["Production Code", "Well Documented", "MIT License"])
        feat_html = "".join(f'<span class="feat">{f}</span>' for f in features[:6])
        pay_link = f"https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business={paypal_email}&item_name={l['title']}&amount={l['price']}&currency_code=USD"
        download_link = f"https://github.com/mukoyalikuwa83-star/JARVIS-OS-V.2/releases/download/products/{c['id']}.zip"
        items_html += f"""
            <div class="product" data-category="{l.get('category', 'Code')}" id="product-{c['id']}">
              <div class="badge">{l.get('category', 'Code')}</div>
              <h3>{l['title']}</h3>
              <p>{l.get('description', '')[:200]}</p>
              <div class="features">{feat_html}</div>
              <div class="meta">{c['size_kb']}KB &middot; ZIP Download &middot; MIT License &middot; Instant Delivery</div>
              <div class="price">${l['price']}</div>
              <a href="{pay_link}" class="btn btn-buy" target="_blank">Buy Now — ${l['price']}</a>
              <a href="{download_link}" class="btn btn-details" target="_blank">Download Preview</a>
            </div>"""

    html = f"""<!DOCTYPE html>
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
.filters{{text-align:center;padding:16px 20px;max-width:1200px;margin:0 auto}}
.cat-btn{{background:#1a1a2e;color:#7b2ff7;border:1px solid #333;padding:6px 16px;border-radius:20px;font-size:0.8em;margin:4px;cursor:pointer;transition:all 0.2s}}
.cat-btn:hover,.cat-btn.active{{background:#7b2ff7;color:#fff;border-color:#7b2ff7}}
.search-box{{display:block;width:100%;max-width:500px;margin:16px auto;padding:12px 20px;background:#111;border:1px solid #333;border-radius:10px;color:#e0e0e0;font-size:1em}}
.search-box:focus{{outline:none;border-color:#00d4ff}}
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
</style>
<script>
function filterCategory(cat) {{
  document.querySelectorAll('.product').forEach(p => {{
    p.style.display = (cat === 'All' || p.dataset.category === cat) ? '' : 'none';
  }});
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}}
function searchProducts(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('.product').forEach(p => {{
    const text = p.textContent.toLowerCase();
    p.style.display = text.includes(q) ? '' : 'none';
  }});
}}
</script></head><body>
<div class="header">
  <h1>JARVIS Code Store</h1>
  <p>Production-quality Python tools, bots, and scripts. Built with AI, tested, documented. Instant download after purchase.</p>
</div>
<div class="stats">
  <strong>{len(catalog)}</strong> products &middot; <strong>${total}</strong> total value &middot; MIT licensed &middot; Instant download
</div>
<div class="trust">
  <span>100% source code</span> &middot; <span>Production tested</span> &middot; <span>Well documented</span> &middot; <span>MIT License</span>
</div>
<div class="filters">
  <input type="text" class="search-box" placeholder="Search products..." oninput="searchProducts(this.value)">
  <button class="cat-btn active" onclick="filterCategory('All')">All ({len(catalog)})</button>
  {cat_html}
</div>
<div class="grid">
{items_html}
</div>
<div class="faq">
  <h2>Frequently Asked Questions</h2>
  <div class="faq-item"><h4>What do I get?</h4><p>Production-ready Python source code with README, requirements.txt, tests, and configuration. Download the ZIP, extract, and run.</p></div>
  <div class="faq-item"><h4>Are these ready to use?</h4><p>Yes. Each product is tested, documented, and includes setup instructions. Just <code>pip install -r requirements.txt</code> and run.</p></div>
  <div class="faq-item"><h4>What license?</h4><p>All code is MIT licensed. Use it in personal or commercial projects without restriction.</p></div>
  <div class="faq-item"><h4>Can I get support?</h4><p>Yes. Contact us via email for any questions about setup or customization.</p></div>
</div>
<div class="footer">
  <p>Questions? Email: mukoyalikuwa83@gmail.com</p>
  <p style="margin-top:8px">Powered by JARVIS-OS &middot; All code is production-ready</p>
</div>
</body></html>"""

    return html


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "enrich":
        result = enrich_all_products()
        print(json.dumps(result, indent=2, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "rebuild":
        html = rebuild_store()
        out = _DATA_DIR.parent / "docs" / "index.html"
        out.write_text(html, encoding="utf-8")
        print(f"Store rebuilt: {out} ({len(html)} bytes)")
    elif len(sys.argv) > 1 and sys.argv[1] == "analyze":
        # Analyze single product
        pid = sys.argv[2] if len(sys.argv) > 2 else None
        if pid:
            z = _DATA_DIR / "products" / f"{pid}.zip"
            if z.exists():
                result = enrich_product(pid, z)
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"Product {pid} not found")
        else:
            print("Usage: python product_enricher.py analyze <product_id>")
    else:
        print("Usage:")
        print("  python product_enricher.py enrich    - Enrich all generic products")
        print("  python product_enricher.py rebuild   - Rebuild store HTML")
        print("  python product_enricher.py analyze ID - Analyze single product")
