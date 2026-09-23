@echo off
TITLE Clarity POS - Docker Update and Deployment
setlocal EnableDelayedExpansion

echo ============================================================
echo           CLARITY POS - DOCKER UPDATE AND DEPLOYMENT
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT="

if exist "%~dp0windows-update.ps1" set "PS_SCRIPT=%~dp0windows-update.ps1"
if not defined PS_SCRIPT if exist "%~dp0deploy\windows-update.ps1" set "PS_SCRIPT=%~dp0deploy\windows-update.ps1"

if not defined PS_SCRIPT (
    echo [ERROR] windows-update.ps1 script could not be located.
    pause
    exit /b 1
)

PowerShell -ExecutionPolicy Bypass -NoProfile -File "%PS_SCRIPT%" -AppPath "%~dp0.."
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Deployment failed with exit code %ERRORLEVEL%.
)
echo.
pause