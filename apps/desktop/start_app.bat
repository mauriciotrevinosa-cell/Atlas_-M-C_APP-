@echo off
cd /d "%~dp0"
echo Starting ARIA Terminal...
"node_modules\.bin\electron.cmd" .
pause
