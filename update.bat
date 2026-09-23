@echo off
TITLE Clarity POS - One-Click Docker Update and Deploy
setlocal EnableDelayedExpansion

echo ============================================================
echo         CLARITY POS - ONE-CLICK DOCKER UPDATE
echo ============================================================
echo.

set "APP_DIR=%~dp0"
set "PS_SCRIPT="

if exist "%~dp0deploy\windows-update.ps1" set "PS_SCRIPT=%~dp0deploy\windows-update.ps1"
if not defined PS_SCRIPT if exist "%~dp0windows-update.ps1" set "PS_SCRIPT=%~dp0windows-update.ps1"

if not defined PS_SCRIPT (
    echo [ERROR] Deployment script windows-update.ps1 not found.
    pause
    exit /b 1
)

PowerShell -ExecutionPolicy Bypass -NoProfile -File "%PS_SCRIPT%" -AppPath "%APP_DIR:~0,-1%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Update process encountered an error.
)
echo.
pause
