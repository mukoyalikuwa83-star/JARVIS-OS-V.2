"""Learning memory — tracks user patterns, preferences, workflows, and context over time."""

import json
import time
from pathlib import Path
from collections import defaultdict


_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE_DIR / ".jarvis"
_PREFS_FILE = _MEMORY_DIR / "user_preferences.json"
_PATTERNS_FILE = _MEMORY_DIR / "learned_patterns.json"
_CONTEXT_FILE = _MEMORY_DIR / "active_context.json"
_WORKFLOWS_FILE = _MEMORY_DIR / "learned_workflows.json"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, data: dict):
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_prefs() -> dict:
    return _load_json(_PREFS_FILE)


def _save_prefs(data: dict):
    _save_json(_PREFS_FILE, data)


def _load_patterns() -> dict:
    return _load_json(_PATTERNS_FILE)


def _save_patterns(data: dict):
    _save_json(_PATTERNS_FILE, data)


def _load_context() -> dict:
    return _load_json(_CONTEXT_FILE)


def _save_context(data: dict):
    _save_json(_CONTEXT_FILE, data)


def _load_workflows() -> dict:
    return _load_json(_WORKFLOWS_FILE)


def _save_workflows(data: dict):
    _save_json(_WORKFLOWS_FILE, data)


def remember_preference(key: str, value: str) -> str:
    """Store a user preference."""
    prefs = _load_prefs()
    prefs[key] = {"value": value, "updated": time.strftime("%Y-%m-%d %H:%M")}
    _save_prefs(prefs)
    return f"REMEMBERED|{key} = {value}"


def get_preference(key: str) -> str:
    """Get a stored preference."""
    prefs = _load_prefs()
    entry = prefs.get(key)
    if entry:
        return f"{key} = {entry['value']} (set {entry.get('updated', 'unknown')})"
    return f"NO_PREF|{key} not found"


def list_preferences() -> str:
    """List all stored preferences."""
    prefs = _load_prefs()
    if not prefs:
        return "No preferences stored yet."
    lines = [f"  {k}: {v['value']}" for k, v in prefs.items()]
    return f"USER PREFERENCES ({len(prefs)}):\n" + "\n".join(lines)


def track_pattern(action: str, context: str = "", result: str = "success") -> str:
    """Track a user action pattern for learning."""
    patterns = _load_patterns()
    hour = time.strftime("%H")
    day = time.strftime("%A")

    key = f"{action}:{context}" if context else action
    if key not in patterns:
        patterns[key] = {
            "count": 0,
            "first_seen": time.strftime("%Y-%m-%d %H:%M"),
            "times": [],
            "results": defaultdict(int),
        }

    entry = patterns[key]
    entry["count"] = entry.get("count", 0) + 1
    entry["last_seen"] = time.strftime("%Y-%m-%d %H:%M")
    entry["times"].append(f"{day} {hour}:00")
    if len(entry["times"]) > 50:
        entry["times"] = entry["times"][-50:]
    entry["results"][result] = entry.get("results", {}).get(result, 0) + 1

    _save_patterns(patterns)
    return f"TRACKED|{action} (total: {entry['count']})"


def get_pattern_insight(action: str) -> str:
    """Get insights about a pattern."""
    patterns = _load_patterns()
    key = action
    for k in patterns:
        if k.startswith(action):
            key = k
            break
    else:
        return f"No pattern data for '{action}'."

    entry = patterns[key]
    count = entry.get("count", 0)
    times = entry.get("times", [])
    results = entry.get("results", {})

    most_common_time = max(set(times), key=times.count) if times else "unknown"
    success_rate = results.get("success", 0) / max(count, 1) * 100

    return (
        f"PATTERN '{action}':\n"
        f"  Used {count} times\n"
        f"  Most common: {most_common_time}\n"
        f"  Success rate: {success_rate:.0f}%\n"
        f"  Last seen: {entry.get('last_seen', 'unknown')}"
    )


def set_context(key: str, value: str) -> str:
    """Set active context (current project, task, etc.)."""
    ctx = _load_context()
    ctx[key] = {"value": value, "updated": time.strftime("%Y-%m-%d %H:%M")}
    _save_context(ctx)
    return f"CONTEXT_SET|{key} = {value}"


