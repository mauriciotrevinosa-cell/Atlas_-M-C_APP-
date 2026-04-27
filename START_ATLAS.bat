@echo off
title ATLAS SYSTEM
color 0f
cls
echo ==================================================
echo      ATLAS SYSTEM - BROWSER EDITION
echo ==================================================
echo Made by: M&C Inc.
echo.
echo  [1] Start normally (single run, opens browser)
echo  [2] Start with DAEMON (auto-restart on crash, 24/7)
echo  [3] Install auto-start on boot  (run once on Samsung 360)
echo  [4] Upgrade code (git pull + restart)
echo.
set /p CHOICE="Select [1-4] or press Enter for normal start: "

if "%CHOICE%"=="2" goto DAEMON
if "%CHOICE%"=="3" goto INSTALL
if "%CHOICE%"=="4" goto UPGRADE

:NORMAL
echo.
echo Starting Atlas (single run)...
python run_atlas.py
pause
goto END

:DAEMON
echo.
echo Starting Atlas in 24/7 daemon mode...
echo Press Ctrl+C to stop. Logs: logs\daemon.log
echo.
python run_daemon.py
pause
goto END

:INSTALL
echo.
call scripts\install_service.bat
goto END

:UPGRADE
echo.
call scripts\upgrade.bat
goto END

:END
