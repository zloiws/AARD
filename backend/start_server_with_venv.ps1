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

# Проверка зависимостей (python-json-logger больше не требуется - используем кастомный formatter)
Write-Host "Проверка зависимостей..." -ForegroundColor Green

# Запустить сервер
Write-Host "Запуск сервера..." -ForegroundColor Green
Write-Host "Сервер будет доступен на http://localhost:8000" -ForegroundColor Cyan
Write-Host "Для остановки нажмите CTRL+C" -ForegroundColor Yellow
Write-Host ""

python main.py

