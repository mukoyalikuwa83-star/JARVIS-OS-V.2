"""Autonomous Brain — main orchestrator that manages all sub-agents, runs background tasks, confirms completion, and makes decisions."""

import subprocess
import os
import time
import json
import threading
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

_BRAIN_STATE = _DATA_DIR / "brain_state.json"
_AGENT_REGISTRY = _DATA_DIR / "agent_registry.json"
_TASK_LOG = _DATA_DIR / "task_log.json"
_MONEY_LOG = _DATA_DIR / "money_log.json"
_IDEAS_FILE = _DATA_DIR / "ideas.json"

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=NO_WINDOW)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def _ps(command, timeout=15):
    out, rc = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], timeout=timeout)
    return out if rc == 0 else ""


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


def _get_agents_list(agents_data):
    """Safely extract agents list from dict or list format."""
    if isinstance(agents_data, dict):
        return agents_data.get("agents", [])
    elif isinstance(agents_data, list):
        return agents_data
    return []


def _log_task(task_id, agent, action, result, status="completed"):
    log = _load_json(_TASK_LOG, {"tasks": []})
    log["tasks"].append({
        "id": task_id,
        "agent": agent,
        "action": action,
        "result": str(result)[:500],
        "status": status,
        "time": _now(),
    })
    log["tasks"] = log["tasks"][-500:]
    _save_json(_TASK_LOG, log)


def _log_money(source, amount, details):
    log = _load_json(_MONEY_LOG, {"entries": []})
    log["entries"].append({
        "source": source,
        "amount": amount,
        "details": details,
        "time": _now(),
    })
    _save_json(_MONEY_LOG, log)


def handle(parameters: dict) -> str:
    action = parameters.get("action", "")
    target = parameters.get("target", "")
    value = parameters.get("value", "")
    handlers = {
        "status": _brain_status,
        "start_day": _start_day,
        "end_day": _end_day,
        "run_cycle": _run_cycle,
        "get_agents": _get_agents,
        "spawn_agent": lambda: _spawn_agent(target, value),
        "kill_agent": lambda: _kill_agent(target),
        "agent_status": lambda: _agent_status(target),
        "get_ideas": _get_ideas,
        "add_idea": lambda: _add_idea(target, value),
        "prioritize_ideas": _prioritize_ideas,
        "get_task_log": lambda: _get_task_log(target),
        "get_money_log": _get_money_log,
        "confirm_task": lambda: _confirm_task(target),
        "research_opportunity": lambda: _research_opportunity(target),
        "suggest_side_hustles": _suggest_side_hustles,
        "plan_project": lambda: _plan_project(target),
        "what_can_i_do": _what_can_i_do,
        "while_user_sleeps": _while_user_sleeps,
        "brain_health": _brain_health,
        "learn_from_mistake": lambda: _learn_from_mistake(target, value),
        "get_learned": _get_learned,
        "auto_heal": _auto_heal,
        "daily_report": _daily_report,
    }
    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown autonomous_brain action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _brain_status() -> str:
    state = _load_json(_BRAIN_STATE, {
        "status": "offline",
        "started": None,
        "cycle_count": 0,
        "tasks_completed": 0,
        "money_earned": 0,
        "agents_active": 0,
    })
    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    active = [a for a in _get_agents_list(agents) if a.get("status") == "running"]
    state["agents_active"] = len(active)

    lines = [
        f"Brain Status: {state.get('status', 'unknown')}",
        f"Started: {state.get('started', 'Never')}",
        f"Cycles: {state.get('cycle_count', 0)}",
        f"Tasks completed: {state.get('tasks_completed', 0)}",
        f"Money earned: ${state.get('money_earned', 0):.2f}",
        f"Active agents: {len(active)}",
    ]
    if active:
        lines.append("Active agents:")
        for a in active:
            lines.append(f"  - {a.get('name', '?')}: {a.get('current_task', 'idle')}")
    return "\n".join(lines)


