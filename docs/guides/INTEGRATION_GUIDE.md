# Руководство по интеграции компонентов AARD

## Введение

Это руководство поможет разработчикам интегрировать новые компоненты в систему AARD и работать с существующими сервисами.

## Быстрый старт

### 1. Создание сервиса с поддержкой ExecutionContext

```python
from typing import Union
from sqlalchemy.orm import Session
from app.core.execution_context import ExecutionContext
from app.core.database import SessionLocal

class MyService:
    def __init__(self, db_or_context: Union[Session, ExecutionContext] = None):
        """
        Инициализация сервиса
        
        Args:
            db_or_context: Либо Session (для обратной совместимости),
                          либо ExecutionContext (рекомендуется)
        """
        if isinstance(db_or_context, ExecutionContext):
            self.context = db_or_context
            self.db = db_or_context.db
            self.workflow_id = db_or_context.workflow_id
        elif db_or_context is not None:
            # Обратная совместимость: создаем минимальный контекст
            self.db = db_or_context
            self.context = ExecutionContext.from_db_session(db_or_context)
            self.workflow_id = self.context.workflow_id
        else:
            # Создаем новую сессию, если ничего не передано
            self.db = SessionLocal()
            self.context = ExecutionContext.from_db_session(self.db)
            self.workflow_id = self.context.workflow_id
    
    async def do_something(self, data: str):
        """Пример метода сервиса"""
        # Используем self.db для работы с БД
        # Используем self.workflow_id для логирования
        pass
```

### 2. Использование сервиса в RequestOrchestrator

```python
from app.core.request_orchestrator import RequestOrchestrator

class RequestOrchestrator:
    async def _handle_my_request_type(
        self,
        message: str,
        context: ExecutionContext,
        metadata: Dict[str, Any]
    ) -> OrchestrationResult:
        """Обработчик нового типа запроса"""
        
        # Создаем сервис с контекстом
        my_service = MyService(context)
        
        # Используем сервис
        result = await my_service.do_something(message)
        
        # Возвращаем результат
        return OrchestrationResult(
            response=result,
            metadata={"service": "MyService"}
        )
```

### 3. Использование через ServiceRegistry

```python
from app.core.service_registry import get_service_registry
from app.services.my_service import MyService

registry = get_service_registry()
my_service = registry.get_service(MyService, context)
```

## Работа с ExecutionContext

### Создание контекста

```python
from app.core.execution_context import ExecutionContext

# Из db session
context = ExecutionContext.from_db_session(db)

# Из FastAPI request
from fastapi import Request
context = ExecutionContext.from_request(db, request, session_id="...")

# Вручную
context = ExecutionContext(
    db=db,
    workflow_id=str(uuid4()),
    trace_id=None,
    session_id="session_123",
    user_id="user_456",
    metadata={"key": "value"}
)
```

### Доступ к компонентам контекста

```python
# База данных
db = context.db

# Workflow ID для логирования
workflow_id = context.workflow_id

# Метаданные
metadata = context.metadata
context.metadata["new_key"] = "new_value"

# PromptManager (если доступен)
if context.prompt_manager:
    prompt = await context.prompt_manager.get_prompt_for_stage("planning")

# WorkflowEngine (если доступен)
if context.workflow_engine:
    context.workflow_engine.transition_to(WorkflowState.EXECUTING, "Начало выполнения")
```

## Работа с WorkflowEngine

### Инициализация

```python
from app.core.workflow_engine import WorkflowEngine, WorkflowState

workflow_engine = WorkflowEngine.from_context(context)
workflow_engine.initialize(
    user_request="Создай функцию",
    username="user",
    interaction_type="code_generation"
)
```

### Переходы между состояниями

```python
# Переход к планированию
workflow_engine.transition_to(
    WorkflowState.PLANNING,
    "Начало планирования",
    metadata={"task": "..."}
)

# Пауза
workflow_engine.pause("Приостановлено пользователем")

# Возобновление
workflow_engine.resume("Возобновлено")

# Завершение
workflow_engine.mark_completed("Задача выполнена")

# Ошибка
workflow_engine.mark_failed("Ошибка выполнения", error="...")
```

