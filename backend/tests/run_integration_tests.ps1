# PowerShell скрипт для запуска интеграционных тестов

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Integration Tests with Real LLM" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка Python
Write-Host "0. Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "   ✗ Python not found" -ForegroundColor Red
    exit 1
}

# Проверка pytest
Write-Host ""
Write-Host "1. Checking pytest..." -ForegroundColor Yellow
$pytestCheck = python -m pytest --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ pytest is available" -ForegroundColor Green
} else {
    Write-Host "   Installing pytest..." -ForegroundColor Yellow
    python -m pip install pytest pytest-asyncio -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ pytest installed" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Failed to install pytest" -ForegroundColor Red
        exit 1
    }
}

# Проверка Ollama
Write-Host ""
Write-Host "2. Checking Ollama server..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   ✓ Ollama server is running" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Ollama server is not accessible" -ForegroundColor Red
    Write-Host "   Please start Ollama server first" -ForegroundColor Red
    Write-Host "   You can continue anyway, but tests may fail" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host ""
Write-Host "3. Running simple question tests..." -ForegroundColor Yellow
python -m pytest tests/test_integration_simple_question.py -v -s
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ⚠ Some tests failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "4. Running code generation tests..." -ForegroundColor Yellow
python -m pytest tests/test_integration_code_generation.py -v -s
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ⚠ Some tests failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "5. Running complex task tests (slow)..." -ForegroundColor Yellow
$runSlow = Read-Host "Run slow tests? (y/n)"
if ($runSlow -eq "y") {
    python -m pytest tests/test_integration_complex_task.py -v -s -m slow
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ⚠ Some tests failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "   Skipped" -ForegroundColor Gray
}

Write-Host ""
Write-Host "6. Running prompt improvement tests (slow)..." -ForegroundColor Yellow
if ($runSlow -eq "y") {
    python -m pytest tests/test_integration_prompt_improvement.py -v -s -m slow
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ⚠ Some tests failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "   Skipped" -ForegroundColor Gray
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "All integration tests completed!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
