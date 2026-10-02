@echo off
setlocal
title JARVIS OS V.2 - Current Local Build
pushd "%~dp0"
if errorlevel 1 (
    echo Could not open the JARVIS project folder:
    echo %~dp0
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    echo JARVIS Python environment is missing at:
    echo %CD%\.venv\Scripts\python.exe
    echo Restore the project's .venv and try again.
    pause
    popd
    exit /b 1
)
if not exist ".jarvis" mkdir ".jarvis"
set JARVIS_AUTO_START=1
set PYTHONUNBUFFERED=1
echo [%date% %time%] JARVIS watchdog started >> .jarvis\watchdog.log
:restart
echo [%date% %time%] Starting JARVIS-OS V.2...
echo [%date% %time%] Starting >> .jarvis\watchdog.log
".venv\Scripts\python.exe" -u main.py >> .jarvis\watchdog.log 2>&1
set "JARVIS_EXIT_CODE=%ERRORLEVEL%"
echo [%date% %time%] JARVIS exited with code %JARVIS_EXIT_CODE%
echo [%date% %time%] Exited code %JARVIS_EXIT_CODE% >> .jarvis\watchdog.log
if exist .jarvis\.stop (
    echo Intentional shutdown detected.
    echo [%date% %time%] Intentional shutdown >> .jarvis\watchdog.log
    del /f /q .jarvis\.stop >nul 2>&1
    popd
    exit /b
)
echo Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto restart
