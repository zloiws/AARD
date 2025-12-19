"""
Комплексное тестирование Фазы 5
Запускает все тесты и собирает статистику покрытия
"""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).parent.parent
import os

os.chdir(backend_dir)

print("=" * 80)
print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ФАЗЫ 5")
print("=" * 80)
print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Список тестовых файлов по фазам
test_files = {
    "Фаза 1-2: Базовые компоненты": [
        "tests/test_execution_context.py",
        "tests/test_service_registry.py",
        "tests/test_request_orchestrator.py",
    ],
    "Фаза 3: Расширенные сервисы": [
        "tests/test_memory_service_integration.py",
        "tests/test_reflection_service_integration.py",
        "tests/test_meta_learning_service_integration.py",
        "tests/integration/test_phase3_full_integration.py",
        "tests/integration/test_phase3_orchestrator_integration.py",
    ],
    "Фаза 4: Улучшение интеграции": [
        "tests/integration/test_workflow_engine.py",
        "tests/integration/test_phase4_integration.py",
    ],
    "Фаза 5: E2E тесты": [
        "tests/integration/test_phase5_e2e_workflows.py",
    ],
}

results = {}
total_passed = 0
total_failed = 0
total_skipped = 0

for phase_name, files in test_files.items():
    print(f"\n{'=' * 80}")
    print(f"{phase_name}")
    print(f"{'=' * 80}\n")
    
    phase_passed = 0
    phase_failed = 0
    phase_skipped = 0
    
    for test_file in files:
        if not Path(test_file).exists():
            print(f"⚠️  Файл не найден: {test_file}")
            continue
        
        print(f"Запуск: {test_file}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--no-header",
            "-q"  # Quiet mode для более компактного вывода
        ]
        
        try:
            result = subprocess.run(
                cmd,
                text=True,
                encoding='utf-8',
                errors='replace',
                capture_output=True,
                timeout=300  # 5 минут на файл
            )
            
            # Парсим результаты
            output = result.stdout + result.stderr
            output_lower = output.lower()
            
            # Ищем итоговую строку pytest
            # Форматы: "X passed", "X passed, Y failed", "X passed, Y failed, Z skipped"
            passed = 0
            failed = 0
            skipped = 0
            
            # Ищем в обратном порядке (результаты обычно в конце)
            lines = output.split('\n')
            for line in reversed(lines):
                line_lower = line.lower()
                # Ищем полную строку с результатами
                # Пример: "5 passed, 1 failed, 2 skipped in 10.23s"
                full_match = re.search(r'(\d+)\s+passed(?:,\s*(\d+)\s+failed)?(?:,\s*(\d+)\s+skipped)?', line_lower)
                if full_match:
                    passed = int(full_match.group(1))
                    if full_match.group(2):
                        failed = int(full_match.group(2))
                    if full_match.group(3):
                        skipped = int(full_match.group(3))
                    break
            
            # Если не нашли полную строку, ищем отдельно
            if passed == 0 and failed == 0 and skipped == 0:
                # Ищем "X passed" (может быть без других значений)
                passed_match = re.search(r'(\d+)\s+passed', output_lower)
                if passed_match:
                    passed = int(passed_match.group(1))
                
                # Ищем "X failed"
                failed_match = re.search(r'(\d+)\s+failed', output_lower)
                if failed_match:
                    failed = int(failed_match.group(1))
                
                # Ищем "X skipped"
                skipped_match = re.search(r'(\d+)\s+skipped', output_lower)
                if skipped_match:
                    skipped = int(skipped_match.group(1))
            
            # Также учитываем ERROR как failed
            error_match = re.search(r'(\d+)\s+error', output_lower)
            if error_match:
                errors = int(error_match.group(1))
                failed += errors  # ERROR тоже считается как failed
            
            phase_passed += passed
            phase_failed += failed
            phase_skipped += skipped
            
            # Показываем результаты
            status_icon = "✅" if result.returncode == 0 and failed == 0 else "❌"
            print(f"  {status_icon} PASSED: {passed}, FAILED: {failed}, SKIPPED: {skipped}")
            
            # Если не нашли результаты, показываем последние строки вывода для отладки
            if passed == 0 and failed == 0 and skipped == 0:
                # Показываем последние строки вывода
                last_lines = [line for line in output.split('\n') if line.strip()][-3:]
                if last_lines:
                    print(f"    (Отладка: последние строки вывода)")
                    for line in last_lines:
                        if len(line) > 100:
                            line = line[:100] + "..."
                        print(f"    {line}")
            
            if result.returncode != 0 and failed == 0:
                # Если код возврата не 0, но не нашли failed, показываем ошибки
                error_lines = [line for line in output.split('\n') if 'ERROR' in line or 'FAILED' in line or 'Error' in line][:3]
                if error_lines:
                    print(f"    Ошибки:")
                    for line in error_lines:
                        if len(line) > 150:
                            line = line[:150] + "..."
                        print(f"    {line}")
            
        except subprocess.TimeoutExpired:
            print(f"  ⏱️  Таймаут (более 5 минут)")
            phase_failed += 1
        except Exception as e:
            print(f"  ❌ Ошибка запуска: {e}")
            phase_failed += 1
    
    results[phase_name] = {
        "passed": phase_passed,
        "failed": phase_failed,
        "skipped": phase_skipped
    }
    
    total_passed += phase_passed
    total_failed += phase_failed
    total_skipped += phase_skipped

# Итоговая сводка
print("\n" + "=" * 80)
print("ИТОГОВАЯ СВОДКА")
print("=" * 80)

for phase_name, stats in results.items():
    total = stats["passed"] + stats["failed"] + stats["skipped"]
    print(f"\n{phase_name}:")
    print(f"  PASSED: {stats['passed']}")
    print(f"  FAILED: {stats['failed']}")
    print(f"  SKIPPED: {stats['skipped']}")
    print(f"  Всего: {total}")

print(f"\n{'=' * 80}")
print(f"ВСЕГО:")
print(f"  PASSED: {total_passed}")
print(f"  FAILED: {total_failed}")
print(f"  SKIPPED: {total_skipped}")
print(f"  Всего: {total_passed + total_failed + total_skipped}")
print(f"{'=' * 80}")

if total_failed == 0:
    print("\n✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    exit_code = 0
else:
    print(f"\n❌ НАЙДЕНО {total_failed} ОШИБОК")
    exit_code = 1

# Выход только если скрипт запущен напрямую
if __name__ == "__main__":
    sys.exit(exit_code)
