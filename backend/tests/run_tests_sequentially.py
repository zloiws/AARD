"""
Последовательный запуск всех тестов Фазы 3 с выводом результатов
"""
import sys
import subprocess
from pathlib import Path

backend_dir = Path(__file__).parent.parent
import os
os.chdir(backend_dir)

test_levels = [
    ("test_level1_basic_context_creation", "Уровень 1: Базовое создание ExecutionContext"),
    ("test_level2_service_registry_with_context", "Уровень 2: Создание сервисов через ServiceRegistry"),
    ("test_level3_memory_service_real_operations", "Уровень 3: Реальные операции с MemoryService"),
    ("test_level4_reflection_service_real_llm", "Уровень 4: ReflectionService с реальным LLM"),
    ("test_level5_meta_learning_real_analysis", "Уровень 5: MetaLearningService с реальным анализом"),
    ("test_level6_full_workflow_with_orchestrator", "Уровень 6: Полный workflow с RequestOrchestrator"),
    ("test_level7_complex_task_with_all_services", "Уровень 7: Сложная задача со всеми сервисами"),
    ("test_level8_error_recovery_with_reflection", "Уровень 8: Восстановление после ошибки"),
    ("test_level9_end_to_end_complex_scenario", "Уровень 9: End-to-end сложный сценарий"),
    ("test_level10_prompt_metrics_tracking", "Уровень 10: Отслеживание метрик промптов")
]

results = {}

print("=" * 80)
print("ПОСЛЕДОВАТЕЛЬНЫЙ ЗАПУСК ТЕСТОВ ФАЗЫ 3")
print("=" * 80)
print()

for test_name, description in test_levels:
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"Тест: {test_name}")
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
    
    passed = result.returncode == 0
    results[test_name] = passed
    
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"\n{status}: {test_name}")
    print()

print("\n" + "=" * 80)
print("ИТОГОВАЯ СВОДКА")
print("=" * 80)
print()

passed_count = sum(1 for v in results.values() if v)
failed_count = len(results) - passed_count

for test_name, passed in results.items():
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{status}: {test_name}")

print()
print(f"Всего тестов: {len(results)}")
print(f"Пройдено: {passed_count}")
print(f"Провалено: {failed_count}")
print("=" * 80)

sys.exit(0 if failed_count == 0 else 1)
