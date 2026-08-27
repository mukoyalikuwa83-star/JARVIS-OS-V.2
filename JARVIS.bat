@echo off
title JARVIS OS V.2 - Autonomous AI Assistant
cd /d "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"
call .venv\Scripts\activate.bat
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=utf-8

rem Clear any intentional-stop marker so a manual launch always starts
del /f /q ".jarvis\.stop" >nul 2>&1

:restart
rem Respect an intentional shutdown marker
if exist ".jarvis\.stop" (
    echo Intentional shutdown detected. Staying off.
    del /f /q ".jarvis\.stop" >nul 2>&1
    exit /b 0
)
echo ============================================
echo   JARVIS OS V.2 - Starting...
echo   %date% %time%
echo ============================================
python main.py
echo.
echo JARVIS exited with code %ERRORLEVEL%.
echo Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto restart
