@echo off
echo ========================================
echo POS System Update
echo ========================================
cd /d C:\pos-app
PowerShell -ExecutionPolicy Bypass -File "%~dp0windows-update.ps1"
pause