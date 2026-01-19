@echo off
REM Development startup script for PDF to Editable Web Layout System (Windows)
REM Starts both backend (Flask) and frontend (Vite) servers

echo.
echo ========================================
echo   PDF to Editable Web Layout System
echo ========================================
echo.

REM Change to the directory where this script is located
cd /d "%~dp0"
echo [INFO] Working directory: %CD%

REM Verify we're in the right directory
if not exist "backend\app.py" (
    echo [ERROR] Cannot find backend\app.py
    echo         Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Create required directories
if not exist "uploads" mkdir uploads
if not exist "temp" mkdir temp
if not exist "logs" mkdir logs
if not exist "backend\uploads" mkdir backend\uploads
if not exist "backend\temp" mkdir backend\temp
if not exist "backend\logs" mkdir backend\logs

REM Check for existing virtual environment (venv310 or venv)
set VENV_DIR=
if exist "venv310\Scripts\activate.bat" (
    set VENV_DIR=venv310
    echo [OK] Found virtual environment: venv310
) else if exist "venv\Scripts\activate.bat" (
    set VENV_DIR=venv
    echo [OK] Found virtual environment: venv
) else (
    echo [ERROR] No virtual environment found!
    echo         Please create one first:
    echo         python -m venv venv310
    echo         venv310\Scripts\activate
    echo         pip install -r backend\requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment: %VENV_DIR%
call %VENV_DIR%\Scripts\activate.bat

REM Set PYTHONPATH
set PYTHONPATH=%CD%

REM Check if Node.js is available
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js to run the frontend.
    echo         Download from: https://nodejs.org/
    pause
    exit /b 1
)

REM Check frontend dependencies
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd /d "%~dp0frontend"
    call npm install
    cd /d "%~dp0"
) else (
    echo [OK] Frontend dependencies already installed
)

echo.
echo ========================================
echo   Starting servers...
echo ========================================
echo.

REM Start backend server in a new window
echo [INFO] Starting backend server on port 5000...
start "Backend Server" cmd /k "cd /d "%~dp0" && call %VENV_DIR%\Scripts\activate.bat && set PYTHONPATH=%CD% && python backend\app.py"

REM Wait for backend to start
echo [INFO] Waiting for backend to start...
timeout /t 3 /nobreak >nul

REM Start frontend server in a new window
echo [INFO] Starting frontend server on port 3000...
start "Frontend Server" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================
echo   System started successfully!
echo ========================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:5000
echo.
echo   Two new windows have been opened:
echo   - Backend Server (Python Flask)
echo   - Frontend Server (Vite)
echo.
echo   Close those windows to stop the servers.
echo.
pause
