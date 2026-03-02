"""
ARIA Windows Service

Corre ARIA como servicio de Windows (24/7 en background)

Features:
- Auto-start on boot
- Runs in background
- System tray icon
- Logs
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os


class ARIAService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ARIAService"
    _svc_display_name_ = "ARIA Assistant Service"
    _svc_description_ = "ARIA AI Assistant running 24/7"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = True
    
    def SvcStop(self):
        """Stop service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.is_running = False
    
    def SvcDoRun(self):
        """Run service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
    
    def main(self):
        """Main service loop"""
        # Import ARIA
        sys.path.append(os.path.dirname(__file__))
        
        try:
            from atlas.assistants.aria import ARIA
            from aria.server import run_server
            
            # Initialize ARIA
            aria = ARIA()
            
            # Run server
            run_server(aria, host="0.0.0.0", port=8000)
        
        except Exception as e:
            servicemanager.LogErrorMsg(f"ARIA Service error: {e}")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ARIAService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ARIAService)


# ==================== INSTALLATION SCRIPTS ====================

# install_service.bat
INSTALL_BAT = """@echo off
echo Installing ARIA Service...
python windows_service.py install
echo.
echo Starting ARIA Service...
python windows_service.py start
echo.
echo ARIA Service installed and started!
pause
"""

# uninstall_service.bat
UNINSTALL_BAT = """@echo off
echo Stopping ARIA Service...
python windows_service.py stop
echo.
echo Uninstalling ARIA Service...
python windows_service.py remove
echo.
echo ARIA Service uninstalled!
pause
"""

# Save scripts
with open("install_service.bat", "w") as f:
    f.write(INSTALL_BAT)

with open("uninstall_service.bat", "w") as f:
    f.write(UNINSTALL_BAT)

print("""
✅ Windows Service files created:
- windows_service.py
- install_service.bat
- uninstall_service.bat

Installation:
1. Run as Administrator: install_service.bat
2. ARIA will start automatically on boot

Uninstall:
1. Run as Administrator: uninstall_service.bat

Requirements:
pip install pywin32
""")
