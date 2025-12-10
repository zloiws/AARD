# Start AARD - Backend and Frontend servers
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting AARD Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    pause
    exit 1
}

# Start backend
Write-Host "[1/2] Starting Backend Server..." -ForegroundColor Green
$backendScript = @"
cd `"$PSScriptRoot\backend`"
& `"$PSScriptRoot\venv\Scripts\python.exe`" main.py
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript -WindowStyle Normal

# Wait a bit for backend to start
Start-Sleep -Seconds 3

# Check if node_modules exists
if (-not (Test-Path "ui\node_modules")) {
    Write-Host "ERROR: node_modules not found!" -ForegroundColor Red
    Write-Host "Please run: cd ui && npm install" -ForegroundColor Yellow
    pause
    exit 1
}

# Start frontend
Write-Host "[2/2] Starting Frontend Server..." -ForegroundColor Green
$frontendScript = @"
cd `"$PSScriptRoot\ui`"
npm run dev
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Both servers are starting..." -ForegroundColor Cyan
Write-Host "Backend: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Servers are running in separate windows." -ForegroundColor Green
Write-Host "Press any key to exit this script (servers will continue running)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