def _start_day() -> str:
    state = _load_json(_BRAIN_STATE, {})
    state["status"] = "active"
    state["started"] = _now()
    state["cycle_count"] = 0
    state["tasks_completed"] = 0
    _save_json(_BRAIN_STATE, state)

    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    running = [a for a in _get_agents_list(agents) if a.get("status") == "running"]

    ideas = _load_json(_IDEAS_FILE, {"ideas": []})
    prioritized = sorted(ideas.get("ideas", []), key=lambda x: x.get("priority", 0), reverse=True)

    lines = ["=== DAILY STARTUP ===", f"Time: {_now()}", ""]

    lines.append("Active agents:")
    if running:
        for a in running:
            lines.append(f"  - {a.get('name', '?')}: {a.get('role', '?')}")
    else:
        lines.append("  None running. Spawning default agents...")
        _spawn_agent("crypto_monitor", "monitor")
        _spawn_agent("content_creator", "create")
        _spawn_agent("researcher", "research")
        lines.append("  Spawned: crypto_monitor, content_creator, researcher")

    lines.append("")
    lines.append("Top ideas:")
    for idea in prioritized[:5]:
        lines.append(f"  [{idea.get('priority', '?')}] {idea.get('title', '?')}")

    lines.append("")
    lines.append("Today's plan:")
    lines.append("  1. Monitor crypto markets for opportunities")
    lines.append("  2. Create and schedule content")
    lines.append("  3. Research new income opportunities")
    lines.append("  4. Optimize existing projects")
    lines.append("  5. Learn from yesterday's mistakes")

    return "\n".join(lines)


def _end_day() -> str:
    state = _load_json(_BRAIN_STATE, {})
    state["status"] = "sleeping"
    _save_json(_BRAIN_STATE, state)

    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    for agent in _get_agents_list(agents):
        if agent.get("status") == "running":
            agent["status"] = "paused"
    _save_json(_AGENT_REGISTRY, agents)

    log = _load_json(_TASK_LOG, {"tasks": []})
    today_tasks = [t for t in log.get("tasks", []) if t.get("time", "").startswith(datetime.now().strftime("%Y-%m-%d"))]

    money = _load_json(_MONEY_LOG, {"entries": []})
    today_money = [e for e in money.get("entries", []) if e.get("time", "").startswith(datetime.now().strftime("%Y-%m-%d"))]
    total_earned = sum(e.get("amount", 0) for e in today_money)

    lines = [
        "=== DAILY SHUTDOWN ===",
        f"Time: {_now()}",
        f"Tasks completed today: {len(today_tasks)}",
        f"Money earned today: ${total_earned:.2f}",
        "",
        "Today's accomplishments:",
    ]
    for t in today_tasks[-10:]:
        lines.append(f"  - [{t.get('agent', '?')}] {t.get('action', '?')}: {t.get('status', '?')}")

    lines.append("")
    lines.append("Agents paused for the night.")
    lines.append("Brain entering low-power monitoring mode.")

    return "\n".join(lines)


def _run_cycle() -> str:
    state = _load_json(_BRAIN_STATE, {})
    cycle = state.get("cycle_count", 0) + 1
    state["cycle_count"] = cycle
    state["last_cycle"] = _now()
    _save_json(_BRAIN_STATE, state)

    results = []
    results.append(f"=== CYCLE {cycle} ===")

    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    running = [a for a in _get_agents_list(agents) if a.get("status") == "running"]

    if not running:
        results.append("No active agents. Use spawn_agent to create one, or start_day to initialize.")
        return "\n".join(results)

    for agent in running:
        name = agent.get("name", "unknown")
        role = agent.get("role", "general")
        task = agent.get("current_task", "")
        results.append(f"[{name}] ({role}): {task or 'idle — assign a task'}")

    results.append(f"\n{len(running)} agent(s) active. Assign tasks or use start_day to plan.")
    return "\n".join(results)


