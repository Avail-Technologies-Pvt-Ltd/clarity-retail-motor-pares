@echo off
REM windows-update.bat - Batch wrapper for PowerShell script
REM Usage: windows-update.bat [CompanyName] [Tag]

echo ========================================
echo POS System Update Check
echo ========================================

set COMPANY=%1
if "%COMPANY%"=="" set COMPANY=CompanyA

set TAG=%2
if "%TAG%"=="" set TAG=latest

set APP_PATH=%3
if "%APP_PATH%"=="" set APP_PATH=C:\pos-app

echo Company: %COMPANY%
echo Tag: %TAG%
echo Path: %APP_PATH%

PowerShell -ExecutionPolicy Bypass -File "%~dp0windows-update.ps1" -CompanyName "%COMPANY%" -Tag "%TAG%" -AppPath "%APP_PATH%"

pause