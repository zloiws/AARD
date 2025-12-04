# Скрипт реорганизации файлов проекта
# Перемещает файлы в правильные места

Write-Host "📋 РЕОРГАНИЗАЦИЯ ФАЙЛОВ ПРОЕКТА" -ForegroundColor Cyan
Write-Host ""

# 1. Переместить тестовые скрипты из backend/scripts/ в backend/tests/scripts/
Write-Host "1. Перемещение тестовых скриптов..." -ForegroundColor Yellow
$testScripts = Get-ChildItem "backend/scripts/test_*.py" -ErrorAction SilentlyContinue
if ($testScripts) {
    New-Item -ItemType Directory -Force -Path "backend/tests/scripts" | Out-Null
    foreach ($script in $testScripts) {
        Move-Item -Path $script.FullName -Destination "backend/tests/scripts/" -Force
        Write-Host "  ✅ Перемещен: $($script.Name)" -ForegroundColor Green
    }
} else {
    Write-Host "  ℹ️  Тестовые скрипты не найдены" -ForegroundColor Gray
}

Write-Host ""

# 2. Переместить документацию из backend/ в docs/ (только если нет дубликатов)
Write-Host "2. Перемещение документации..." -ForegroundColor Yellow
$docs = Get-ChildItem "backend/*.md" -ErrorAction SilentlyContinue
foreach ($doc in $docs) {
    $destPath = "docs/$($doc.Name)"
    if (Test-Path $destPath) {
        Write-Host "  ⚠️  Дубликат, пропускаю: $($doc.Name)" -ForegroundColor Yellow
        # Удаляем дубликат из backend, оставляем в docs
        Remove-Item $doc.FullName -Force
    } else {
        Move-Item -Path $doc.FullName -Destination "docs/" -Force
        Write-Host "  ✅ Перемещен: $($doc.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "✅ РЕОРГАНИЗАЦИЯ ЗАВЕРШЕНА!" -ForegroundColor Green