def get_context(key: str = "") -> str:
    """Get active context."""
    ctx = _load_context()
    if not ctx:
        return "No active context."
    if key:
        entry = ctx.get(key)
        if entry:
            return f"{key} = {entry['value']}"
        return f"No context for '{key}'."
    lines = [f"  {k}: {v['value']}" for k, v in ctx.items()]
    return f"ACTIVE CONTEXT ({len(ctx)}):\n" + "\n".join(lines)


def clear_context(key: str = "") -> str:
    """Clear context."""
    ctx = _load_context()
    if key:
        if key in ctx:
            del ctx[key]
            _save_context(ctx)
            return f"CONTEXT_CLEARED|{key}"
        return f"No context for '{key}'."
    _save_context({})
    return "ALL_CONTEXT_CLEARED"


def save_workflow(name: str, steps: list[dict]) -> str:
    """Save a learned workflow."""
    workflows = _load_workflows()
    workflows[name] = {
        "steps": steps,
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "run_count": 0,
    }
    _save_workflows(workflows)
    return f"WORKFLOW_SAVED|{name} ({len(steps)} steps)"


def get_workflow(name: str) -> str:
    """Get a workflow."""
    workflows = _load_workflows()
    wf = workflows.get(name)
    if not wf:
        return f"No workflow '{name}'."
    steps = wf.get("steps", [])
    lines = [f"  {i+1}. {s.get('action', '?')}: {s.get('target', '') or s.get('description', '')}" for i, s in enumerate(steps)]
    return f"WORKFLOW '{name}' ({len(steps)} steps, run {wf.get('run_count', 0)} times):\n" + "\n".join(lines)


def list_workflows() -> str:
    """List all workflows."""
    workflows = _load_workflows()
    if not workflows:
        return "No workflows saved."
    lines = [f"  {name}: {len(wf.get('steps', []))} steps (run {wf.get('run_count', 0)} times)" for name, wf in workflows.items()]
    return f"WORKFLOWS ({len(workflows)}):\n" + "\n".join(lines)


def run_workflow(name: str) -> str:
    """Mark a workflow as run."""
    workflows = _load_workflows()
    if name not in workflows:
        return f"No workflow '{name}'."
    workflows[name]["run_count"] = workflows[name].get("run_count", 0) + 1
    workflows[name]["last_run"] = time.strftime("%Y-%m-%d %H:%M")
    _save_workflows(workflows)
    steps = workflows[name].get("steps", [])
    return json.dumps({"workflow": name, "steps": steps}, ensure_ascii=False)


def delete_workflow(name: str) -> str:
    """Delete a workflow."""
    workflows = _load_workflows()
    if name in workflows:
        del workflows[name]
        _save_workflows(workflows)
        return f"WORKFLOW_DELETED|{name}"
    return f"No workflow '{name}'."


def handle(params: dict) -> str:
    """Tool handler."""
    action = str(params.get("action", "list") or "list").lower()

    if action == "remember":
        return remember_preference(str(params.get("key", "") or ""), str(params.get("value", "") or ""))
    elif action == "get_pref":
        return get_preference(str(params.get("key", "") or ""))
    elif action == "list_prefs":
        return list_preferences()
    elif action == "track":
        return track_pattern(str(params.get("action_name", "") or params.get("target", "") or ""),
                           str(params.get("context", "") or ""))
    elif action == "insight":
        return get_pattern_insight(str(params.get("action_name", "") or params.get("target", "") or ""))
    elif action == "set_context":
        return set_context(str(params.get("key", "") or ""), str(params.get("value", "") or ""))
    elif action == "get_context":
        return get_context(str(params.get("key", "") or ""))
    elif action == "clear_context":
        return clear_context(str(params.get("key", "") or ""))
    elif action == "save_workflow":
        steps = params.get("steps", [])
        return save_workflow(str(params.get("name", "") or ""), steps if isinstance(steps, list) else [])
    elif action == "get_workflow":
        return get_workflow(str(params.get("name", "") or ""))
    elif action == "list_workflows":
        return list_workflows()
    elif action == "run_workflow":
        return run_workflow(str(params.get("name", "") or ""))
    elif action == "delete_workflow":
        return delete_workflow(str(params.get("name", "") or ""))
    return f"Unknown action: {action}. Valid: remember, get_pref, list_prefs, track, insight, set_context, get_context, clear_context, save_workflow, get_workflow, list_workflows, run_workflow, delete_workflow"
