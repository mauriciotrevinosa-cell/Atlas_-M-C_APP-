@echo off
:: Atlas Windows Auto-Start Installer
:: Registers Atlas daemon to start automatically when Windows boots.
:: Uses Windows Task Scheduler (no admin required for current user scope).
::
:: Run this ONCE on the Samsung 360 dedicated machine.
:: To uninstall: scripts\uninstall_service.bat

title ATLAS SERVICE INSTALLER
color 0a
cls

echo ==================================================
echo  ATLAS AUTO-START INSTALLER
echo  (Windows Task Scheduler — Current User)
echo ==================================================
echo.

cd /d "%~dp0\.."
set ATLAS_ROOT=%CD%
set TASK_NAME=AtlasDaemon
set PYTHON=%ATLAS_ROOT%\venv\Scripts\python.exe

:: Check if venv python exists, fallback to system python
if not exist "%PYTHON%" (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python not found. Install Python or activate your venv.
        pause
        exit /b 1
    )
    set PYTHON=python
)

echo Atlas Root:  %ATLAS_ROOT%
echo Python:      %PYTHON%
echo Task Name:   %TASK_NAME%
echo.

:: Remove old task if it exists
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %errorlevel% equ 0 (
    echo Removing existing task...
    schtasks /delete /tn "%TASK_NAME%" /f
)

:: Create the scheduled task
:: Trigger: on user logon  |  Action: run daemon  |  Start in: Atlas root
echo Registering scheduled task...

schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON%\" \"%ATLAS_ROOT%\run_daemon.py\" --no-browser" ^
  /sc ONLOGON ^
  /delay 0000:30 ^
  /sd 01/01/2026 ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to register scheduled task.
    echo Try running this script as Administrator.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo  SUCCESS!
echo  Atlas will auto-start 30 seconds after login.
echo.
echo  To start now:
echo    python run_daemon.py
echo.
echo  To check task:
echo    schtasks /query /tn AtlasDaemon
echo.
echo  To remove auto-start:
echo    scripts\uninstall_service.bat
echo ==================================================
pause
