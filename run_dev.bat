@echo off
REM Development startup script for PDF to Editable Web Layout System (Windows)
REM Starts both backend (Flask) and frontend (Vite) servers

echo 🚀 Starting PDF to Editable Web Layout System...

REM Create required directories
if not exist "uploads" mkdir uploads
if not exist "temp" mkdir temp
if not exist "logs" mkdir logs

REM Check if Python virtual environment exists
if not exist "venv" (
    echo 📦 Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install Python dependencies
echo 📦 Installing Python dependencies...
pip install -r backend\requirements.txt --quiet

REM Start backend server in background
echo 🔧 Starting backend server on port 5000...
start /B python start_backend.py

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Check if Node.js is available
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js is not installed. Please install Node.js to run the frontend.
    exit /b 1
)

REM Install frontend dependencies
echo 📦 Installing frontend dependencies...
cd frontend
call npm install --silent

REM Start frontend server
echo 🎨 Starting frontend server on port 3000...
start /B npm run dev
cd ..

echo.
echo ✅ System started successfully!
echo    Frontend: http://localhost:3000 or http://127.0.0.1:3000
echo    Backend:  http://localhost:5000 or http://127.0.0.1:5000
echo    API:      http://localhost:5000/api
echo.
echo Press Ctrl+C to stop all servers...
echo.

REM Keep window open
pause