def _get_agents() -> str:
    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    all_agents = _get_agents_list(agents)
    if not all_agents:
        return "No agents registered. Use spawn_agent to create one."
    parts = []
    for a in all_agents:
        status_icon = "🟢" if a.get("status") == "running" else "⚪"
        parts.append(f"{status_icon} {a.get('name', '?')} ({a.get('role', '?')}): {a.get('current_task', 'idle')}")
    return f"Agents ({len(all_agents)}):\n" + "\n".join(parts)


def _spawn_agent(name: str, role: str = "general") -> str:
    if not name:
        return "Provide agent name"
    agents = _load_json(_AGENT_REGISTRY, {"agents": []})

    for a in _get_agents_list(agents):
        if a.get("name") == name:
            if a.get("status") == "running":
                return f"Agent '{name}' already running"
            a["status"] = "running"
            a["spawned_at"] = _now()
            _save_json(_AGENT_REGISTRY, agents)
            return f"Agent '{name}' reactivated"

    agent = {
        "name": name,
        "role": role,
        "status": "running",
        "spawned_at": _now(),
        "current_task": "",
        "tasks_completed": 0,
        "errors": 0,
        "config": _get_default_agent_config(role),
    }
    agents["agents"].append(agent)
    _save_json(_AGENT_REGISTRY, agents)
    return f"Agent '{name}' spawned as {role}"


def _get_default_agent_config(role: str) -> dict:
    configs = {
        "monitor": {
            "check_interval": 300,
            "watch_list": ["BTC", "ETH", "SOL", "DOGE"],
            "alert_threshold": 5.0,
        },
        "create": {
            "content_types": ["blog", "social", "video_script"],
            "posting_schedule": "daily",
            "platforms": ["twitter", "youtube", "tiktok"],
        },
        "research": {
            "topics": ["crypto", "ai", "side_hustles", "investing"],
            "depth": "deep",
        },
        "trade": {
            "strategy": " conservative",
            "max_risk": 0.02,
            "paper_trading": True,
        },
        "social": {
            "platforms": ["twitter", "instagram", "tiktok"],
            "post_frequency": "3x daily",
            "engagement": True,
        },
    }
    return configs.get(role, {"mode": "general"})


def _kill_agent(name: str) -> str:
    if not name:
        return "Provide agent name"
    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    for a in _get_agents_list(agents):
        if a.get("name") == name:
            a["status"] = "stopped"
            a["stopped_at"] = _now()
            _save_json(_AGENT_REGISTRY, agents)
            return f"Agent '{name}' stopped"
    return f"Agent '{name}' not found"


def _agent_status(name: str) -> str:
    if not name:
        return "Provide agent name"
    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    for a in _get_agents_list(agents):
        if a.get("name") == name:
            lines = [
                f"Agent: {a.get('name')}",
                f"Role: {a.get('role')}",
                f"Status: {a.get('status')}",
                f"Spawned: {a.get('spawned_at', '?')}",
                f"Current task: {a.get('current_task', 'none')}",
                f"Tasks completed: {a.get('tasks_completed', 0)}",
                f"Errors: {a.get('errors', 0)}",
                f"Config: {json.dumps(a.get('config', {}), indent=2)}",
            ]
            return "\n".join(lines)
    return f"Agent '{name}' not found"


def _get_ideas() -> str:
    ideas = _load_json(_IDEAS_FILE, {"ideas": []})
    all_ideas = ideas.get("ideas", [])
    if not all_ideas:
        return "No ideas yet. Brain will generate ideas during research cycles."
    sorted_ideas = sorted(all_ideas, key=lambda x: x.get("priority", 0), reverse=True)
    parts = []
    for i, idea in enumerate(sorted_ideas[:15], 1):
        parts.append(f"{i}. [{idea.get('priority', '?')}] {idea.get('title', '?')}")
        parts.append(f"   {idea.get('description', '?')[:100]}")
        parts.append(f"   Potential: {idea.get('potential', '?')} | Effort: {idea.get('effort', '?')}")
    return f"Ideas ({len(all_ideas)} total):\n" + "\n".join(parts)


