"""Brain for crypto_agent — autonomous sub-agent."""

import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

AGENT_NAME = "crypto_agent"
PURPOSE = "Monitor crypto prices"


class AgentBrain:
    def __init__(self):
        self.state_file = DATA_DIR / f"{AGENT_NAME}_state.json"
        self.log_file = DATA_DIR / f"{AGENT_NAME}_log.json"
        self.state = self._load_state()

    def _load_state(self):
        try:
            if self.state_file.exists():
                return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {
            "name": AGENT_NAME,
            "purpose": PURPOSE,
            "status": "active",
            "created": datetime.now().isoformat(),
            "tasks_completed": 0,
            "errors": 0,
            "learnings": [],
        }

    def _save_state(self):
        try:
            self.state_file.write_text(json.dumps(self.state, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    def log(self, message):
        entry = {"time": datetime.now().isoformat(), "message": message}
        try:
            entries = []
            if self.log_file.exists():
                entries = json.loads(self.log_file.read_text(encoding="utf-8"))
            entries.append(entry)
            entries = entries[-1000:]
            self.log_file.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    def execute(self, task):
        self.log(f"Executing: {task}")
        self.state["tasks_completed"] = self.state.get("tasks_completed", 0) + 1
        self._save_state()
        return f"{AGENT_NAME} completed: {task}"

    def learn(self, observation):
        self.state.setdefault("learnings", []).append({
            "observation": observation,
            "time": datetime.now().isoformat(),
        })
        self.state["learnings"] = self.state["learnings"][-100:]
        self._save_state()
        self.log(f"Learned: {observation}")

    def status(self):
        return json.dumps(self.state, indent=2, default=str)


if __name__ == "__main__":
    brain = AgentBrain()
    print(brain.status())
