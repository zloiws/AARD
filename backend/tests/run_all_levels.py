"""
Запуск всех тестов по уровням с выводом
"""
import os
import subprocess
import sys
from pathlib import Path

os.chdir(Path(__file__).parent.parent)

levels = [
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

print("=" * 80)
print("ЗАПУСК ВСЕХ ТЕСТОВ ПО УРОВНЯМ")
print("=" * 80)
print()

results = {}

for i, test_name in enumerate(levels, 1):
    print(f"\n{'='*80}")
    print(f"УРОВЕНЬ {i}: {test_name}")
    print(f"{'='*80}\n")
    
    cmd = [sys.executable, "-m", "pytest", 
           f"tests/integration/test_phase3_full_integration.py::{test_name}",
           "-v", "-s", "--tb=short"]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                           text=True, encoding='utf-8', errors='replace', bufsize=1)
    
    output_lines = []
    for line in proc.stdout:
        print(line, end='')
        output_lines.append(line)
    
    proc.wait()
    output = ''.join(output_lines)
    
    passed = "PASSED" in output or proc.returncode == 0
    results[test_name] = passed
    
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"\n{status}: {test_name}\n")

print("\n" + "=" * 80)
print("ИТОГОВАЯ СВОДКА")
print("=" * 80)
for test_name, passed in results.items():
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{status}: {test_name}")

passed_count = sum(1 for v in results.values() if v)
print(f"\nВсего: {len(results)}, Пройдено: {passed_count}, Провалено: {len(results) - passed_count}")

sys.exit(0 if passed_count == len(results) else 1)