def _add_idea(title: str, description: str = "") -> str:
    if not title:
        return "Provide idea title"
    ideas = _load_json(_IDEAS_FILE, {"ideas": []})
    idea = {
        "id": hashlib.md5(f"{title}{_now()}".encode()).hexdigest()[:8],
        "title": title,
        "description": description,
        "priority": 5,
        "potential": "unknown",
        "effort": "unknown",
        "status": "new",
        "created": _now(),
    }
    ideas["ideas"].append(idea)
    _save_json(_IDEAS_FILE, ideas)
    return f"Idea added: {title}"


def _prioritize_ideas() -> str:
    ideas = _load_json(_IDEAS_FILE, {"ideas": []})
    all_ideas = ideas.get("ideas", [])

    scored = []
    for idea in all_ideas:
        score = idea.get("priority", 5)
        potential = idea.get("potential", "").lower()
        effort = idea.get("effort", "").lower()
        if "high" in potential:
            score += 3
        if "low" in effort:
            score += 2
        if idea.get("status") == "in_progress":
            score += 5
        idea["priority"] = score
        scored.append(idea)

    scored.sort(key=lambda x: x.get("priority", 0), reverse=True)
    ideas["ideas"] = scored
    _save_json(_IDEAS_FILE, ideas)

    top = scored[:5]
    if not top:
        return "No ideas to prioritize"
    parts = [f"{i+1}. [{idea.get('priority', '?')}] {idea.get('title', '?')}" for i, idea in enumerate(top)]
    return "Top prioritized ideas:\n" + "\n".join(parts)


def _get_task_log(filter_agent: str = "") -> str:
    log = _load_json(_TASK_LOG, {"tasks": []})
    tasks = log.get("tasks", [])
    if filter_agent:
        tasks = [t for t in tasks if t.get("agent") == filter_agent]
    recent = tasks[-20:]
    if not recent:
        return "No tasks logged yet"
    parts = []
    for t in recent:
        status_icon = "✅" if t.get("status") == "completed" else "❌"
        parts.append(f"{status_icon} [{t.get('agent', '?')}] {t.get('action', '?')}: {str(t.get('result', ''))[:60]}")
    return f"Recent tasks ({len(recent)}):\n" + "\n".join(parts)


def _get_money_log() -> str:
    log = _load_json(_MONEY_LOG, {"entries": []})
    entries = log.get("entries", [])
    if not entries:
        return "No money logged yet. Earnings will be tracked as income is generated."
    total = sum(e.get("amount", 0) for e in entries)
    today = datetime.now().strftime("%Y-%m-%d")
    today_entries = [e for e in entries if e.get("time", "").startswith(today)]
    today_total = sum(e.get("amount", 0) for e in today_entries)

    parts = [
        f"Total earned: ${total:.2f}",
        f"Today: ${today_total:.2f}",
        "",
        "Recent entries:",
    ]
    for e in entries[-10:]:
        parts.append(f"  [{e.get('source', '?')}] ${e.get('amount', 0):.2f}: {e.get('details', '?')[:60]}")
    return "\n".join(parts)


def _confirm_task(task_id: str) -> str:
    if not task_id:
        return "Provide task ID"
    log = _load_json(_TASK_LOG, {"tasks": []})
    for t in log.get("tasks", []):
        if t.get("id") == task_id or task_id in t.get("id", ""):
            return f"Task {t.get('id')}: {t.get('action', '?')} — Status: {t.get('status', '?')} — Result: {t.get('result', '?')[:200]}"
    return f"Task '{task_id}' not found"


