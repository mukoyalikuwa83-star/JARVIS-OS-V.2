import os, glob
for f in glob.glob("*.py") + glob.glob("*.ps1") + glob.glob("*.bat"):
    if f in ("main.py", "ui.py", "watchdog.py", "test_all_tools.py"):
        continue
    if f.startswith("test_") or f in ("count_tools.py", "do_commit.py", "do_push.py", "install_stripe.py", "launch_jarvis.py", "launch_sub.py", "setup_shortcuts.ps1", "start_jarvis.bat", "update_shortcut.ps1", "verify_all.py"):
        try:
            os.remove(f)
            print(f"Removed: {f}")
        except:
            pass
