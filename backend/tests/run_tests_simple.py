"""
Простой запуск тестов с выводом в консоль и файл
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)

# Файл для результатов
results_file = backend_dir / "tests" / "test_run_results.txt"

print("Запуск тестов...")
print(f"Результаты будут сохранены в: {results_file}")
print()

# Запуск тестов Фазы 3
print("=" * 80)
print("ФАЗА 3: Интеграционные тесты")
print("=" * 80)

cmd = [
    sys.executable, "-m", "pytest",
    "tests/integration/test_phase3_full_integration.py",
    "-v",
    "--tb=short",
    "-x"  # Остановиться на первой ошибке
]

with open(results_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ\n")
    f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 80 + "\n\n")
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    
    output = result.stdout
    print(output)
    f.write(output)
    
    f.write("\n" + "=" * 80 + "\n")
    f.write(f"Exit code: {result.returncode}\n")
    f.write("=" * 80 + "\n")

print(f"\nРезультаты сохранены в: {results_file}")
print(f"Exit code: {result.returncode}")

sys.exit(result.returncode)
