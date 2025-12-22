"""
Запуск тестов для всех выполненных этапов
"""
import subprocess
import sys

import pytest


def run_phase_tests():
    """Запустить тесты для всех выполненных этапов"""
    
    phases = [
        ("Этап 1: Критические исправления", "test_phase1_critical_fixes.py"),
        ("Этап 2: Dual-Model архитектура", "test_phase2_dual_model.py"),
        ("Этап 3: Уровни автономности", "test_phase3_autonomy_levels.py"),
        ("Этап 4: Workflow Engine", "test_phase4_workflow_engine.py"),
        ("Комплексные интеграционные тесты", "test_integration_comprehensive.py"),
    ]
    
    results = {}
    
    for phase_name, test_file in phases:
        print(f"\n{'='*60}")
        print(f"Запуск тестов: {phase_name}")
        print(f"Файл: {test_file}")
        print(f"{'='*60}\n")
        
        try:
            result = pytest.main([
                f"tests/{test_file}",
                "-v",
                "--tb=short",
                "-x"  # Остановиться на первой ошибке
            ])
            results[phase_name] = "PASSED" if result == 0 else "FAILED"
        except Exception as e:
            print(f"Ошибка при запуске тестов {phase_name}: {e}")
            results[phase_name] = "ERROR"
    
    # Итоговый отчет
    print(f"\n{'='*60}")
    print("ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*60}\n")
    
    for phase_name, status in results.items():
        status_symbol = "✅" if status == "PASSED" else "❌"
        print(f"{status_symbol} {phase_name}: {status}")
    
    total = len(results)
    passed = sum(1 for s in results.values() if s == "PASSED")
    
    print(f"\nВсего этапов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Провалено: {total - passed}")
    
    return all(s == "PASSED" for s in results.values())


if __name__ == "__main__":
    success = run_phase_tests()
    sys.exit(0 if success else 1)

