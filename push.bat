@echo off
TITLE Clarity POS - 1-Click GitHub Push ^& Docker Hub Build
setlocal enabledelayedexpansion

echo ============================================================
echo   CLARITY POS - ONE-CLICK GITHUB PUSH ^& DOCKER HUB BUILD
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

REM 4. Check for uncommitted changes
git status --porcelain > "%TEMP%\git_status_check.txt"
set HAS_CHANGES=0
for %%A in ("%TEMP%\git_status_check.txt") do if %%~zA gtr 0 set HAS_CHANGES=1
del "%TEMP%\git_status_check.txt" 2>nul

REM Check for unpushed commits
set HAS_UNPUSHED=0
for /f "tokens=*" %%C in ('git log origin/%CURRENT_BRANCH%..%CURRENT_BRANCH% --oneline 2^>nul') do (
    set HAS_UNPUSHED=1
)

REM Handle completely clean state
if %HAS_CHANGES% equ 0 if %HAS_UNPUSHED% equ 0 (
    echo [INFO] Working tree is clean and up to date with origin/%CURRENT_BRANCH%.
    echo.
    choice /C YN /T 5 /D N /M "Do you want to force-trigger a fresh Docker Hub build anyway"
    if !ERRORLEVEL! equ 1 (
        for /f "tokens=*" %%T in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set "FORCE_TIME=%%T"
        echo [INFO] Creating trigger commit...
        git commit --allow-empty -m "Manual trigger: Docker Hub build (!FORCE_TIME!)"
        set HAS_UNPUSHED=1
    ) else (
        echo.
        echo No changes to push. Exiting.
        pause
        exit /b 0
    )
)

REM 5. Determine commit message
set "COMMIT_MSG=%*"

if not defined COMMIT_MSG (
    if %HAS_CHANGES% equ 1 (
        echo [INFO] Changes detected in working directory.
        choice /C YM /T 3 /D Y /M "Auto-pushing in 3 seconds [Y: Proceed now, M: Custom message]"
        if !ERRORLEVEL! equ 2 (
            set /p "INPUT_MSG=Enter commit message: "
            if defined INPUT_MSG set "COMMIT_MSG=!INPUT_MSG!"
        )
        if not defined COMMIT_MSG (
            for /f "tokens=*" %%T in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set "COMMIT_MSG=Update: %%T"
        )
    )
)

echo.
echo [1/3] Staging changes...
git add -A

if %HAS_CHANGES% equ 1 (
    echo [2/3] Committing changes: "!COMMIT_MSG!"...
    git commit -m "!COMMIT_MSG!"
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
    echo ============================================================
    echo [ERROR] Git push failed!
    echo Check your internet connection and GitHub repository permissions.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo                   PUSH SUCCESSFUL!
echo ============================================================
echo.
echo GitHub has received your code and automatically triggered
echo the "Build and Push Docker Image" workflow to Docker Hub!
echo.

set "REPO_URL="
for /f "tokens=*" %%u in ('git remote get-url origin 2^>nul') do set "REPO_URL=%%u"
if defined REPO_URL (
    set "REPO_URL=!REPO_URL:.git=!"
    set "ACTIONS_URL=!REPO_URL!/actions"
) else (
    set "ACTIONS_URL=https://github.com/Avail-Technologies-Pvt-Ltd/clarity-retail-motor-pares/actions"
)

echo View the live build and push progress here:
echo   !ACTIONS_URL!
echo.
echo Once the build is green, update any client installation via:
echo   update.bat
echo ============================================================
echo.

choice /C YN /T 5 /D N /M "Open GitHub Actions page in browser"
if !ERRORLEVEL! equ 1 (
    start "" "!ACTIONS_URL!"
)

echo.
pause
