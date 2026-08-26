@echo off
title JARVIS Watchdog - 24/7
setlocal enabledelayedexpansion

set "JARVIS_DIR=C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"
set "PYTHON=%JARVIS_DIR%\.venv\Scripts\python.exe"
set "LOG=%JARVIS_DIR%\jarvis.log"
set "MAX_RESTARTS=999999"
set "RESTARTS=0"

echo [%date% %time%] JARVIS Watchdog started >> "%LOG%"
echo [%date% %time%] Will auto-restart on crash >> "%LOG%"

:restart
set /a RESTARTS+=1
echo [%date% %time%] Starting JARVIS (restart #%RESTARTS%) >> "%LOG%"
echo [%date% %time%] Starting JARVIS (restart #%RESTARTS%)...

cd /d "%JARVIS_DIR%"
set "PYTHONIOENCODING=utf-8"
set "JARVIS_AUTO_START=1"

"%PYTHON%" main.py 2>> "%LOG%"
set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] JARVIS exited with code %EXIT_CODE% >> "%LOG%"
echo [%date% %time%] JARVIS exited with code %EXIT_CODE%

if %RESTARTS% GEQ %MAX_RESTARTS% (
    echo [%date% %time%] Max restarts reached. Stopping. >> "%LOG%"
    goto :end
)

echo Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto :restart

:end
echo [%date% %time%] Watchdog shutting down >> "%LOG%"