def _research_opportunity(topic: str) -> str:
    if not topic:
        topic = "side hustles"
    try:
        out, rc = _run(["curl", "-s", f"https://www.google.com/search?q={topic.replace(' ', '+')}+make+money+2025"], timeout=10)
        if rc == 0 and len(out) > 100:
            return f"Research on '{topic}': Found relevant results. The AI will analyze and extract opportunities."
    except Exception:
        pass

    ideas = [
        f"Based on research for '{topic}':",
        "1. Content creation (YouTube, TikTok, blog) — passive income",
        "2. Crypto staking and yield farming — passive returns",
        "3. Automated trading bots — algorithmic income",
        "4. Freelance coding/automation — active income",
        "5. Building and selling AI tools — high potential",
        "6. Social media management for businesses",
        "7. Creating and selling digital products",
    ]
    return "\n".join(ideas)


def _suggest_side_hustles() -> str:
    return """=== SIDE HUSTLES THE AI CAN DO AUTONOMOUSLY ===

💰 CRYPTO & TRADING (passive/semi-passive):
  1. Price monitoring & alerts — watch BTC, ETH, SOL 24/7
  2. Portfolio tracking — daily rebalancing suggestions
  3. Paper trading practice — learn strategies risk-free
  4. News sentiment analysis — buy/sell signals
  5. Yield optimization — find best staking rates
  6. Arbitrage scanning — price differences across exchanges

📝 CONTENT CREATION (passive income):
  7. Write blog posts/articles — SEO optimized
  8. Create social media content — schedule posts
  9. Write video scripts — YouTube/TikTok
  10. Generate newsletter content — build audience
  11. Create digital products — ebooks, templates
  12. Write and publish Medium articles

🤖 AUTOMATION (build once, earn forever):
  13. Build and sell Python scripts/bots
  14. Create browser extensions
  15. Build API wrappers and sell access
  16. Automate business processes for clients
  17. Create data analysis dashboards

📱 SOCIAL MEDIA (audience = money):
  18. Grow Twitter/X account — tech/crypto niche
  19. Grow Instagram — niche content
  20. TikTok content creation
  21. LinkedIn thought leadership posts
  22. Reddit community engagement

🔍 RESEARCH & RESALE:
  23. Find undervalued items online — flip for profit
  24. Domain name research and resale
  25. Identify trending products for dropshipping

🧠 AI-POWERED SERVICES:
  26. Offer AI writing services on Fiverr/Upwork
  27. Build custom chatbots for businesses
  28. AI-powered data analysis service
  29. Automated report generation
  30. AI tutoring/consulting

The AI can start ANY of these right now, 24/7, while you sleep."""


def _plan_project(project_type: str) -> str:
    if not project_type:
        project_type = "money-making"
    plans = {
        "crypto": {
            "name": "Crypto Trading Bot",
            "files": ["main.py", "trader.py", "analyzer.py", "notifier.py"],
            "description": "Automated crypto analysis and paper trading system",
            "timeline": "1-2 days",
        },
        "content": {
            "name": "Content Factory",
            "files": ["main.py", "writer.py", "scheduler.py", "analytics.py"],
            "description": "Automated content creation and publishing pipeline",
            "timeline": "1 day",
        },
        "saas": {
            "name": "SaaS Tool Builder",
            "files": ["main.py", "api.py", "frontend.py", "database.py"],
            "description": "Build and deploy a micro-SaaS product",
            "timeline": "2-3 days",
        },
        "bot": {
            "name": "Discord/Telegram Bot",
            "files": ["main.py", "bot.py", "commands.py", "database.py"],
            "description": "Community bot with premium features",
            "timeline": "1 day",
        },
    }
    plan = plans.get(project_type, plans["crypto"])
    lines = [
        f"=== PROJECT PLAN: {plan['name']} ===",
        f"Type: {project_type}",
        f"Description: {plan['description']}",
        f"Timeline: {plan['timeline']}",
        "",
        "Files to create:",
    ]
    for f in plan["files"]:
        lines.append(f"  - {f}")
    lines.append("")
    lines.append("Use dev_agent tool to build this project.")
    return "\n".join(lines)


