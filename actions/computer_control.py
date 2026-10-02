"""
Computer Control Agent — Part 3.1: Full desktop automation.
Launching, closing, controlling applications; file operations; scheduling; RPA.
"""
import asyncio
import os
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.domain_agent import DomainAgent, DomainConfig, AutonomyLevel
from core.safety_guardian import is_killed, log_audit, is_breaker_tripped
from core.audit_log import write_audit_entry

class ComputerControlAgent(DomainAgent):
    """Full computer control: apps, files, scheduling, RPA."""
    
    def __init__(self):
        config = DomainConfig(
            domain="computer_control",
            autonomy_level=1,
            target_ceiling=5,
            caps={
                "max_file_ops_per_min": 100,
                "max_app_launches_per_min": 10,
                "allowed_dirs": ["~/Documents", "~/Downloads", "~/Desktop", "~/Projects", "~/jarvis_workspace"]
            },
            always_requires_approval=[
                "delete_file", "delete_dir", "format_disk", "modify_system_files",
                "install_software", "modify_registry", "run_as_admin"
            ],
            allowlist=[
                "notepad.exe", "code.exe", "python.exe", "cmd.exe", "powershell.exe",
                "chrome.exe", "firefox.exe", "explorer.exe", "notepad++.exe",
                "sublime_text.exe", "vim.exe", "git.exe", "npm.exe", "pip.exe"
            ]
        )
        super().__init__(config)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._file_op_count = 0
        self._last_minute = time.time()
        
    async def handle(self, action: str, params: Dict) -> Any:
        """Handle computer control actions."""
        if is_killed("computer_control"):
            raise PermissionError("Computer control domain is killed by safety guardian")
            
        can_exec, needs_approval, reason = self.can_execute(action)
        if not can_exec:
            return {"success": False, "error": reason, "requires_approval": False}
            
        if self.config.autonomy_level < 3 and not self._check_approval(params):
            return {"success": False, "error": "Requires Boss approval", "requires_approval": True}
            
        # Check circuit breakers
        if is_breaker_tripped("scope_commands_per_min"):
            return {"success": False, "error": "Rate limit exceeded"}
            
        try:
            if action == "launch_app":
                return await self._launch_app(params)
            elif action == "close_app":
                return await self._close_app(params)
            elif action == "run_command":
                return await self._run_command(params)
            elif action == "create_file":
                return await self._create_file(params)
            elif action == "read_file":
                return await self._read_file(params)
            elif action == "write_file":
                return await self._write_file(params)
            elif action == "delete_file":
                return await self._delete_file(params)
            elif action == "list_dir":
                return await self._list_dir(params)
            elif action == "create_dir":
                return await self._create_dir(params)
            elif action == "schedule_task":
                return await self._schedule_task(params)
            elif action == "take_screenshot":
                return await self._take_screenshot(params)
            elif action == "get_system_info":
                return await self._get_system_info()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _check_approval(self, params: Dict) -> bool:
        """Check if action has Boss approval."""
        return params.get("approved", False) or params.get("approved_by_boss", False)
        
    async def _launch_app(self, params: Dict) -> Dict:
        app = params.get("app")
        args = params.get("args", [])
        
        if not self.config.allowlist or params.get("approved", False):
            pass  # Approved or no allowlist
        elif not self._is_allowed(app):
            return {"success": False, "error": f"App not in allowlist: {app}", "requires_approval": True}
            
        try:
            proc = await asyncio.create_subprocess_exec(
                app, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            return {"success": True, "pid": proc.pid, "app": app}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _is_allowed(self, app: str) -> bool:
        app_lower = app.lower()
        for allowed in self.config.allowlist:
            if allowed.lower() in app_lower or app_lower in allowed.lower():
                return True
        return False
        
    async def _close_app(self, params: Dict) -> Dict:
        app = params.get("app")
        try:
            proc = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/IM", app,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            return {"success": True, "app": app}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _run_command(self, params: Dict) -> Dict:
        cmd = params.get("command")
        cwd = params.get("cwd", ".")
        shell = params.get("shell", False)
        
        if not self._check_rate_limit():
            return {"success": False, "error": "Rate limit exceeded"}
            
        try:
            if shell:
                proc = await asyncio.create_subprocess_shell(
                    cmd, cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                parts = cmd.split()
                proc = await asyncio.create_subprocess_exec(
                    parts[0], *parts[1:], cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            stdout, stderr = await proc.communicate()
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout.decode(errors="replace")[:5000],
                "stderr": stderr.decode(errors="replace")[:5000]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _check_rate_limit(self) -> bool:
        now = time.time()
        if now - self._last_minute > 60:
            self._file_op_count = 0
            self._last_minute = now
        if self._file_op_count >= self.config.caps.get("max_file_ops_per_min", 100):
            return False
        self._file_op_count += 1
        return True
        
    async def _create_file(self, params: Dict) -> Dict:
        path = Path(params.get("path", ""))
        content = params.get("content", "")
        
        if not self._is_allowed_path(path):
            return {"success": False, "error": "Path not in allowed directories", "requires_approval": True}
            
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(params.get("content", ""), encoding="utf-8")
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _read_file(self, params: Dict) -> Dict:
        path = Path(params.get("path", ""))
        try:
            content = path.read_text(encoding="utf-8")
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _write_file(self, params: Dict) -> Dict:
        return await self._create_file(params)
        
    async def _delete_file(self, params: Dict) -> Dict:
        path = Path(params.get("path", ""))
        if not params.get("approved", False):
            return {"success": False, "error": "Delete requires Boss approval", "requires_approval": True}
        try:
            path.unlink()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _list_dir(self, params: Dict) -> Dict:
        path = Path(params.get("path", "."))
        try:
            items = []
            for p in path.iterdir():
                items.append({
                    "name": p.name,
                    "type": "dir" if p.is_dir() else "file",
                    "size": p.stat().st_size if p.is_file() else None
                })
            return {"success": True, "items": items}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _create_dir(self, params: Dict) -> Dict:
        path = Path(params.get("path", ""))
        try:
            path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _schedule_task(self, params: Dict) -> Dict:
        # Simple scheduling - in production would use proper scheduler
        return {"success": True, "scheduled": True}
        
    async def _take_screenshot(self, params: Dict) -> Dict:
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            path = Path(params.get("path", "screenshot.png"))
            screenshot.save(path)
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _get_system_info(self) -> Dict:
        import psutil
        return {
            "success": True,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "boot_time": psutil.boot_time()
        }
        
    def _is_allowed_path(self, path: Path) -> bool:
        allowed = self.config.caps.get("allowed_dirs", [])
        if not allowed:
            return True
        try:
            path.resolve()
            for allowed_dir in allowed:
                allowed_path = Path(os.path.expanduser(allowed_dir)).resolve()
                try:
                    path.relative_to(allowed_path)
                    return True
                except ValueError:
                    continue
        except Exception:
            pass
        return False
        
    def get_status(self) -> Dict:
        return {
            "domain": "computer_control",
            "autonomy_level": 1,
            "target_ceiling": 5,
            "running_tasks": len(self._running_tasks),
            "file_ops_this_minute": self._file_op_count
        }
        
    def get_proposals(self) -> List[Dict]:
        return []  # Would return pending proposals
        
    def get_status(self) -> Dict:
        return {
            "domain": "computer_control",
            "autonomy_level": 1,
            "target_ceiling": 5,
            "running_tasks": len(self._running_tasks),
            "file_ops_this_minute": self._file_op_count
        }
        
    def get_proposals(self) -> List[Dict]:
        return []


_computer_control_agent: ComputerControlAgent | None = None


def handle_computer_control(parameters: Dict | None = None, response=None, player=None, session_memory=None) -> Dict[str, Any]:
    """Synchronous tool entry point for the async desktop-control agent."""
    global _computer_control_agent
    params = dict(parameters or {})
    action = str(params.pop("action", "")).strip().lower()
    if not action:
        return {"success": False, "error": "Choose a computer-control action."}

    if _computer_control_agent is None:
        _computer_control_agent = ComputerControlAgent()
    try:
        return asyncio.run(_computer_control_agent.handle(action, params))
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def computer_control(parameters: Dict | None = None, response=None, player=None, session_memory=None) -> Dict[str, Any]:
    """Route the dashboard's declared desktop controls through guarded helpers."""
    params = dict(parameters or {})
    action = str(params.get("action", "")).strip().lower()
    if not action:
        return {"success": False, "error": "Choose a computer-control action."}
    from core.qa_mode import guard_tool_call, qa_block_message
    decision = guard_tool_call("computer_control", params)
    if not decision.allowed:
        return {"success": False, "error": qa_block_message(decision)}

    if action in {"type", "smart_type", "paste"}:
        text = params.get("text")
        if not isinstance(text, str) or not text:
            return {"success": False, "error": "Provide non-empty text to type."}
        try:
            from actions.safe_text_entry import safe_type_text
            result = safe_type_text(
                text,
                purpose="generic",
                clear_first=bool(params.get("clear_first", action == "smart_type")),
            )
            return {"success": result.ok, "message": result.message}
        except Exception as exc:
            return {"success": False, "error": f"Text entry failed: {type(exc).__name__}: {exc}"}

    if action == "random_data":
        kind = str(params.get("type", "")).strip().lower()
        if kind not in {"password", "token", "hex"}:
            return {"success": False, "error": "Supported synthetic data types: password, token, hex."}
        value = secrets.token_urlsafe(24) if kind in {"password", "token"} else secrets.token_hex(16)
        return {"success": True, "type": kind, "value": value}
    if action == "user_data":
        return {"success": False, "error": "No local user profile is configured; personal data was not invented."}

    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        if action == "press":
            key = str(params.get("key", "")).strip().lower()
            allowed = {
                "enter", "return", "tab", "escape", "esc", "backspace", "delete", "space",
                "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
                "ctrl", "alt", "shift", "win", "command", "f1", "f2", "f3", "f4", "f5",
                "f6", "f7", "f8", "f9", "f10", "f11", "f12",
            }
            if key not in allowed:
                return {"success": False, "error": "This key is not in the supported single-key allowlist."}
            pyautogui.press(key)
            return {"success": True, "message": f"Pressed {key}."}
        if action == "hotkey":
            keys = str(params.get("keys", "")).strip().lower().replace("+", " ").split()
            allowed = {"ctrl", "alt", "shift", "win", "command", "enter", "tab", "escape", "esc", "c", "v", "x", "a", "z", "y", "s", "f", "w", "t", "r", "left", "right", "up", "down"}
            if len(keys) < 2 or len(keys) > 4 or any(key not in allowed for key in keys):
                return {"success": False, "error": "Use a supported hotkey combination such as ctrl+c or alt+tab."}
            pyautogui.hotkey(*keys)
            return {"success": True, "message": f"Pressed {'+'.join(keys)}."}
        if action == "wait":
            seconds = float(params.get("seconds", 1))
            if not 0 <= seconds <= 10:
                return {"success": False, "error": "Wait duration must be between 0 and 10 seconds."}
            time.sleep(seconds)
            return {"success": True, "waited_seconds": seconds}
        if action == "scroll":
            direction = str(params.get("direction", "down")).lower()
            amount = max(1, min(10, int(params.get("amount", 3))))
            if direction not in {"up", "down"}:
                return {"success": False, "error": "Scroll direction must be up or down."}
            pyautogui.scroll(amount if direction == "up" else -amount)
            return {"success": True, "message": f"Scrolled {direction} {amount} steps."}
        if action == "move":
            x, y = int(params.get("x", -1)), int(params.get("y", -1))
            width, height = pyautogui.size()
            if not 0 <= x < width or not 0 <= y < height:
                return {"success": False, "error": "Mouse coordinates are outside the screen."}
            pyautogui.moveTo(x, y, duration=0.15)
            return {"success": True, "message": f"Moved pointer to ({x}, {y})."}
        if action == "clear_field":
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            return {"success": True, "message": "Cleared the focused field."}
        if action == "copy":
            pyautogui.hotkey("ctrl", "c")
            return {"success": True, "message": "Copied the current selection."}
        if action == "click":
            x, y = int(params.get("x", -1)), int(params.get("y", -1))
            width, height = pyautogui.size()
            if not 0 <= x < width or not 0 <= y < height:
                return {"success": False, "error": "Click coordinates are outside the screen."}
            pyautogui.click(x, y)
            return {"success": True, "message": f"Clicked ({x}, {y})."}
        if action in {"double_click", "right_click"}:
            x, y = int(params.get("x", -1)), int(params.get("y", -1))
            width, height = pyautogui.size()
            if not 0 <= x < width or not 0 <= y < height:
                return {"success": False, "error": "Click coordinates are outside the screen."}
            pyautogui.doubleClick(x, y) if action == "double_click" else pyautogui.rightClick(x, y)
            return {"success": True, "message": f"{action.replace('_', ' ').title()} at ({x}, {y})."}
    except Exception as exc:
        return {"success": False, "error": f"Desktop action failed: {type(exc).__name__}: {exc}"}

    target = str(params.get("description", params.get("title", "")))
    screen_actions = {
        "screenshot": "screenshot",
        "focus_window": "focus_window",
        "screen_find": "find_on_screen",
        "screen_click": "click_on_text",
    }
    if action in screen_actions:
        try:
            from actions.screen_automation import handle as screen_handle
            result = screen_handle({"action": screen_actions[action], "target": params.get("path", "") if action == "screenshot" else target})
            failed = isinstance(result, str) and (result.startswith("Unknown action:") or "failed:" in result.lower() or "not installed" in result.lower())
            return {"success": not failed, "result": result}
        except Exception as exc:
            return {"success": False, "error": f"Screen action failed: {type(exc).__name__}: {exc}"}
    return {"success": False, "error": f"Unsupported computer-control action: {action}"}
