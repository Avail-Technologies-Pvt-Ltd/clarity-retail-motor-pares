@echo off
TITLE PostgreSQL Setup
echo ========================================
echo Setting up PostgreSQL Database
echo ========================================
echo.

cd /d "%~dp0"

if not exist ".env" (
    echo ERROR: .env file not found. Please run deploy.bat first.
    pause
    exit /b 1
)

REM Load environment variables
for /f "usebackq delims=" %%A in (.env) do (
    set %%A
)

echo Database: %DB_NAME%
echo User: %DB_USER%
echo.

REM Check PostgreSQL
where psql >nul 2>&1
if errorlevel 1 (
    echo PostgreSQL not found. Please install PostgreSQL.
    pause
    exit /b 1
)

REM Create database and user
echo Creating database and user...
echo This will prompt for PostgreSQL admin password.
echo.

psql -U postgres -c "CREATE USER %DB_USER% WITH PASSWORD '%DB_PASSWORD%';" 2>nul
psql -U postgres -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;" 2>nul
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %DB_USER%;" 2>nul
psql -U postgres -c "ALTER USER %DB_USER% CREATEDB;" 2>nul

echo.
echo ========================================
echo DATABASE SETUP COMPLETE!
echo ========================================
echo.
pause