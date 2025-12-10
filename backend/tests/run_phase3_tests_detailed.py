"""
Детальный запуск тестов Фазы 3 с полным выводом
"""
import sys
import subprocess
from pathlib import Path

backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)

print("=" * 80)
print("ПОЛНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ ФАЗЫ 3")
print("=" * 80)
print()

# Запускаем тесты по уровням
test_levels = [
    "test_level1_basic_context_creation",
    "test_level2_service_registry_with_context",
    "test_level3_memory_service_real_operations",
    "test_level4_reflection_service_real_llm",
    "test_level5_meta_learning_real_analysis",
    "test_level6_full_workflow_with_orchestrator",
    "test_level7_complex_task_with_all_services",
    "test_level8_error_recovery_with_reflection",
    "test_level9_end_to_end_complex_scenario",
    "test_level10_prompt_metrics_tracking"
]

results = {}

for test_name in test_levels:
    print(f"\n{'='*80}")
    print(f"ЗАПУСК: {test_name}")
    print(f"{'='*80}\n")
    
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/integration/test_phase3_full_integration.py::{test_name}",
        "-v",
        "-s",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    results[test_name] = result.returncode == 0
    print(f"\n{'✅ PASSED' if results[test_name] else '❌ FAILED'}: {test_name}\n")

print("\n" + "=" * 80)
print("ИТОГОВАЯ СВОДКА")
print("=" * 80)
print()

passed = sum(1 for v in results.values() if v)
failed = len(results) - passed

for test_name, passed_test in results.items():
    status = "✅ PASSED" if passed_test else "❌ FAILED"
    print(f"{status}: {test_name}")

print()
print(f"Всего: {len(results)}")
print(f"Пройдено: {passed}")
print(f"Провалено: {failed}")
print("=" * 80)

sys.exit(0 if failed == 0 else 1)
