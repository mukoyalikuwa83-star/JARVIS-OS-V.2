@echo off
title JARVIS-OS V.2 - AI Assistant Setup
cd /d "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"

:: Step 1: Ensure pydantic 1.x is installed (compatible with Windows)
echo Checking pydantic version...
python -c "import pydantic" 2>nul
if %errorlevel% neq 0 (
    echo Installing pydantic 1.x...
    pip install pydantic==1.10.5 --quiet --index-url https://mirrors.aliyun.com/pypi/simple/ >nul 2>&1
)

:: Step 2: Try to import and start JARVIS
echo Starting JARVIS-OS V.2...
echo.

:: Try to import and start main
python -c "
import sys
sys.path.insert(0, r'.')
try:
    from actions.autonomous_worker import AutonomousWorker
    from actions.main import JarvisLive
    print('SUCCESS: All imports working')
except ImportError as e:
    print(f'Import error: {e}')
    print('Attempting fallback startup...')
"

:: Start JARVIS main process
echo.
echo Starting JARVIS main process...
'.venv\Scripts\python.exe' main.py

echo.
echo JARVIS process ended.
echo.
pause