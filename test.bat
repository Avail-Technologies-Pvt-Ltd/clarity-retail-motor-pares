@echo off
TITLE Clarity POS - Automated Test Runner
setlocal EnableDelayedExpansion

echo ============================================================
echo           CLARITY POS - AUTOMATED TEST SUITE
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Check Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    pause
    exit /b 1
)

REM 2. Determine Test Target
set "TARGET=%*"
if "%TARGET%"=="" (
    set "TARGET=tests"
    set "LABEL=All Application Tests (tests/)"
) else (
    set "LABEL=%TARGET%"
)

echo [INFO] Running test target: %LABEL%
echo [INFO] Settings module: point_of_sale.settings_dev
echo [INFO] Saving detailed log to: test_results.log
echo.
echo ============================================================
echo                    RUNNING TESTS...
echo ============================================================
echo.

python manage.py test %TARGET% --settings=point_of_sale.settings_dev > "%~dp0test_results.log" 2>&1
set "TEST_EXIT_CODE=%ERRORLEVEL%"

REM Display full test output from log
type "%~dp0test_results.log"

echo.
echo ============================================================
if "%TEST_EXIT_CODE%"=="0" (
    echo                TEST SUITE PASSED - ALL GREEN
) else (
    echo             TEST SUITE FINISHED WITH ISSUES OR ERRORS
)
echo ============================================================
echo.
echo Detailed test log saved to:
echo   %~dp0test_results.log
echo.
pause
