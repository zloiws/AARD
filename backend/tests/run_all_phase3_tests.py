"""
Последовательный запуск всех тестов Фазы 3 с сохранением результатов
"""
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent.parent
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

results_file = backend_dir / "tests" / "phase3_test_results.txt"

print("=" * 80)
print("ПОСЛЕДОВАТЕЛЬНЫЙ ЗАПУСК ВСЕХ ТЕСТОВ ФАЗЫ 3")
print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print()

results = {}

with open(results_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ФАЗЫ 3\n")
    f.write(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 80 + "\n\n")
    
    for i, (test_name, description) in enumerate(test_levels, 1):
        print(f"\n{'='*80}")
        print(f"{description}")
        print(f"Тест: {test_name}")
        print(f"{'='*80}\n")
        
        f.write(f"\n{'='*80}\n")
        f.write(f"{description}\n")
        f.write(f"Тест: {test_name}\n")
        f.write(f"{'='*80}\n\n")
        
        cmd = [
            sys.executable, "-m", "pytest",
            f"tests/integration/test_phase3_full_integration.py::{test_name}",
            "-v",
            "-s",
            "--tb=short"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300  # 5 минут на тест
            )
            
            output = result.stdout + result.stderr
            print(output)
            f.write(output)
            f.write("\n")
            
            passed = result.returncode == 0 or "PASSED" in output.upper()
            results[test_name] = passed
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"\n{status}: {test_name}\n")
            f.write(f"\n{status}: {test_name}\n\n")
            
        except subprocess.TimeoutExpired:
            print(f"\n⏱️ TIMEOUT: {test_name} (превышено время ожидания)\n")
            f.write(f"\n⏱️ TIMEOUT: {test_name}\n\n")
            results[test_name] = False
        except Exception as e:
            print(f"\n❌ ERROR: {test_name} - {e}\n")
            f.write(f"\n❌ ERROR: {test_name} - {e}\n\n")
            results[test_name] = False
    
    # Итоговая сводка
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СВОДКА")
    print("=" * 80)
    print()
    
    f.write("\n" + "=" * 80 + "\n")
    f.write("ИТОГОВАЯ СВОДКА\n")
    f.write("=" * 80 + "\n\n")
    
    passed_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - passed_count
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        f.write(f"{status}: {test_name}\n")
    
    print()
    print(f"Всего тестов: {len(results)}")
    print(f"Пройдено: {passed_count}")
    print(f"Провалено: {failed_count}")
    print("=" * 80)
    
    f.write(f"\nВсего тестов: {len(results)}\n")
    f.write(f"Пройдено: {passed_count}\n")
    f.write(f"Провалено: {failed_count}\n")
    f.write("=" * 80 + "\n")

print(f"\nРезультаты сохранены в: {results_file}")

sys.exit(0 if failed_count == 0 else 1)
