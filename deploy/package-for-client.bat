@echo off
TITLE Clarity POS - Prepare Client Deployment Package
setlocal EnableDelayedExpansion

echo ============================================================
echo      CLARITY POS - GENERATE CLIENT DEPLOYMENT PACKAGE
echo ============================================================
echo.

set "PROJECT_ROOT=%~dp0.."
set "OUTPUT_DIR=%~dp0client-package"
set "ZIP_FILE=%~dp0ClarityPOS_Client_Deployment.zip"

echo [1/4] Preparing output directory...
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%\certs"
mkdir "%OUTPUT_DIR%\logs"
mkdir "%OUTPUT_DIR%\media"
mkdir "%OUTPUT_DIR%\staticfiles"

echo [2/4] Copying deployment files...
copy /y "%PROJECT_ROOT%\docker-compose.prod.yml" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\update.bat" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\deploy\windows-update.ps1" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\.env.example" "%OUTPUT_DIR%\.env" >nul

echo [3/4] Creating client instructions and launch shortcuts...
(
echo ============================================================
echo   CLARITY POS - CLIENT MACHINE SETUP INSTRUCTIONS
echo ============================================================
echo.
echo PREREQUISITES ON THIS MACHINE:
echo 1. Install Docker Desktop for Windows:
echo    https://www.docker.com/products/docker-desktop/
echo 2. Start Docker Desktop and wait until it says "Engine running".
echo.
echo INSTALLATION STEPS:
echo 1. Copy this entire folder to: C:\pos-app
echo    ^(You can also run it directly from this folder^)
echo 2. Open the .env file in Notepad and configure:
echo    - SECRET_KEY ^(set a secure random string^)
echo    - DB_PASSWORD ^(set your database password^)
echo    - ZIMRA credentials ^(if using fiscalisation^)
echo 3. Double-click "update.bat"
echo    This will automatically download the Docker containers,
echo    set up PostgreSQL, run migrations, and launch Clarity POS!
echo.
echo ACCESSING THE APPLICATION:
echo Open your browser and go to:
echo   http://localhost:8085
echo.
echo FUTURE UPDATES:
echo Whenever a new update is released, simply double-click:
echo   update.bat
echo It will pull the latest version and update without losing data!
echo ============================================================
) > "%OUTPUT_DIR%\INSTRUCTIONS.txt"

REM Create Start POS Browser launcher
(
echo @echo off
echo echo Opening Clarity POS...
echo start http://localhost:8085
) > "%OUTPUT_DIR%\Open Clarity POS.bat"

echo [4/4] Creating zip archive...
if exist "%ZIP_FILE%" del /f /q "%ZIP_FILE%"
powershell -NoProfile -Command "Compress-Archive -Path '%OUTPUT_DIR%\*' -DestinationPath '%ZIP_FILE%' -Force"

echo.
echo ============================================================
echo               PACKAGE CREATED SUCCESSFULLY!
echo ============================================================
echo.
echo Client Folder: %OUTPUT_DIR%
echo Zip Archive:   %ZIP_FILE%
echo.
echo What to do next:
echo 1. Copy "%ZIP_FILE%" to the other machine ^(via USB, network, etc.^).
echo 2. Extract to "C:\pos-app" on the other machine.
echo 3. Configure .env and double-click "update.bat".
echo ============================================================
echo.
pause
