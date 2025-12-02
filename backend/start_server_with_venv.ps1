# Скрипт для запуска сервера с активацией venv
$ErrorActionPreference = "Stop"

# Перейти в директорию backend
$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $backendDir

# Активировать виртуальное окружение
$venvPath = Join-Path (Split-Path -Parent $backendDir) "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (Test-Path $activateScript) {
    Write-Host "Активация виртуального окружения..." -ForegroundColor Green
    & $activateScript
} else {
    Write-Host "Виртуальное окружение не найдено: $venvPath" -ForegroundColor Red
    exit 1
}

# Проверить установку python-json-logger
Write-Host "Проверка зависимостей..." -ForegroundColor Green
python -c "from pythonjsonlogger import jsonlogger; print('✓ python-json-logger установлен')" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Установка python-json-logger..." -ForegroundColor Yellow
    pip install python-json-logger==2.0.7
}

# Запустить сервер
Write-Host "Запуск сервера..." -ForegroundColor Green
Write-Host "Сервер будет доступен на http://localhost:8000" -ForegroundColor Cyan
Write-Host "Для остановки нажмите CTRL+C" -ForegroundColor Yellow
Write-Host ""

python main.py

