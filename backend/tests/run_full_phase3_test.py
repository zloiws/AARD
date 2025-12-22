"""
Полный запуск интеграционных тестов Фазы 3 с выводом результатов
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import os
import subprocess


def run_tests():
    """Запуск тестов с полным выводом"""
    os.chdir(backend_dir)
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/integration/test_phase3_full_integration.py",
        "-v",
        "-s",
        "--tb=short",
        "--color=yes"
    ]
    
    print("=" * 80)
    print("ЗАПУСК ПОЛНОГО ИНТЕГРАЦИОННОГО ТЕСТА ФАЗЫ 3")
    print("=" * 80)
    print()
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    print()
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
