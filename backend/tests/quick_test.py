"""Быстрый тест для проверки работоспособности"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("БЫСТРАЯ ПРОВЕРКА ТЕСТОВ")
print("=" * 80)
print()

# Проверка импортов
try:
    from tests.integration.test_workflow_engine import TestWorkflowEngineBasic
    print("✅ test_workflow_engine.py импортирован успешно")
except Exception as e:
    print(f"❌ Ошибка импорта test_workflow_engine.py: {e}")

try:
    from tests.integration.test_phase3_full_integration import \
        test_level1_basic_context_creation
    print("✅ test_phase3_full_integration.py импортирован успешно")
except Exception as e:
    print(f"❌ Ошибка импорта test_phase3_full_integration.py: {e}")

try:
    from tests.integration.test_phase4_integration import \
        TestWorkflowEngineIntegration
    print("✅ test_phase4_integration.py импортирован успешно")
except Exception as e:
    print(f"❌ Ошибка импорта test_phase4_integration.py: {e}")

print()
print("=" * 80)
print("Для запуска тестов используйте:")
print("  python -m pytest tests/integration/test_workflow_engine.py -v")
print("  python -m pytest tests/integration/test_phase3_full_integration.py -v")
print("  python -m pytest tests/integration/test_phase4_integration.py -v")
print("=" * 80)
