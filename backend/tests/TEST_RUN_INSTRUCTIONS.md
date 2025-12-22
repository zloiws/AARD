# Инструкции по запуску тестов

## Быстрый запуск

### Все тесты Фазы 3
```bash
cd backend
python -m pytest tests/integration/test_phase3_full_integration.py -v
```

### Все тесты Фазы 4 (WorkflowEngine)
```bash
cd backend
python -m pytest tests/integration/test_workflow_engine.py -v
```

### Все тесты Фазы 4 (Интеграция)
```bash
cd backend
python -m pytest tests/integration/test_phase4_integration.py -v
```

### Все тесты через скрипт
```bash
cd backend
python tests/run_all_tests.py
```

### Последовательный запуск тестов Фазы 3
```bash
cd backend
python tests/run_tests_sequentially.py
```

## Отдельные тесты

### Тест инициализации WorkflowEngine
```bash
python -m pytest tests/integration/test_workflow_engine.py::TestWorkflowEngineBasic::test_initialization -v
```

### Тест переходов состояний
```bash
python -m pytest tests/integration/test_workflow_engine.py::TestWorkflowEngineBasic::test_transition_to_parsing -v
```

### Тест уровня 1 Фазы 3
```bash
python -m pytest tests/integration/test_phase3_full_integration.py::test_level1_basic_context_creation -v
```

## Опции pytest

- `-v` - подробный вывод
- `-s` - показать print() вывод
- `--tb=short` - короткий traceback при ошибках
- `--tb=long` - полный traceback
- `-x` - остановиться на первой ошибке
- `--pdb` - запустить отладчик при ошибке

## Примеры

### Запуск с подробным выводом
```bash
python -m pytest tests/integration/test_workflow_engine.py -v -s
```

### Запуск с остановкой на первой ошибке
```bash
python -m pytest tests/integration/test_phase3_full_integration.py -v -x
```

### Запуск конкретного класса тестов
```bash
python -m pytest tests/integration/test_workflow_engine.py::TestWorkflowEngineBasic -v
```

## Структура тестов

### Фаза 3
- `test_phase3_full_integration.py` - 10 уровней интеграционных тестов
  - test_level1_basic_context_creation
  - test_level2_service_registry_with_context
  - test_level3_memory_service_real_operations
  - test_level4_reflection_service_real_llm
  - test_level5_meta_learning_real_analysis
  - test_level6_full_workflow_with_orchestrator
  - test_level7_complex_task_with_all_services
  - test_level8_error_recovery_with_reflection
  - test_level9_end_to_end_complex_scenario
  - test_level10_prompt_metrics_tracking

### Фаза 4
- `test_workflow_engine.py` - тесты WorkflowEngine
  - TestWorkflowEngineBasic - базовые тесты
  - TestWorkflowEngineStateManagement - управление состояниями
  - TestWorkflowEngineApprovalFlow - workflow с одобрением
  - TestWorkflowEngineStateInfo - информация о состоянии
  - TestWorkflowEngineFullFlow - полные workflow

- `test_phase4_integration.py` - интеграционные тесты Фазы 4
  - TestWorkflowEngineIntegration
  - TestErrorHandlingIntegration
  - TestAdaptiveApprovalIntegration
  - TestPhase4EndToEnd

## Примечания

- Некоторые тесты требуют реального LLM (помечены `@pytest.mark.asyncio`)
- Тесты с моками работают без внешних зависимостей
- WorkflowEventService опционально - тесты работают даже если сервис недоступен
