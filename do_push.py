import subprocess
r1 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "add", "-A"], capture_output=True, text=True, timeout=30)
r2 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "commit", "-m", "Fix phone_tracking bug, verify shortcuts work, 67/67 tests pass"], capture_output=True, text=True, timeout=30)
print("COMMIT:", r2.returncode)
r3 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "push", "origin", "main"], capture_output=True, text=True, timeout=60)
print("PUSH:", r3.returncode)
