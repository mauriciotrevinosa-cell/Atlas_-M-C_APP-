@echo off
:: Atlas Hot-Upgrade Script
:: Pulls latest code and signals the daemon to restart Atlas gracefully.
:: Run this from the Atlas root directory (or double-click).

title ATLAS UPGRADE
color 0e
cls

echo ==================================================
echo  ATLAS HOT-UPGRADE
echo ==================================================
echo.

cd /d "%~dp0\.."

:: Step 1 — Pull latest code
echo [1/3] Pulling latest code...
git pull --ff-only
if %errorlevel% neq 0 (
    echo.
    echo ERROR: git pull failed. Check for merge conflicts or network issues.
    pause
    exit /b 1
)
echo OK.

:: Step 2 — Install/update Python dependencies (only if requirements changed)
echo.
echo [2/3] Updating dependencies...
pip install -q -r requirements.txt --upgrade
if %errorlevel% neq 0 (
    echo WARNING: pip install reported errors. Check manually if needed.
)
echo OK.

:: Step 3 — Restart the daemon (if it's running via run_daemon.py)
echo.
echo [3/3] Restarting Atlas daemon...

if exist atlas_daemon.pid (
    set /p DAEMON_PID=<atlas_daemon.pid
    echo Found daemon PID: %DAEMON_PID%
    :: Send SIGTERM equivalent on Windows via taskkill
    taskkill /PID %DAEMON_PID% /F >nul 2>&1
    echo Daemon stopped. Starting new daemon...
    timeout /t 2 /nobreak >nul
    start "ATLAS DAEMON" python run_daemon.py
    echo Done! Atlas is restarting in background.
) else (
    echo No daemon PID file found.
    echo If Atlas is running via START_ATLAS.bat, close it and relaunch manually.
    echo If you want auto-restart, use: python run_daemon.py
)

echo.
echo ==================================================
echo  Upgrade complete! Check logs\daemon.log for status.
echo ==================================================
timeout /t 5
