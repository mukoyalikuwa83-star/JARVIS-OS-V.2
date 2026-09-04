@echo off
title JARVIS-OS V.2 - AI Assistant
cd /d "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"
set JARVIS_AUTO_START=1
echo [%date% %time%] JARVIS watchdog started >> .jarvis\watchdog.log
:restart
echo [%date% %time%] Starting JARVIS-OS V.2...
echo [%date% %time%] Starting >> .jarvis\watchdog.log
".venv\Scripts\python.exe" main.py >> .jarvis\watchdog.log 2>&1
echo [%date% %time%] JARVIS exited with code %ERRORLEVEL%
echo [%date% %time%] Exited code %ERRORLEVEL% >> .jarvis\watchdog.log
if exist .jarvis\.stop (
    echo Intentional shutdown detected.
    echo [%date% %time%] Intentional shutdown >> .jarvis\watchdog.log
    del /f /q .jarvis\.stop >nul 2>&1
    exit /b
)
echo Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto restart
