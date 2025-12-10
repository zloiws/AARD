@echo off
REM Start AARD - Backend and Frontend servers
echo ========================================
echo Starting AARD Application
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment and start backend
echo [1/2] Starting Backend Server...
start "AARD Backend" cmd /k "cd /d %~dp0backend && call ..\venv\Scripts\activate.bat && python main.py"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
echo [2/2] Starting Frontend Server...
cd /d %~dp0ui
if exist "node_modules" (
    start "AARD Frontend" cmd /k "npm run dev"
) else (
    echo ERROR: node_modules not found!
    echo Please run: cd ui && npm install
    pause
    exit /b 1
)

echo.
echo ========================================
echo Both servers are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo ========================================
echo.
echo Press any key to close this window (servers will continue running)
pause >nul
