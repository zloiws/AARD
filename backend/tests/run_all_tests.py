"""
Запуск всех тестов Фаз 3 и 4
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).parent.parent
import os

os.chdir(backend_dir)

print("=" * 80)
print("ЗАПУСК ВСЕХ ТЕСТОВ ФАЗ 3 И 4")
print("=" * 80)
print(f"Рабочая директория: {os.getcwd()}")
print()

# Тестовые наборы
test_suites = [
    {
        "name": "Фаза 3: Полные интеграционные тесты",
        "path": "tests/integration/test_phase3_full_integration.py"
    },
    {
        "name": "Фаза 4: WorkflowEngine тесты",
        "path": "tests/integration/test_workflow_engine.py"
    },
    {
        "name": "Фаза 4: Интеграционные тесты",
        "path": "tests/integration/test_phase4_integration.py"
    }
]

results = {}

for suite in test_suites:
    suite_name = suite["name"]
    test_path = suite["path"]
    
    print("\n" + "=" * 80)
    print(suite_name)
    print(f"Файл: {test_path}")
    print("=" * 80)
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    print(f"\nЗапуск команды: {' '.join(cmd)}\n")
    
    # Запуск с выводом в реальном времени
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1
    )
    
    # Вывод в реальном времени
    output_lines = []
    for line in process.stdout:
        print(line, end='')
        output_lines.append(line)
    
    process.wait()
    
    output = ''.join(output_lines)
    passed = process.returncode == 0
    results[suite_name] = {
        "passed": passed,
        "output": output,
        "returncode": process.returncode
    }
    
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"\n{status}: {suite_name} (exit code: {process.returncode})")

# Итоговая сводка
print("\n" + "=" * 80)
print("ИТОГОВАЯ СВОДКА")
print("=" * 80)

total_passed = sum(1 for r in results.values() if r["passed"])
total_failed = len(results) - total_passed

for suite_name, result in results.items():
    status = "✅ PASSED" if result["passed"] else "❌ FAILED"
    print(f"{status}: {suite_name}")

print()
print(f"Всего наборов тестов: {len(results)}")
print(f"Пройдено: {total_passed}")
print(f"Провалено: {total_failed}")
print("=" * 80)

sys.exit(0 if total_failed == 0 else 1)
