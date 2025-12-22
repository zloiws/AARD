# Архитектура интеграции компонентов AARD

## Обзор

Система интеграции компонентов AARD обеспечивает единообразное взаимодействие всех сервисов через централизованный оркестратор и единый контекст выполнения. Архитектура построена на принципах:

- **Единый контекст выполнения** (ExecutionContext)
- **Централизованный оркестратор** (RequestOrchestrator)
- **Реестр сервисов** (ServiceRegistry)
- **Управление состояниями** (WorkflowEngine)
- **Адаптивное одобрение** (AdaptiveApprovalService)

## Компоненты архитектуры

### 1. ExecutionContext

**Назначение:** Единый контекст выполнения для всех сервисов

**Содержит:**
- `db: Session` - сессия базы данных
- `workflow_id: str` - уникальный ID workflow для отслеживания
- `trace_id: Optional[str]` - ID трассировки OpenTelemetry
- `session_id: Optional[str]` - ID сессии чата
- `user_id: Optional[str]` - ID пользователя
- `metadata: Dict[str, Any]` - дополнительные метаданные
- `prompt_manager: Optional[PromptManager]` - менеджер промптов
- `workflow_engine: Optional[WorkflowEngine]` - движок workflow

**Создание:**
```python
from app.core.execution_context import ExecutionContext

# Из db session
context = ExecutionContext.from_db_session(db)

# Из FastAPI request
context = ExecutionContext.from_request(db, request, session_id="...")
```

### 2. ServiceRegistry

**Назначение:** Централизованный реестр сервисов с lazy initialization

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

### 3. RequestOrchestrator

**Назначение:** Центральный оркестратор для обработки всех запросов пользователей

**Функционал:**
- Определение типа запроса через RequestRouter
- Маршрутизация на соответствующий обработчик:
  - `SIMPLE_QUESTION` → прямой LLM ответ
  - `INFORMATION_QUERY` → поиск в памяти/интернете
  - `CODE_GENERATION` → PlanningService + ExecutionService
  - `COMPLEX_TASK` → PlanningService + ExecutionService + ReflectionService + MetaLearningService
  - `PLANNING_ONLY` → только планирование
- Обработка ошибок с автоматическим fallback
- Интеграция с WorkflowEngine для отслеживания

**Использование:**
```python
from app.core.request_orchestrator import RequestOrchestrator

orchestrator = RequestOrchestrator()
result = await orchestrator.process_request(
    message="Создай функцию для вычисления факториала",
    context=context
)
```

### 4. WorkflowEngine

**Назначение:** Управление состояниями workflow

**Состояния:**
- `INITIALIZED` - инициализация
- `PARSING` - парсинг запроса
- `PLANNING` - планирование
- `APPROVAL_PENDING` - ожидание одобрения
- `APPROVED` - одобрено
- `EXECUTING` - выполнение
- `PAUSED` - приостановлено
- `COMPLETED` - завершено
- `FAILED` - ошибка
- `CANCELLED` - отменено
- `RETRYING` - повторная попытка

**Использование:**
```python
from app.core.workflow_engine import WorkflowEngine, WorkflowState

workflow_engine = WorkflowEngine.from_context(context)
workflow_engine.initialize(user_request="...", username="user")
workflow_engine.transition_to(WorkflowState.PLANNING, "Начало планирования")
```

### 5. AdaptiveApprovalService

**Назначение:** Интеллектуальное принятие решений об одобрении

**Критерии:**
- Уровень риска задачи
- Trust score агента
- Сложность плана

**Использование:**
```python
from app.services.adaptive_approval_service import AdaptiveApprovalService

approval_service = AdaptiveApprovalService(context)
decision = approval_service.should_auto_approve(plan, agent, risk_level)
```

## Интегрированные сервисы

### MemoryService
- **Интеграция:** `_handle_information_query()`, `_handle_code_generation()`
- **Функции:** Поиск в памяти, сохранение результатов выполнения

### ReflectionService
- **Интеграция:** `_handle_complex_task()`
- **Функции:** Анализ ошибок, генерация исправлений

### MetaLearningService
- **Интеграция:** `_handle_complex_task()`
- **Функции:** Анализ паттернов выполнения, улучшение стратегий

## Workflow обработки запроса

1. **Создание ExecutionContext** - из request или db session
2. **Инициализация WorkflowEngine** - создание workflow
3. **Определение типа запроса** - через RequestRouter
4. **Маршрутизация** - выбор соответствующего обработчика
5. **Обработка** - выполнение через соответствующие сервисы
6. **Управление состояниями** - через WorkflowEngine
7. **Одобрение** - через AdaptiveApprovalService (если нужно)
8. **Результат** - возврат OrchestrationResult

## Диаграмма потока данных

```
User Request
    ↓
RequestOrchestrator
    ↓
RequestRouter (определение типа)
    ↓
┌─────────────────────────────────────┐
│  Обработчики запросов:              │
│  - _handle_simple_question()        │
│  - _handle_information_query()      │
│  - _handle_code_generation()        │
│  - _handle_complex_task()           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Сервисы:                           │
│  - PlanningService                  │
│  - ExecutionService                 │
│  - MemoryService                    │
│  - ReflectionService                 │
│  - MetaLearningService               │
└─────────────────────────────────────┘
    ↓
WorkflowEngine (управление состояниями)
    ↓
OrchestrationResult
```

## Обработка ошибок

Многоуровневый fallback:
1. Попытка replanning (для сложных задач)
2. Fallback к простому вопросу
3. Возврат ошибки с деталями

## Тестирование

Все компоненты покрыты тестами:
- Unit тесты для каждого компонента
- Интеграционные тесты для взаимодействия компонентов
- E2E тесты для полных workflow

## Расширение архитектуры

Для добавления нового сервиса:

1. Создать сервис с поддержкой `ExecutionContext`:
```python
class NewService:
    def __init__(self, db_or_context: Union[Session, ExecutionContext]):
        if isinstance(db_or_context, ExecutionContext):
            self.context = db_or_context
            self.db = db_or_context.db
        else:
            self.db = db_or_context
```

2. Интегрировать в RequestOrchestrator:
```python
async def _handle_new_type(self, message, context, metadata):
    new_service = NewService(context)
    # Использование сервиса
```

3. Добавить тесты:
- Unit тесты для сервиса
- Интеграционные тесты в RequestOrchestrator
- E2E тесты для полных workflow
