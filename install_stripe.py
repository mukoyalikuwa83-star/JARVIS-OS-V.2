import subprocess, sys
py = sys.executable
pip = py.replace("python.exe", "pip.exe")
result = subprocess.run([pip, "install", "--quiet", "stripe"], capture_output=True, text=True, timeout=180)
print("RC:", result.returncode)
print(result.stdout[-300:] if result.stdout else "")
print(result.stderr[-300:] if result.stderr else "")
