"""
Запуск всех тестов Фаз 3 и 4 с сохранением результатов
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).parent.parent
import os

os.chdir(backend_dir)

# Результаты будут сохранены в файл
output_file = backend_dir / "tests" / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

test_suites = [
    {
        "name": "Фаза 3: Интеграционные тесты",
        "file": "tests/integration/test_phase3_full_integration.py",
        "tests": [
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
    },
    {
        "name": "Фаза 4: WorkflowEngine тесты",
        "file": "tests/integration/test_workflow_engine.py",
        "tests": None  # Все тесты в файле
    },
    {
        "name": "Фаза 4: Интеграционные тесты",
        "file": "tests/integration/test_phase4_integration.py",
        "tests": None  # Все тесты в файле
    }
]

results = {}
total_passed = 0
total_failed = 0

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ\n")
    f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 80 + "\n\n")
    
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ ФАЗ 3 И 4")
    print("=" * 80)
    print(f"Результаты сохраняются в: {output_file}")
    print()
    
    for suite in test_suites:
        suite_name = suite["name"]
        test_file = suite["file"]
        tests = suite["tests"]
        
        print(f"\n{'='*80}")
        print(f"{suite_name}")
        print(f"Файл: {test_file}")
        print(f"{'='*80}\n")
        
        f.write(f"\n{'='*80}\n")
        f.write(f"{suite_name}\n")
        f.write(f"Файл: {test_file}\n")
        f.write(f"{'='*80}\n\n")
        
        if tests:
            # Запуск конкретных тестов
            for test_name in tests:
                print(f"Запуск: {test_name}")
                f.write(f"Запуск: {test_name}\n")
                
                cmd = [
                    sys.executable, "-m", "pytest",
                    f"{test_file}::{test_name}",
                    "-v",
                    "--tb=short"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                
                passed = result.returncode == 0
                results[f"{suite_name}::{test_name}"] = passed
                
                if passed:
                    total_passed += 1
                else:
                    total_failed += 1
                
                f.write(result.stdout)
                if result.stderr:
                    f.write("\nSTDERR:\n")
                    f.write(result.stderr)
                
                status = "✅ PASSED" if passed else "❌ FAILED"
                print(f"  {status}: {test_name}")
                f.write(f"\n{status}: {test_name}\n\n")
        else:
            # Запуск всех тестов в файле
            print(f"Запуск всех тестов из {test_file}")
            f.write(f"Запуск всех тестов из {test_file}\n\n")
            
            cmd = [
                sys.executable, "-m", "pytest",
                test_file,
                "-v",
                "--tb=short"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            # Подсчет результатов из вывода pytest
            passed_count = result.stdout.count(' PASSED')
            failed_count = result.stdout.count(' FAILED')
            skipped_count = result.stdout.count(' SKIPPED')
            
            total_passed += passed_count
            total_failed += failed_count
            
            f.write(result.stdout)
            if result.stderr:
                f.write("\nSTDERR:\n")
                f.write(result.stderr)
            
            print(f"  Пройдено: {passed_count}, Провалено: {failed_count}, Пропущено: {skipped_count}")
            f.write(f"\nПройдено: {passed_count}, Провалено: {failed_count}, Пропущено: {skipped_count}\n\n")
    
    # Итоговая сводка
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СВОДКА")
    print("=" * 80)
    print(f"Всего пройдено: {total_passed}")
    print(f"Всего провалено: {total_failed}")
    print(f"Результаты сохранены в: {output_file}")
    print("=" * 80)
    
    f.write("\n" + "=" * 80 + "\n")
    f.write("ИТОГОВАЯ СВОДКА\n")
    f.write("=" * 80 + "\n")
    f.write(f"Всего пройдено: {total_passed}\n")
    f.write(f"Всего провалено: {total_failed}\n")
    f.write("=" * 80 + "\n")

sys.exit(0 if total_failed == 0 else 1)
