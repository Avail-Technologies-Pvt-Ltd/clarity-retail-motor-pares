@echo off
TITLE POS System - Database Backup
echo ========================================
echo Backing up database
echo ========================================

cd /d "%~dp0"

REM Load environment variables
for /f "usebackq delims=" %%A in (.env) do (
    set %%A
)

REM Create backup directory
set BACKUP_DIR=C:\POS_Backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Generate timestamp
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM Backup database
set PGPASSWORD=%DB_PASSWORD%
pg_dump -h %DB_HOST% -U %DB_USER% -d %DB_NAME% > "%BACKUP_DIR%\pos_backup_%TIMESTAMP%.sql"

if errorlevel 1 (
    echo ERROR: Backup failed
    pause
    exit /b 1
)

set PGPASSWORD=
echo Backup saved to: %BACKUP_DIR%\pos_backup_%TIMESTAMP%.sql

REM Keep only last 30 backups
forfiles /p "%BACKUP_DIR%" /m "*.sql" /d -30 /c "cmd /c del @file" 2>nul

echo.
echo Backup complete!
pause