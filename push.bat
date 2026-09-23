@echo off
TITLE Clarity POS - One-Step GitHub Push
setlocal enabledelayedexpansion

echo ============================================================
echo           CLARITY POS - ONE-STEP GITHUB PUSH
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Check if git is installed
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git is not installed or not in system PATH.
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

REM 2. Check if this is a git repository
if not exist ".git" (
    echo [ERROR] Current directory is not a Git repository.
    pause
    exit /b 1
)

REM 3. Get current branch name
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
if "%CURRENT_BRANCH%"=="" set CURRENT_BRANCH=master

echo [INFO] Active branch: %CURRENT_BRANCH%
echo.

REM 4. Check for changes
git status --porcelain > "%TEMP%\git_status_check.txt"
set HAS_CHANGES=0
for %%A in ("%TEMP%\git_status_check.txt") do if %%~zA gtr 0 set HAS_CHANGES=1
del "%TEMP%\git_status_check.txt" 2>nul

REM Check for unpushed commits
for /f "tokens=*" %%C in ('git log origin/%CURRENT_BRANCH%..%CURRENT_BRANCH% --oneline 2^>nul') do (
    set HAS_UNPUSHED=1
)

if %HAS_CHANGES% equ 0 if not defined HAS_UNPUSHED (
    echo [INFO] Working tree is clean and up to date with origin/%CURRENT_BRANCH%.
    echo No changes to commit or push.
    echo.
    pause
    exit /b 0
)

REM 5. Determine commit message
set "COMMIT_MSG=%*"

if not defined COMMIT_MSG (
    set /p "INPUT_MSG=Enter commit message (or press ENTER for auto-timestamp): "
    if not defined INPUT_MSG (
        for /f "tokens=*" %%T in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set "COMMIT_MSG=Update: %%T"
    ) else (
        set "COMMIT_MSG=!INPUT_MSG!"
    )
)

echo.
echo [1/3] Staging changes...
git add -A

if %HAS_CHANGES% equ 1 (
    echo [2/3] Committing changes: "%COMMIT_MSG%"...
    git commit -m "%COMMIT_MSG%"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Git commit failed.
        pause
        exit /b 1
    )
) else (
    echo [2/3] No new file changes to commit; pushing existing commits...
)

echo [3/3] Pushing to origin %CURRENT_BRANCH%...
git push origin %CURRENT_BRANCH%

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Git push failed! Please check your network connection and GitHub permissions.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo                   PUSH SUCCESSFUL!
echo ============================================================
echo.
echo GitHub Actions has been automatically triggered to build and
echo push the updated Docker image to Docker Hub.
echo.
echo Track build progress live here:
echo   https://github.com/Recusants/CLARITY-POS/actions
echo.
echo Once the build is green, deploy with 1-click using:
echo   update.bat
echo ============================================================
echo.
pause