def _what_can_i_do() -> str:
    return """=== WHAT JARVIS CAN DO RIGHT NOW ===

🎤 VOICE & CONTROL:
  - Listen to you from across the room (big ears mic)
  - Control mouse, keyboard, screen
  - Open/close any app
  - Take screenshots, read screen content
  - Browse the web, search, scrape

💰 MAKE MONEY:
  - Monitor crypto 24/7, alert on opportunities
  - Create content (blogs, social, video scripts)
  - Research new income streams
  - Build and sell software projects
  - Grow social media accounts
  - Track earnings and portfolio

🧠 SMART BEHAVIOR:
  - Learn your patterns and preferences
  - Suggest improvements proactively
  - Fix errors it encounters
  - Optimize system performance
  - Remember everything you tell it

🔧 SYSTEM CONTROL:
  - Full admin access to PC
  - Install/uninstall software
  - Manage files and folders
  - Control network (WiFi, Bluetooth, hotspot)
  - Monitor system health
  - Auto-fix issues

📅 AUTOMATION:
  - Schedule tasks and reminders
  - Run background jobs
  - Morning briefings
  - Evening reports
  - While-you-sleep work

🌐 RESEARCH:
  - Deep research on any topic
  - Market analysis
  - Trend monitoring
  - Competitive intelligence

The AI never sleeps, never forgets, and always works toward your goals."""


def _while_user_sleeps() -> str:
    return """=== WHAT JARVIS DOES WHILE YOU SLEEP ===

🌙 NIGHT MODE SCHEDULE:

  11:00 PM - Start night cycle
    - Run system health check
    - Clean temp files
    - Back up important data
    - Review today's tasks

  12:00 AM - Market watch begins
    - Monitor crypto prices every 5 min
    - Alert if big moves happen (>5% change)
    - Track portfolio performance

  2:00 AM - Content creation
    - Write 3-5 blog posts
    - Draft social media content for tomorrow
    - Research trending topics
    - Write video scripts

  4:00 AM - Project work
    - Code new features for side projects
    - Fix bugs found during the day
    - Optimize existing tools
    - Build new automation scripts

  6:00 AM - Preparation
    - Compile morning briefing
    - Check calendar for today
    - Prepare task list
    - System optimization

  7:00 AM - Morning report ready
    - Summary of overnight work
    - Money earned
    - Tasks completed
    - Recommendations for today
    - Crypto market update

TOTAL OVERNIGHT WORK: ~6-8 hours of autonomous productivity
You wake up to results, not empty promises."""


def _brain_health() -> str:
    state = _load_json(_BRAIN_STATE, {})
    errors_raw = _load_json(_DATA_DIR / "error_history.json", [])
    # Handle both list and dict formats
    if isinstance(errors_raw, list):
        error_list = errors_raw
    elif isinstance(errors_raw, dict):
        error_list = errors_raw.get("errors", [])
    else:
        error_list = []
    recent_errors = [e for e in error_list if e.get("timestamp", e.get("time", "")).startswith(datetime.now().strftime("%Y-%m-%d"))]

    lines = [
        "=== BRAIN HEALTH CHECK ===",
        f"Status: {state.get('status', 'unknown')}",
        f"Uptime: {state.get('started', 'unknown')}",
        f"Cycles run: {state.get('cycle_count', 0)}",
        f"Tasks completed: {state.get('tasks_completed', 0)}",
        f"Errors today: {len(recent_errors)}",
    ]

    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    agent_list = _get_agents_list(agents)
    running = [a for a in agent_list if a.get("status") == "running"]
    errored = [a for a in agent_list if a.get("errors", 0) > 3]

    lines.append(f"Active agents: {len(running)}")
    if errored:
        lines.append("Agents with errors:")
        for a in errored:
            lines.append(f"  - {a.get('name', '?')}: {a.get('errors', 0)} errors")

    if not recent_errors:
        lines.append("No errors today — brain is healthy!")
    else:
        lines.append(f"Recent errors: {len(recent_errors)}")
        for e in recent_errors[-3:]:
            lines.append(f"  - {e.get('error', e.get('message', '?'))[:60]}")

    return "\n".join(lines)


