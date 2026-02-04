@echo off
set "PROJECT_ROOT=%~dp0"
set "PYTHONPATH=%PROJECT_ROOT%python\src"

echo ===================================================
echo   Starting ARIA (Atlas Reasoning & Intelligence)
echo   Local Mode | Powered by Ollama
echo ===================================================

python "%PROJECT_ROOT%apps\cli\terminal.py"

pause
