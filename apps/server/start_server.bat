@echo off
title ARIA SERVER
cd /d "%~dp0..\.."
echo Starting ARIA Backend Legacy...
python run_server.py
pause
