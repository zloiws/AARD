"""
Простой последовательный запуск тестов Фазы 3
"""
import pytest
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Список тестов по порядку (используем правильный формат пути)
tests = [
    "tests/integration/test_phase3_full_integration.py::test_level1_basic_context_creation",
    "tests/integration/test_phase3_full_integration.py::test_level2_service_registry_with_context",
    "tests/integration/test_phase3_full_integration.py::test_level3_memory_service_real_operations",
    "tests/integration/test_phase3_full_integration.py::test_level4_reflection_service_real_llm",
    "tests/integration/test_phase3_full_integration.py::test_level5_meta_learning_real_analysis",
    "tests/integration/test_phase3_full_integration.py::test_level6_full_workflow_with_orchestrator",
    "tests/integration/test_phase3_full_integration.py::test_level7_complex_task_with_all_services",
    "tests/integration/test_phase3_full_integration.py::test_level8_error_recovery_with_reflection",
    "tests/integration/test_phase3_full_integration.py::test_level9_end_to_end_complex_scenario",
    "tests/integration/test_phase3_full_integration.py::test_level10_prompt_metrics_tracking",
]

print("=" * 80)
print("ПОСЛЕДОВАТЕЛЬНЫЙ ЗАПУСК ТЕСТОВ ФАЗЫ 3")
print("=" * 80)
print()

results = {}

for i, test_path in enumerate(tests, 1):
    test_name = test_path.split("::")[-1]
    print(f"\n{'='*80}")
    print(f"УРОВЕНЬ {i}: {test_name}")
    print(f"{'='*80}\n")
    
    exit_code = pytest.main([
        test_path,
        "-v",
        "-s",
        "--tb=short"
    ])
    
    passed = exit_code == 0
    results[test_name] = passed
    
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"\n{status}: {test_name}\n")

print("\n" + "=" * 80)
print("ИТОГОВАЯ СВОДКА")
print("=" * 80)
print()

for test_name, passed in results.items():
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{status}: {test_name}")

passed_count = sum(1 for v in results.values() if v)
failed_count = len(results) - passed_count

print()
print(f"Всего тестов: {len(results)}")
print(f"Пройдено: {passed_count}")
print(f"Провалено: {failed_count}")
print("=" * 80)

sys.exit(0 if failed_count == 0 else 1)
