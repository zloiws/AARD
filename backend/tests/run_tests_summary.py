"""Simple test runner with summary"""
import re
import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
import os

os.chdir(backend_dir)

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
    print(f"{'='*80}")
    
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
        
        # Показываем только важные строки
        lines = stdout.split('\n')
        for line in lines:
            if any(keyword in line for keyword in ['PASSED', 'FAILED', 'SKIPPED', 'passed', 'failed', 'error', '::test_']):
                print(line)
        
        # Парсим итоговую строку pytest
        summary_line = None
        for line in reversed(lines):
            if 'passed' in line.lower() or 'failed' in line.lower():
                summary_line = line.strip()
                print(f"\n{summary_line}")
                break
        
        # Извлекаем числа из итоговой строки
        passed = 0
        failed = 0
        skipped = 0
        
        if summary_line:
            passed_match = re.search(r'(\d+)\s+passed', summary_line.lower())
            failed_match = re.search(r'(\d+)\s+failed', summary_line.lower())
            skipped_match = re.search(r'(\d+)\s+skipped', summary_line.lower())
            
            if passed_match:
                passed = int(passed_match.group(1))
            if failed_match:
                failed = int(failed_match.group(1))
            if skipped_match:
                skipped = int(skipped_match.group(1))
        
        results.append({
            'file': test_file,
            'returncode': result.returncode,
            'passed': passed,
            'failed': failed,
            'skipped': skipped
        })
        
        if stderr and 'UnicodeDecodeError' not in stderr:
            print(f"\nWarnings: {stderr[:100]}...")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        results.append({
            'file': test_file,
            'returncode': 1,
            'passed': 0,
            'failed': 0,
            'skipped': 0
        })

# Итоговая сводка
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
    
    total_passed += r['passed']
    total_failed += r['failed']
    total_skipped += r['skipped']

print("\n" + "=" * 80)
print(f"ИТОГО: PASSED={total_passed}, FAILED={total_failed}, SKIPPED={total_skipped}")
print("=" * 80)

sys.exit(0 if total_failed == 0 else 1)
