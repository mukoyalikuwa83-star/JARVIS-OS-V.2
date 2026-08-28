"""Content Engine — generates real blog posts, articles, and marketing content."""
import json
import hashlib
from pathlib import Path
from datetime import datetime

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_CONTENT_DIR = _DATA_DIR / "content"
_CONTENT_DIR.mkdir(exist_ok=True)


def generate_article(topic, style="blog_post"):
    templates = {
        "blog_post": {
            "intro": f"# {topic}\n\nIn today's fast-paced tech landscape, {topic.lower()} has become essential for developers and businesses alike.",
            "sections": [
                f"## Why {topic} Matters\n\nModern development demands efficiency, reliability, and scalability. Whether you're building a startup MVP or maintaining enterprise systems, the right approach to {topic.lower()} can make or break your project.",
                "## Key Components\n\n1. **Architecture Design** — A well-planned foundation saves time and reduces bugs\n2. **Implementation Patterns** — Using proven patterns ensures reliability\n3. **Testing Strategy** — Automated testing catches issues before they reach production\n4. **Deployment Pipeline** — CI/CD enables rapid, safe releases",
                "## Best Practices\n\n- Start simple, iterate based on real usage\n- Write tests alongside code, not after\n- Document decisions and trade-offs\n- Monitor in production, not just staging\n- Keep dependencies updated but stable",
                "## Getting Started\n\nThe fastest way to get started is with a production-ready template. Pre-built solutions handle the common patterns so you can focus on your unique business logic.",
            ],
            "cta": "Ready to accelerate your development? Browse production-ready templates and tools built for real-world use."
        },
        "tutorial": {
            "intro": f"# Building {topic} from Scratch\n\nThis step-by-step guide walks you through creating a production-quality {topic.lower()} solution.",
            "sections": [
                "## Prerequisites\n\n- Python 3.9+\n- Basic understanding of the domain\n- A text editor or IDE",
                "## Step 1: Setup\n\nStart with a clean project structure. We'll use a template that includes configuration, tests, and documentation.",
                "## Step 2: Core Implementation\n\nBuild the core logic first. Focus on correctness before optimization.",
                "## Step 3: Testing\n\nWrite unit tests for each component. Aim for high coverage on critical paths.",
                "## Step 4: Production Readiness\n\nAdd logging, error handling, configuration management, and documentation.",
            ],
            "cta": "Want the complete, tested implementation? Get the full source code with all tests and documentation."
        },
        "comparison": {
            "intro": f"# {topic}: A Practical Comparison\n\nChoosing the right approach for {topic.lower()} can be overwhelming. Here's a practical comparison.",
            "sections": [
                "## What We're Comparing\n\nWe'll evaluate based on: ease of setup, performance, maintainability, and cost.",
                "## Approach A: Manual Implementation\n\nPros: Full control, no dependencies, educational\nCons: Time-consuming, error-prone, hard to maintain",
                "## Approach B: Template-Based\n\nPros: Fast setup, tested patterns, documented\nCons: Less customization, learning curve",
                "## Approach C: Framework Solution\n\nPros: Rich ecosystem, community support, rapid development\nCons: Bloat, opinions, version lock-in",
                "## Recommendation\n\nFor most projects, a template-based approach offers the best balance of speed, quality, and flexibility.",
            ],
            "cta": "See our production-ready templates in action. Browse the full catalog."
        }
    }
    t = templates.get(style, templates["blog_post"])
    article = t["intro"] + "\n\n" + "\n\n".join(t["sections"]) + "\n\n" + t["cta"]
    content_id = hashlib.md5(f"{topic}{datetime.now().isoformat()}".encode()).hexdigest()[:8]
    filepath = _CONTENT_DIR / f"{content_id}.md"
    filepath.write_text(article, encoding="utf-8")
    return {"id": content_id, "topic": topic, "style": style, "filepath": str(filepath),
            "word_count": len(article.split()), "content": article[:500]}


def generate_product_description(title, features, price):
    desc = f"""## {title}

Production-quality code ready for immediate use.

### Features
{chr(10).join(f'- {f}' for f in features)}

### What's Included
- Complete source code
- README with setup instructions
- requirements.txt
- Configuration files
- Basic tests

### Price: ${price}

Instant download. MIT License. Use in personal or commercial projects.

### Why This Product?
Built with best practices, tested, and documented. Save hours of development time with a solid foundation you can build on."""
    return desc


def generate_seo_tags(title, description):
    words = title.lower().split()
    keywords = words + [f"python {w}" for w in words] + ["code", "template", "production-ready", "download"]
    return {
        "title": f"{title} — Production-Ready Python Code",
        "description": description[:160],
        "keywords": keywords[:15],
        "og_title": title,
        "og_description": description[:200],
        "og_type": "product",
    }


def list_content():
    if not _CONTENT_DIR.exists():
        return "No content generated yet."
    files = sorted(_CONTENT_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return "No content files found."
    lines = [f"=== CONTENT LIBRARY ({len(files)} articles) ==="]
    for f in files[:10]:
        content = f.read_text(encoding="utf-8")
        lines.append(f"  {f.stem}: {content[:80].replace(chr(10), ' ')} ({len(content.split())} words)")
    if len(files) > 10:
        lines.append(f"  ... and {len(files) - 10} more")
    return "\n".join(lines)


def handle(parameters=None):
    params = parameters or {}
    action = params.get("action", "status")
    target = params.get("target", "")
    value = params.get("value", "")
    if action == "status":
        return list_content()
    elif action == "blog" or action == "article":
        result = generate_article(target or "Python Development Best Practices")
        return f"Generated: {result['topic']} ({result['word_count']} words)\n{result['content'][:300]}"
    elif action == "tutorial":
        result = generate_article(target or "Building a Production API", "tutorial")
        return f"Generated: {result['topic']} ({result['word_count']} words)\n{result['content'][:300]}"
    elif action == "comparison":
        result = generate_article(target or "Python Web Frameworks", "comparison")
        return f"Generated: {result['topic']} ({result['word_count']} words)\n{result['content'][:300]}"
    elif action == "description":
        features = [f.strip() for f in (value or "Production Code, Well Documented, MIT License").split(",")]
        desc = generate_product_description(target or "Python Tool", features, 49)
        return desc[:500]
    elif action == "seo":
        tags = generate_seo_tags(target or "Python Tool", value or "Production-ready code")
        return json.dumps(tags, indent=2)
    return f"Unknown action: {action}. Available: status, blog, tutorial, comparison, description, seo"
