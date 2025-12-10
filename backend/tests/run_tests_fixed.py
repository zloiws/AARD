"""Fixed test runner with better result parsing"""
import subprocess
import sys
import re
from pathlib import Path

backend_dir = Path(__file__).parent.parent

test_files = [
    "tests/test_integration_basic.py",
    "tests/test_integration_simple_question.py",
    "tests/test_integration_code_generation.py"
]

print("=" * 80)
print("ЗАПУСК ИНТЕГРАЦИОННЫХ ТЕСТОВ")
print("=" * 80)
print()

results = []

for test_file in test_files:
    print(f"\n{'='*80}")
    print(f"Тестирование: {test_file}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=line"],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        
        # Показываем вывод
        print(stdout)
        if stderr and 'UnicodeDecodeError' not in stderr:
            print("STDERR:", stderr[:500])
        
        # Парсим результаты
        passed = 0
        failed = 0
        skipped = 0
        
        # Метод 1: Ищем итоговую строку pytest
        lines = stdout.split('\n')
        for line in reversed(lines):
            line_lower = line.lower().strip()
            # Ищем строку вида "5 passed in 1.23s" или "=== 5 passed ==="
            if ('passed' in line_lower or 'failed' in line_lower or 'skipped' in line_lower):
                # Проверяем, что это итоговая строка (содержит "in" или "=")
                if 'in' in line_lower or '=' in line_lower or line_lower.startswith('='):
                    passed_match = re.search(r'(\d+)\s+passed', line_lower)
                    failed_match = re.search(r'(\d+)\s+failed', line_lower)
                    skipped_match = re.search(r'(\d+)\s+skipped', line_lower)
                    
                    if passed_match:
                        passed = int(passed_match.group(1))
                    if failed_match:
                        failed = int(failed_match.group(1))
                    if skipped_match:
                        skipped = int(skipped_match.group(1))
                    
                    if passed > 0 or failed > 0 or skipped > 0:
                        break
        
        # Метод 2: Если не нашли итоговую строку, считаем по отдельным тестам
        if passed == 0 and failed == 0 and skipped == 0:
            for line in lines:
                # Ищем строки вида "tests/test_file.py::test_name PASSED"
                if '::test_' in line:
                    if ' PASSED' in line:
                        passed += 1
                    elif ' FAILED' in line:
                        failed += 1
                    elif ' SKIPPED' in line:
                        skipped += 1
        
        results.append({
            'file': test_file,
            'returncode': result.returncode,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'stdout': stdout
        })
        
    except Exception as e:
        print(f"Ошибка: {e}")
        results.append({
            'file': test_file,
            'returncode': 1,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'stdout': ""
        })

# Сводка
print("\n" + "=" * 80)
print("СВОДКА РЕЗУЛЬТАТОВ")
print("=" * 80)

total_passed = 0
total_failed = 0
total_skipped = 0

for r in results:
    status = "✅ PASSED" if r['returncode'] == 0 else "❌ FAILED"
    print(f"\n{r['file']}: {status}")
    print(f"  PASSED: {r['passed']}, FAILED: {r['failed']}, SKIPPED: {r['skipped']}")
    
    # Если результаты 0, но тест прошел, попробуем найти в выводе
    if r['passed'] == 0 and r['failed'] == 0 and r['skipped'] == 0 and r['returncode'] == 0:
        # Ищем в выводе
        stdout_lines = r['stdout'].split('\n')
        for line in stdout_lines:
            if 'passed' in line.lower() and 'failed' in line.lower():
                print(f"  (Найдено в выводе: {line.strip()})")
                break
    
    total_passed += r['passed']
    total_failed += r['failed']
    total_skipped += r['skipped']

print("\n" + "=" * 80)
print(f"ИТОГО: PASSED={total_passed}, FAILED={total_failed}, SKIPPED={total_skipped}")
print("=" * 80)

sys.exit(0 if total_failed == 0 else 1)
