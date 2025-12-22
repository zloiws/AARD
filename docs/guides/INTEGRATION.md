# Архитектура интеграции компонентов AARD

## Обзор

Система интеграции компонентов AARD обеспечивает единообразное взаимодействие всех сервисов через централизованный оркестратор и единый контекст выполнения.

## Компоненты

### ExecutionContext

Единый контекст выполнения для всех сервисов, содержащий:
- `db: Session` - сессия базы данных
- `workflow_id: str` - уникальный ID workflow для отслеживания
- `trace_id: Optional[str]` - ID трассировки OpenTelemetry
- `session_id: Optional[str]` - ID сессии чата
- `user_id: Optional[str]` - ID пользователя
- `metadata: Dict[str, Any]` - дополнительные метаданные
- `prompt_manager: Optional[PromptManager]` - менеджер промптов (добавляется в Фазе 2)

**Создание контекста:**
```python
from app.core.execution_context import ExecutionContext

# Из db session
context = ExecutionContext.from_db_session(db)

# Из FastAPI request
context = ExecutionContext.from_request(db, request, session_id="...")
```

### ServiceRegistry

Централизованный реестр сервисов с lazy initialization и кэшированием.

**Особенности:**
- Singleton pattern
- Кэширование экземпляров сервисов по workflow_id
- Поддержка обратной совместимости (работа с db: Session)
- Регистрация кастомных фабрик для создания сервисов

**Использование:**
```python
from app.core.service_registry import get_service_registry
from app.services.planning_service import PlanningService

registry = get_service_registry()
planning_service = registry.get_service(PlanningService, context)
```

### RequestOrchestrator

Центральный оркестратор для обработки всех запросов пользователей.

**Функционал:**
- Определение типа запроса через RequestRouter
- Маршрутизация на соответствующий обработчик:
  - `SIMPLE_QUESTION` → прямой LLM ответ
  - `INFORMATION_QUERY` → поиск в памяти/интернете
  - `CODE_GENERATION` → PlanningService + ExecutionService
  - `COMPLEX_TASK` → PlanningService + ExecutionService + ReflectionService
  - `PLANNING_ONLY` → только планирование
- Обработка ошибок с автоматическим fallback
- Интеграция с WorkflowTracker для отслеживания

**Использование:**
```python
from app.core.request_orchestrator import RequestOrchestrator

orchestrator = RequestOrchestrator()
result = await orchestrator.process_request(
    message="Создай функцию для вычисления факториала",
    context=context
)
```

## Workflow обработки запроса

1. **Создание ExecutionContext** - из request или db session
2. **Определение типа запроса** - через RequestRouter
3. **Маршрутизация** - выбор соответствующего обработчика
4. **Обработка** - выполнение через соответствующие сервисы
5. **Результат** - возврат OrchestrationResult

## Интеграция с существующими сервисами

### Фаза 1-2: Базовые сервисы ✅
- ✅ PlanningService - поддерживает ExecutionContext
- ✅ ExecutionService - поддерживает ExecutionContext
- ✅ RequestOrchestrator - использует ExecutionContext

### Фаза 3: Расширенные сервисы ✅
- ✅ MemoryService - обновлен для работы с ExecutionContext
- ✅ ReflectionService - обновлен для работы с ExecutionContext + запись метрик промптов
- ✅ MetaLearningService - обновлен для работы с ExecutionContext

Все сервисы поддерживают обратную совместимость:
- Сервисы создаются через `ServiceRegistry.get_service(ServiceClass, context)`
- Если передан Session вместо ExecutionContext, автоматически создается минимальный контекст
- Все сервисы имеют доступ к `workflow_id` и другим метаданным из контекста

## Планы развития

### Фаза 2: Интеграция системы промптов ✅
- ✅ PromptManager для управления промптами
- ✅ Автоматический анализ производительности промптов
- ✅ A/B тестирование версий промптов

### Фаза 3: Рефакторинг сервисов ✅
- ✅ Обновление всех сервисов для работы с ExecutionContext
- ✅ Интеграция MemoryService, ReflectionService, MetaLearningService
- ✅ Запись метрик промптов в ReflectionService
- ✅ Тесты для всех обновленных сервисов

### Фаза 4: Улучшение интеграции ✅
- ✅ WorkflowEngine для управления состояниями
- ✅ Улучшенная обработка ошибок с автоматическим replanning
- ✅ Интеграция AdaptiveApprovalService
- ✅ Тесты для всех компонентов Фазы 4

### Фаза 5: Комплексное тестирование и финализация ✅
- ✅ E2E тесты для полных workflow
- ✅ Комплексное тестирование всех компонентов
- ✅ Финальная документация (INTEGRATION_ARCHITECTURE.md, INTEGRATION_GUIDE.md, MIGRATION_GUIDE.md)
- ✅ Финальная чистка кода

## Тестирование

Созданы тесты для всех компонентов:

### Фаза 1-2:
- `test_execution_context.py` - тесты ExecutionContext
- `test_service_registry.py` - тесты ServiceRegistry
- `test_request_orchestrator.py` - тесты RequestOrchestrator
- `test_orchestrator_integration.py` - интеграционные тесты

### Фаза 3:
- `test_memory_service_integration.py` - тесты MemoryService с ExecutionContext
- `test_reflection_service_integration.py` - тесты ReflectionService с ExecutionContext
- `test_meta_learning_service_integration.py` - тесты MetaLearningService с ExecutionContext
- `test_phase3_full_integration.py` - полные интеграционные тесты Фазы 3

### Фаза 4:
- `test_workflow_engine.py` - тесты WorkflowEngine (управление состояниями, переходы, валидация)
- `test_phase4_integration.py` - интеграционные тесты Фазы 4 (WorkflowEngine + RequestOrchestrator, обработка ошибок, AdaptiveApprovalService)

### Фаза 5:
- `test_phase5_e2e_workflows.py` - E2E тесты для полных workflow сценариев
- `run_phase5_comprehensive_tests.py` - скрипт для комплексного тестирования всех фаз

Запуск тестов:
```bash
# Фаза 1-2
pytest backend/tests/test_execution_context.py -v
pytest backend/tests/test_service_registry.py -v
pytest backend/tests/test_request_orchestrator.py -v
pytest backend/tests/integration/test_orchestrator_integration.py -v

# Фаза 3
pytest backend/tests/test_memory_service_integration.py -v
pytest backend/tests/test_reflection_service_integration.py -v
pytest backend/tests/test_meta_learning_service_integration.py -v
pytest backend/tests/integration/test_phase3_full_integration.py -v

# Фаза 4
pytest backend/tests/integration/test_workflow_engine.py -v
pytest backend/tests/integration/test_phase4_integration.py -v

# Фаза 5
pytest backend/tests/integration/test_phase5_e2e_workflows.py -v
python backend/tests/run_phase5_comprehensive_tests.py
```

## Документация

Дополнительная документация по интеграции:

- [INTEGRATION_ARCHITECTURE.md](./INTEGRATION_ARCHITECTURE.md) - Детальная архитектура интеграции
- [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - Руководство для разработчиков
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Руководство по миграции на новую архитектуру
```
