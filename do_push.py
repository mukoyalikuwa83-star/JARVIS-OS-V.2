import subprocess
r1 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "add", "-A"], capture_output=True, text=True, timeout=30)
r2 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "commit", "-m", "Clean up test/temp files"], capture_output=True, text=True, timeout=30)
print("COMMIT:", r2.returncode)
r3 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "push", "origin", "main"], capture_output=True, text=True, timeout=60)
print("PUSH:", r3.returncode)
print(r3.stderr[-200:] if r3.stderr else "")
