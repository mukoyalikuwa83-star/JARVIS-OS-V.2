"""Headless worker — runs JARVIS money-making pipeline without the GUI.

Independently executes:
  - Full brain cycle (job scanning via Playwright, builds, Gumroad sales check, balance)
  - Storefront deploy + git push
  - No Gemini Live, no UI, no audio
"""
import time, sys, os, json, traceback, signal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

DATA = ROOT / ".jarvis"
STOP_FILE = DATA / ".stop"
LOG_FILE = DATA / "worker_headless.log"

FULL_CYCLE_INT = 90
BUILD_INT = 120
DEPLOY_INT = 180

_running = True

def _log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def _should_stop():
    return STOP_FILE.exists()

def _shutdown(sig, frame):
    global _running
    _running = False
    _log("Received shutdown signal")

signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)

def _run_cycle():
    from actions.autonomous_brain import handle as bh
    return bh({"action": "run_full_cycle"})

def _do_build():
    from actions.autonomous_worker import AutonomousWorker
    import random
    aw = AutonomousWorker()
    work_types = ["python_script", "web_scraper", "cli_tool", "flask_api",
                  "automation_script", "data_pipeline", "saas_template"]
    wt = random.choice(work_types)
    return aw.do_work(wt, f"Auto-built {wt}")

def _do_deploy():
    from actions.autonomous_worker import AutonomousWorker
    aw = AutonomousWorker()
    return aw.deploy()

def _do_sales_check():
    from actions.gumroad_api import record_gumroad_sales
    return record_gumroad_sales()

def _status_line():
    try:
        rev = json.loads((DATA / "revenue.json").read_text(encoding="utf-8"))
        pending = json.loads((DATA / "worker_pending.json").read_text(encoding="utf-8"))
        active_jobs = [p for p in pending if p.get("status") == "pending"]
        return f"bal=${rev['balance']} withdrawn=${rev['total_withdrawn']} tx={len(rev['transactions'])} pending_jobs={len(active_jobs)}"
    except Exception:
        return "status unavailable"

def main():
    global _running
    _log("Headless worker starting")
    _log(f"Intervals: cycle={FULL_CYCLE_INT}s build={BUILD_INT}s deploy={DEPLOY_INT}s")

    last_build = 0
    last_deploy = 0
    last_full_cycle = 0
    cycle_count = 0

    while _running:
        if _should_stop():
            reason = STOP_FILE.read_text(encoding="utf-8").strip()
            _log(f"STOP file found: {reason}")
            break

        time.sleep(15)
        now = time.time()

        # Build product
        if now - last_build > BUILD_INT:
            last_build = now
            try:
                r = _do_build()
                _log(f"BUILD: {str(r)[:80]}")
            except Exception as e:
                _log(f"BUILD error: {e}")

        # Deploy store
        if now - last_deploy > DEPLOY_INT:
            last_deploy = now
            try:
                r = _do_deploy()
                _log(f"DEPLOY: {str(r)[:80]}")
            except Exception as e:
                _log(f"DEPLOY error: {e}")

        # Full brain cycle (job scan + Gumroad sales + balance)
        if now - last_full_cycle > FULL_CYCLE_INT:
            last_full_cycle = now
            cycle_count += 1
            try:
                r = _run_cycle()
                lines = [l.strip() for l in r.split("\n") if l.strip() and not l.startswith("=")]
                _log(f"CYCLE {cycle_count}: {lines[0] if lines else 'done'}")
                for l in lines[1:4]:
                    _log(f"  {l[:100]}")
            except Exception as e:
                _log(f"CYCLE error: {e}")
                traceback.print_exc()

            # Sales check
            try:
                sr = _do_sales_check()
                _log(f"SALES: {sr}")
            except Exception as e:
                _log(f"SALES error: {e}")

            _log(f"STATUS: {_status_line()}")

    _log("Headless worker stopped")

if __name__ == "__main__":
    main()
