@echo off
TITLE POS System - Update
echo ========================================
echo Updating Point of Sale System
echo ========================================
echo.

REM Go to the script's location (C:\CLARITY-POS)
cd /d "%~dp0"

REM ============================================================
REM 1. Activate virtual environment
REM ============================================================
echo [1/6] Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo OK
echo.

REM ============================================================
REM 2. Pull latest code from GitHub
REM ============================================================
echo [2/6] Pulling latest code from GitHub...
git pull origin master
if errorlevel 1 (
    echo ERROR: Failed to pull updates
    pause
    exit /b 1
)
echo OK
echo.

REM ============================================================
REM 3. Update Python packages
REM ============================================================
echo [3/6] Updating Python packages...
pip install --upgrade pip
pip install --upgrade -r requirements.txt
pip install --upgrade waitress psycopg2-binary whitenoise
echo OK
echo.

REM ============================================================
REM 4. Load environment variables
REM ============================================================
echo [4/6] Loading configuration...
if not exist ".env" (
    echo ERROR: .env file not found
    pause
    exit /b 1
)

for /f "usebackq delims=" %%A in (.env) do (
    set %%A
)
set DJANGO_SETTINGS_MODULE=point_of_sale.settings_prod
echo OK
echo.

REM ============================================================
REM 5. Run database migrations
REM ============================================================
echo [5/6] Running database migrations...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Migration failed
    pause
    exit /b 1
)
echo OK
echo.

REM ============================================================
REM 6. Collect static files
REM ============================================================
echo [6/6] Collecting static files...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo WARNING: Static files collection had issues
) else (
    echo OK: Static files updated
)
echo.

REM ============================================================
REM 7. Restart the service
REM ============================================================
echo Restarting service...
if exist ".\nssm.exe" (
    .\nssm.exe stop POSSystem
    timeout /t 3 /nobreak >nul
    .\nssm.exe start POSSystem
) else (
    nssm stop POSSystem
    timeout /t 3 /nobreak >nul
    nssm start POSSystem
)

echo.
echo ========================================
echo UPDATE COMPLETE!
echo ========================================
echo.
echo Your POS system has been updated.
echo.
pause