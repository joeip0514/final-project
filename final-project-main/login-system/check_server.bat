@echo off
echo ========================================
echo Server Connection Diagnostic Tool
echo ========================================
echo.

echo [1] Checking if Python is installed...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo OK: Python is installed
echo.

echo [2] Checking if required packages are installed...
python -c "import fastapi, uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Required packages may not be installed
    echo Run: pip install -r requirements.txt
) else (
    echo OK: Required packages are installed
)
echo.

echo [3] Checking if port 5000 is available...
netstat -ano | findstr :5000 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo WARNING: Port 5000 is already in use
    echo Run: kill_port.bat to free the port
) else (
    echo OK: Port 5000 is available
)
echo.

echo [4] Checking if port 8000 is available...
netstat -ano | findstr :8000 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo WARNING: Port 8000 is already in use
) else (
    echo OK: Port 8000 is available
)
echo.

echo [5] Testing if app.py can be imported...
python -c "import sys; sys.path.insert(0, '.'); import app; print('OK: app.py can be imported')" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Cannot import app.py
    echo Check if app.py exists in the current directory
) else (
    echo OK: app.py can be imported
)
echo.

echo ========================================
echo Diagnostic complete!
echo ========================================
echo.
echo To start the server, run:
echo   python app.py
echo   or
echo   run.bat
echo.
pause

