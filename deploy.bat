@echo off
TITLE POS System - Initial Deployment
echo ========================================
echo Deploying Point of Sale System
echo ========================================
echo.

REM Go to the script's location (C:\CLARITY-POS)
cd /d "%~dp0"

REM ============================================================
REM 1. Check Python
REM ============================================================
echo [1/8] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)
echo OK
echo.

REM ============================================================
REM 2. Check Git
REM ============================================================
echo [2/8] Checking Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git not found
    pause
    exit /b 1
)
echo OK
echo.

REM ============================================================
REM 3. Clone or update repository
REM ============================================================
echo [3/8] Getting code from GitHub...
if exist ".git" (
    git pull origin Motor-Spares
) else (
    git clone -b Motor-Spares https://github.com/Recusants/CLARITY-POS.git .
)
if errorlevel 1 (
    echo ERROR: Failed to get code from GitHub
    pause
    exit /b 1
)
echo OK
echo.

REM ============================================================
REM 4. Create virtual environment
REM ============================================================
echo [4/8] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)
echo OK
echo.

REM ============================================================
REM 5. Install Python packages
REM ============================================================
echo [5/8] Installing Python packages...
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

python -m pip install --upgrade pip
pip install django==5.0.3
pip install -r requirements.txt
pip install waitress psycopg2-binary whitenoise
echo OK
echo.

REM ============================================================
REM 6. Check NSSM
REM ============================================================
echo [6/8] Checking NSSM...
if not exist "nssm.exe" (
    echo ERROR: nssm.exe not found!
    echo Please download nssm.exe from https://nssm.cc/download
    echo and place it in: %cd%
    pause
    exit /b 1
)
echo OK: NSSM found
echo.

REM ============================================================
REM 7. Create .env file
REM ============================================================
echo [7/8] Configuring .env file...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
    ) else (
        echo SECRET_KEY=change-this > .env
        echo DEBUG=False >> .env
        echo ALLOWED_HOSTS=* >> .env
        echo DB_NAME=point_of_sale >> .env
        echo DB_USER=pos_user >> .env
        echo DB_PASSWORD=change-this >> .env
        echo DB_HOST=localhost >> .env
        echo DB_PORT=5432 >> .env
    )
    echo.
    echo ========================================
    echo EDIT THE .env FILE NOW!
    echo ========================================
    echo.
    notepad .env
    echo Press any key after saving...
    pause >nul
)
echo OK
echo.

REM ============================================================
REM 8. Load .env and set production mode
REM ============================================================
echo Loading configuration...
for /f "usebackq delims=" %%A in (.env) do (
    set %%A
)
set DJANGO_SETTINGS_MODULE=point_of_sale.settings_prod
echo OK
echo.

REM ============================================================
REM 9. Run database setup (PostgreSQL)
REM ============================================================
echo [8/8] Setting up database...
if exist "setup_postgres.bat" (
    call setup_postgres.bat
) else (
    echo ERROR: setup_postgres.bat not found
    pause
    exit /b 1
)

echo Running migrations...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Migration failed
    pause
    exit /b 1
)

python manage.py collectstatic --noinput
echo OK
echo.

REM ============================================================
REM 10. Install Windows Service
REM ============================================================
echo Installing Windows service...
.\nssm.exe install POSSystem "%cd%\venv\Scripts\python.exe" "%cd%\run.py"
.\nssm.exe set POSSystem DisplayName "POS System"
.\nssm.exe set POSSystem Start SERVICE_AUTO_START
.\nssm.exe set POSSystem Environment DJANGO_SETTINGS_MODULE=point_of_sale.settings_prod
.\nssm.exe set POSSystem AppStdout "%cd%\logs\stdout.log"
.\nssm.exe set POSSystem AppStderr "%cd%\logs\stderr.log"

mkdir logs 2>nul

.\nssm.exe start POSSystem

echo.
echo ========================================
echo DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo Access at: http://localhost:8081
echo.
pause