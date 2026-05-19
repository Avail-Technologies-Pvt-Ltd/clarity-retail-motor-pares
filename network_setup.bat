@echo off
TITLE Network Setup for POS System
echo ========================================
echo Configuring Windows Firewall
echo ========================================

cd /d "%~dp0"

REM Allow inbound connections on port 8081
netsh advfirewall firewall add rule name="POS System" dir=in action=allow protocol=TCP localport=8081

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :done
)
:done
set IP=%IP: =%

echo.
echo ========================================
echo NETWORK CONFIGURATION
echo ========================================
echo.
echo POS System is now accessible at:
echo.
echo Local access: http://localhost:8081
echo Network access: http://%IP%:8081
echo Admin: http://%IP%:8081/admin
echo.
pause