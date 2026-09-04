import os
for f in ["full_test.py", "check_shortcut.py"]:
    try:
        os.remove(f)
        print(f"Removed: {f}")
    except:
        pass
