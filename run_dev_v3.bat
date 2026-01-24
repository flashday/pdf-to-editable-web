@echo off
REM Development startup script for PDF to Editable Web Layout System (Windows)
REM PaddleOCR 3.x Version - Uses venv_paddle3 virtual environment
REM Starts both backend (Flask) and frontend (Vite) servers

echo.
echo ========================================
echo   PDF to Editable Web Layout System
echo   [PaddleOCR 3.x Development Version]
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

REM Check for venv_paddle3 virtual environment (PaddleOCR 3.x)
set VENV_DIR=venv_paddle3
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] Virtual environment '%VENV_DIR%' not found!
    echo.
    echo         Please create it first:
    echo         python -m venv venv_paddle3
    echo         venv_paddle3\Scripts\activate
    echo         pip install paddlepaddle==3.3.0
    echo         pip install paddleocr==3.3.3
    echo         pip install -r backend\requirements.txt
    echo.
    echo         Or use run_dev.bat for PaddleOCR 2.x version.
    pause
    exit /b 1
)

echo [OK] Found virtual environment: %VENV_DIR% (PaddleOCR 3.x)

REM Activate virtual environment
echo [INFO] Activating virtual environment: %VENV_DIR%
call %VENV_DIR%\Scripts\activate.bat

REM Display PaddleOCR version
echo [INFO] Checking PaddleOCR version...
python -c "import paddleocr; print(f'[OK] PaddleOCR version: {paddleocr.__version__}')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] PaddleOCR not installed in %VENV_DIR%
    echo           Please install: pip install paddleocr==3.3.3
)

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
echo   Starting servers (PaddleOCR 3.x)...
echo ========================================
echo.

REM Start backend server in a new window
echo [INFO] Starting backend server on port 5000...
start "Backend Server (v3)" cmd /k "cd /d "%~dp0" && call %VENV_DIR%\Scripts\activate.bat && set PYTHONPATH=%CD% && python backend\app.py"

REM Wait for backend to start
echo [INFO] Waiting for backend to start...
timeout /t 3 /nobreak >nul

REM Start frontend server in a new window
echo [INFO] Starting frontend server on port 3000...
start "Frontend Server (v3)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================
echo   System started successfully!
echo   [PaddleOCR 3.x Development Version]
echo ========================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:5000
echo.
echo   Two new windows have been opened:
echo   - Backend Server (Python Flask + PaddleOCR 3.x)
echo   - Frontend Server (Vite)
echo.
echo   Close those windows to stop the servers.
echo.
echo   NOTE: This uses venv_paddle3 (PaddleOCR 3.x)
echo         For PaddleOCR 2.x, use run_dev.bat instead.
echo.
pause
