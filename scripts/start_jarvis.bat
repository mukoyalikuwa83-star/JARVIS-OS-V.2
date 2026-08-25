@echo off
REM Windows launcher for JARVIS.
REM Double-clickable from Explorer; from cmd.exe: scripts\start_jarvis.bat

setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0\.."
set JARVIS_CLI=1

set PYTHON_BIN=python
where %PYTHON_BIN% >nul 2>nul
if errorlevel 1 set PYTHON_BIN=py

if not exist ".venv\Scripts\python.exe" (
  echo [start_jarvis] Creating virtual environment in .venv ^(one-time^)...
  %PYTHON_BIN% -m venv .venv
)

call .venv\Scripts\activate.bat

if not exist ".env" (
  echo [start_jarvis] No .env found - copying .env.example to .env.
  copy /Y .env.example .env >nul
  echo [start_jarvis] Edit .env and set GEMINI_API_KEY, then run this script again.
  pause
  exit /b 1
)

find /i "YOUR_GEMINI_API_KEY" .env >nul
if not errorlevel 1 (
  echo [start_jarvis] GEMINI_API_KEY still has the placeholder value.
  echo [start_jarvis] Edit .env and replace YOUR_GEMINI_API_KEY with your real key.
  pause
  exit /b 1
)

echo [start_jarvis] Checking core dependencies...
python -c "import PyQt6, google.genai" >nul 2>nul
if not errorlevel 1 goto :launch

echo [start_jarvis] Core packages are missing ^(PyQt6 and/or google-genai^).
set /p DOINSTALL="[start_jarvis] Install dependencies now? (Y/N) "
if /i not "!DOINSTALL!"=="Y" goto :noinstall

echo [start_jarvis] Installing dependencies ^(needs internet^)...
python -m pip install --retries 1 --timeout 10 -r requirements.txt
python -c "import PyQt6, google.genai" >nul 2>nul
if not errorlevel 1 goto :launch

echo [start_jarvis] Install did not complete. When online, run:
echo   python -m pip install -r requirements.txt
pause
exit /b 1

:noinstall
echo [start_jarvis] Skipping install. When online, run:
echo   python -m pip install -r requirements.txt
pause
exit /b 1

:launch
echo [start_jarvis] Starting JARVIS...
python main.py
set "EXITCODE=%errorlevel%"
echo.
echo [start_jarvis] JARVIS closed (exit code %EXITCODE%).
if not "%EXITCODE%"=="0" (
  echo [start_jarvis] If this failed, run:  python -m pip install -r requirements.txt
  pause
)
endlocal
