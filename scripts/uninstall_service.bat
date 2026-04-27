@echo off
title ATLAS SERVICE UNINSTALLER
color 0c

echo Removing Atlas auto-start task...
schtasks /delete /tn "AtlasDaemon" /f

if %errorlevel% equ 0 (
    echo Done. Atlas will no longer start on boot.
) else (
    echo Task not found or already removed.
)
pause