### Получение информации о состоянии

```python
state_info = workflow_engine.get_state_info()
print(f"Текущее состояние: {state_info.current_state}")
print(f"История переходов: {state_info.transitions}")
```

## Интеграция с MemoryService

### Поиск в памяти

```python
from app.services.memory_service import MemoryService

memory_service = MemoryService(context)
memories = await memory_service.search_memories_vector(
    agent_id=agent_id,
    query="Python programming",
    limit=5
)
```

### Сохранение в память

```python
memory_service.save_memory(
    agent_id=agent_id,
    memory_type="execution",
    content={"task": "...", "result": "..."},
    summary="Выполнена задача",
    importance=0.8,
    tags=["execution", "success"]
)
```

## Интеграция с ReflectionService

### Анализ ошибки

```python
from app.services.reflection_service import ReflectionService

reflection_service = ReflectionService(context)
analysis = await reflection_service.analyze_failure(
    task_description="...",
    error="...",
    context={...}
)
```

### Генерация исправления

```python
fix = await reflection_service.generate_fix(
    task_description="...",
    error="...",
    analysis=analysis
)
```

## Интеграция с MetaLearningService

### Анализ паттернов

```python
from app.services.meta_learning_service import MetaLearningService

meta_learning_service = MetaLearningService(context)
patterns = meta_learning_service.analyze_execution_patterns(
    agent_id=agent_id,
    time_range_days=30
)
```

## Обработка ошибок

### Try-except с логированием

```python
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

try:
    result = await my_service.do_something()
except Exception as e:
    logger.error(f"Ошибка в MyService: {e}", extra={
        "workflow_id": context.workflow_id,
        "error": str(e)
    }, exc_info=True)
    # Не прерываем выполнение, возвращаем fallback
    return fallback_result
```

### Использование WorkflowEngine для ошибок

```python
try:
    result = await my_service.do_something()
except Exception as e:
    workflow_engine = getattr(context, 'workflow_engine', None)
    if workflow_engine:
        workflow_engine.mark_failed("Ошибка выполнения", error=str(e))
    raise
```

## Тестирование

### Создание тестового контекста

```python
import pytest
from app.core.execution_context import ExecutionContext
from app.core.database import SessionLocal

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def execution_context(db_session):
    return ExecutionContext(
        db=db_session,
        workflow_id=str(uuid4()),
        trace_id=None,
        session_id=None,
        user_id="test_user",
        metadata={}
    )
```

### Тест сервиса

```python
@pytest.mark.asyncio
async def test_my_service(execution_context):
    service = MyService(execution_context)
    result = await service.do_something("test")
    assert result is not None
```

## Лучшие практики

1. **Всегда используйте ExecutionContext** вместо прямого использования Session
2. **Логируйте с workflow_id** для отслеживания
3. **Обрабатывайте ошибки gracefully** - не прерывайте весь workflow
4. **Используйте WorkflowEngine** для управления состояниями
5. **Тестируйте с реальными данными** когда возможно
6. **Документируйте интеграции** в коде и документации

## Частые проблемы и решения

### Проблема: Сервис не получает ExecutionContext

**Решение:** Убедитесь, что передаете `context` при создании сервиса:
```python
service = MyService(context)  # ✅ Правильно
service = MyService(context.db)  # ⚠️ Работает, но теряется workflow_id
```

### Проблема: WorkflowEngine не доступен

**Решение:** Проверяйте наличие перед использованием:
```python
workflow_engine = getattr(context, 'workflow_engine', None)
if workflow_engine:
    workflow_engine.transition_to(...)
```

### Проблема: Ошибки транзакций БД

**Решение:** Используйте try-except с rollback:
```python
try:
    # Работа с БД
    db.commit()
except Exception:
    db.rollback()
    raise
```
