"""
Запуск тестов интеграции сервисов в RequestOrchestrator
"""
import sys
import subprocess
from pathlib import Path

backend_dir = Path(__file__).parent.parent
import os
os.chdir(backend_dir)

print("=" * 80)
print("ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ СЕРВИСОВ В REQUESTORCHESTRATOR")
print("=" * 80)
print()

test_file = "tests/integration/test_phase3_orchestrator_integration.py"

cmd = [
    sys.executable, "-m", "pytest",
    test_file,
    "-v",
    "-s",
    "--tb=short",
    "--color=yes"
]

print(f"Запуск команды: {' '.join(cmd)}\n")

result = subprocess.run(cmd, text=True, encoding='utf-8', errors='replace')

print("\n" + "=" * 80)
print(f"Exit code: {result.returncode}")
print("=" * 80)

sys.exit(result.returncode)
