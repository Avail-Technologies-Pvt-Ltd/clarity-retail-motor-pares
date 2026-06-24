@echo off
REM update.bat - One-click update for Windows
echo ========================================
echo POS System Update
echo ========================================
echo.

cd /d C:\pos-app
powershell.exe -ExecutionPolicy Bypass -File deploy\windows-update.ps1

echo.
echo Press any key to exit...
pause > nul