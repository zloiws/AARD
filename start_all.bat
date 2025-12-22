@echo off
REM Start AARD - All services (Backend + Frontend)
REM This script starts both servers in separate windows

echo ========================================
echo Starting AARD - All Services
echo ========================================
echo.

REM Check virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please create it first: python -m venv venv
    pause
    exit /b 1
)

REM Check node_modules
if not exist "ui\node_modules" (
    echo [ERROR] Frontend dependencies not installed!
    echo Please install them: cd ui ^&^& npm install
    pause
    exit /b 1
)

REM Start Backend Server
echo [1/2] Starting Backend Server on http://localhost:8000
start "AARD Backend Server" cmd /k "cd /d %~dp0backend && call ..\venv\Scripts\activate.bat && echo Backend starting... && python main.py"

REM Wait for backend to initialize
echo Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

REM Start Frontend Server
echo [2/2] Starting Frontend Server on http://localhost:3000
cd /d %~dp0ui
start "AARD Frontend Server" cmd /k "npm run dev"

REM Return to root directory
cd /d %~dp0

echo.
echo ========================================
echo Servers Started Successfully!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the servers.
echo.
pause