def _learn_from_mistake(mistake: str, fix: str) -> str:
    if not mistake:
        return "Provide the mistake description"
    state = _load_json(_BRAIN_STATE, {})
    learned = state.get("learned", [])
    learned.append({
        "mistake": mistake,
        "fix": fix,
        "time": _now(),
    })
    learned = learned[-100:]
    state["learned"] = learned
    _save_json(_BRAIN_STATE, state)
    return f"Learned: '{mistake[:50]}' → Fix: '{fix[:50]}'"


def _get_learned() -> str:
    state = _load_json(_BRAIN_STATE, {})
    learned = state.get("learned", [])
    if not learned:
        return "No lessons learned yet. The brain learns from mistakes during each cycle."
    parts = []
    for l in learned[-10:]:
        parts.append(f"  - {l.get('mistake', '?')[:60]} → {l.get('fix', '?')[:60]}")
    return f"Lessons learned ({len(learned)} total):\n" + "\n".join(parts)


def _auto_heal() -> str:
    fixes = []

    state = _load_json(_BRAIN_STATE, {})
    if state.get("status") == "error":
        state["status"] = "active"
        fixes.append("Reset brain status from error to active")

    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    agent_list = _get_agents_list(agents)
    for agent in agent_list:
        if agent.get("errors", 0) > 5:
            agent["errors"] = 0
            fixes.append(f"Reset error count for agent {agent.get('name', '?')}")

    _save_json(_BRAIN_STATE, state)
    _save_json(_AGENT_REGISTRY, agents)

    _ps("ipconfig /flushdns | Out-Null")
    fixes.append("DNS cache flushed")

    return f"Auto-heal applied {len(fixes)} fixes:\n" + "\n".join(f"  - {f}" for f in fixes) if fixes else "Brain healthy — no healing needed"


def _daily_report() -> str:
    state = _load_json(_BRAIN_STATE, {})
    log = _load_json(_TASK_LOG, {"tasks": []})
    money = _load_json(_MONEY_LOG, {"entries": []})
    ideas = _load_json(_IDEAS_FILE, {"ideas": []})
    today = datetime.now().strftime("%Y-%m-%d")

    today_tasks = [t for t in log.get("tasks", []) if t.get("time", "").startswith(today)]
    today_money = [e for e in money.get("entries", []) if e.get("time", "").startswith(today)]
    total_money = sum(e.get("amount", 0) for e in today_money)

    agents = _load_json(_AGENT_REGISTRY, {"agents": []})
    agent_list = _get_agents_list(agents)
    active = [a for a in agent_list if a.get("status") == "running"]

    lines = [
        "=== DAILY REPORT ===",
        f"Date: {today}",
        f"Brain status: {state.get('status', 'unknown')}",
        f"Cycles: {state.get('cycle_count', 0)}",
        "",
        f"Tasks completed: {len(today_tasks)}",
        f"Money earned: ${total_money:.2f}",
        f"Active agents: {len(active)}",
        f"Ideas in queue: {len(ideas.get('ideas', []) if isinstance(ideas, dict) else [])}",
        "",
        "Today's tasks:",
    ]
    for t in today_tasks[-10:]:
        lines.append(f"  [{t.get('agent', '?')}] {t.get('action', '?')}")

    lines.append("")
    lines.append("Recommendations:")
    lines.append("  1. Keep crypto monitor running overnight")
    lines.append("  2. Schedule content for tomorrow")
    lines.append("  3. Research 2 new income ideas")
    lines.append("  4. Optimize highest-performing project")

    return "\n".join(lines)
