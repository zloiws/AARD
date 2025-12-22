# Руководство по миграции на новую архитектуру интеграции

## Введение

Это руководство поможет мигрировать существующий код на новую архитектуру интеграции с ExecutionContext, ServiceRegistry и RequestOrchestrator.

## Миграция сервисов

### Шаг 1: Обновление конструктора сервиса

**Было:**
```python
class MyService:
    def __init__(self, db: Session):
        self.db = db
```

**Стало:**
```python
from typing import Union
from sqlalchemy.orm import Session
from app.core.execution_context import ExecutionContext
from app.core.database import SessionLocal

class MyService:
    def __init__(self, db_or_context: Union[Session, ExecutionContext] = None):
        if isinstance(db_or_context, ExecutionContext):
            self.context = db_or_context
            self.db = db_or_context.db
            self.workflow_id = db_or_context.workflow_id
        elif db_or_context is not None:
            # Обратная совместимость
            self.db = db_or_context
            self.context = ExecutionContext.from_db_session(db_or_context)
            self.workflow_id = self.context.workflow_id
        else:
            self.db = SessionLocal()
            self.context = ExecutionContext.from_db_session(self.db)
            self.workflow_id = self.context.workflow_id
```

### Шаг 2: Обновление вызовов сервиса

**Было:**
```python
service = MyService(db_session)
```

**Стало:**
```python
# Вариант 1: С ExecutionContext (рекомендуется)
service = MyService(context)

# Вариант 2: С Session (обратная совместимость)
service = MyService(db_session)  # Все еще работает
```

### Шаг 3: Использование workflow_id для логирования

**Было:**
```python
logger.info("Processing data")
```

**Стало:**
```python
logger.info("Processing data", extra={
    "workflow_id": self.workflow_id
})
```

## Миграция обработчиков запросов

### Шаг 1: Обновление сигнатуры метода

**Было:**
```python
async def handle_request(self, message: str, db: Session, user_id: str):
    # ...
```

**Стало:**
```python
from app.core.execution_context import ExecutionContext
from typing import Dict, Any

async def handle_request(
    self,
    message: str,
    context: ExecutionContext,
    metadata: Dict[str, Any]
):
    # Используем context.db вместо db
    # Используем context.user_id вместо user_id
    # ...
```

### Шаг 2: Использование ExecutionContext

**Было:**
```python
async def handle_request(self, message: str, db: Session, user_id: str):
    service = MyService(db)
    result = await service.process(message)
    # ...
```

**Стало:**
```python
async def handle_request(
    self,
    message: str,
    context: ExecutionContext,
    metadata: Dict[str, Any]
):
    service = MyService(context)
    result = await service.process(message)
    # ...
```

## Миграция тестов

### Шаг 1: Создание фикстуры ExecutionContext

**Было:**
```python
@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_my_service(db_session):
    service = MyService(db_session)
    # ...
```

**Стало:**
```python
from app.core.execution_context import ExecutionContext
from uuid import uuid4

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
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

def test_my_service(execution_context):
    service = MyService(execution_context)
    # ...
```

### Шаг 2: Обновление вызовов в тестах

**Было:**
```python
def test_handler(db_session):
    handler = MyHandler()
    result = await handler.handle_request("test", db_session, "user1")
```

**Стало:**
```python
def test_handler(execution_context):
    handler = MyHandler()
    result = await handler.handle_request(
        "test",
        execution_context,
        {}
    )
```

## Миграция API endpoints

### Шаг 1: Обновление FastAPI endpoint

**Было:**
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

@router.post("/endpoint")
async def my_endpoint(
    message: str,
    db: Session = Depends(get_db),
    user_id: str = None
):
    handler = MyHandler()
    result = await handler.handle_request(message, db, user_id)
    return result
```

**Стало:**
```python
from fastapi import Depends, Request
from app.core.execution_context import ExecutionContext
from app.core.database import get_db

@router.post("/endpoint")
async def my_endpoint(
    message: str,
    request: Request,
    db: Session = Depends(get_db)
):
    context = ExecutionContext.from_request(
        db, request, session_id=request.headers.get("X-Session-ID")
    )
    handler = MyHandler()
    result = await handler.handle_request(message, context, {})
    return result
```

## Постепенная миграция

### Стратегия 1: Поддержка обоих вариантов

Можно поддерживать оба варианта во время миграции:

```python
class MyService:
    def __init__(self, db_or_context: Union[Session, ExecutionContext]):
        # Код поддерживает оба варианта
        if isinstance(db_or_context, ExecutionContext):
            self.context = db_or_context
            self.db = db_or_context.db
        else:
            self.db = db_or_context
            self.context = ExecutionContext.from_db_session(db_or_context)
```

### Стратегия 2: Миграция по модулям

1. Начните с одного модуля
2. Мигрируйте все сервисы в модуле
3. Обновите тесты модуля
4. Переходите к следующему модулю

### Стратегия 3: Использование ServiceRegistry

Для новых сервисов используйте ServiceRegistry:

```python
from app.core.service_registry import get_service_registry

registry = get_service_registry()
service = registry.get_service(MyService, context)
```

## Проверка миграции

### Чеклист

- [ ] Все сервисы поддерживают ExecutionContext
- [ ] Все обработчики используют ExecutionContext
- [ ] Все тесты обновлены
- [ ] Все API endpoints обновлены
- [ ] Логирование использует workflow_id
- [ ] Обратная совместимость сохранена (если нужно)

### Тестирование

После миграции запустите все тесты:

```bash
cd backend
python -m pytest tests/ -v
```

## Частые проблемы

### Проблема: AttributeError: 'Session' object has no attribute 'workflow_id'

**Причина:** Передается Session вместо ExecutionContext

**Решение:** Оберните Session в ExecutionContext:
```python
context = ExecutionContext.from_db_session(db_session)
service = MyService(context)
```

### Проблема: Ошибки транзакций БД

**Причина:** Неправильное управление транзакциями

**Решение:** Используйте try-except с rollback:
```python
try:
    # Работа с БД
    self.db.commit()
except Exception:
    self.db.rollback()
    raise
```

### Проблема: WorkflowEngine не доступен

**Причина:** WorkflowEngine не был инициализирован

**Решение:** Проверяйте наличие перед использованием:
```python
workflow_engine = getattr(context, 'workflow_engine', None)
if workflow_engine:
    workflow_engine.transition_to(...)
```

## Примеры миграции

### Пример 1: Простой сервис

**Было:**
```python
class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user(self, user_id: str):
        return self.db.query(User).filter(User.id == user_id).first()
```

**Стало:**
```python
class UserService:
    def __init__(self, db_or_context: Union[Session, ExecutionContext]):
        if isinstance(db_or_context, ExecutionContext):
            self.context = db_or_context
            self.db = db_or_context.db
        else:
            self.db = db_or_context
            self.context = ExecutionContext.from_db_session(db_or_context)
    
    def get_user(self, user_id: str):
        return self.db.query(User).filter(User.id == user_id).first()
```

### Пример 2: Сервис с async методами

**Было:**
```python
class ProcessingService:
    def __init__(self, db: Session):
        self.db = db
    
    async def process(self, data: str):
        # Обработка
        result = await some_async_operation(data)
        # Сохранение
        record = Record(data=result)
        self.db.add(record)
        self.db.commit()
        return result
```

**Стало:**
```python
class ProcessingService:
    def __init__(self, db_or_context: Union[Session, ExecutionContext]):
        if isinstance(db_or_context, ExecutionContext):
            self.context = db_or_context
            self.db = db_or_context.db
            self.workflow_id = db_or_context.workflow_id
        else:
            self.db = db_or_context
            self.context = ExecutionContext.from_db_session(db_or_context)
            self.workflow_id = self.context.workflow_id
    
    async def process(self, data: str):
        from app.core.logging_config import LoggingConfig
        logger = LoggingConfig.get_logger(__name__)
        
        logger.info("Processing data", extra={"workflow_id": self.workflow_id})
        
        try:
            result = await some_async_operation(data)
            record = Record(data=result)
            self.db.add(record)
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            logger.error("Processing failed", extra={
                "workflow_id": self.workflow_id,
                "error": str(e)
            }, exc_info=True)
            raise
```

## Дополнительные ресурсы

- [INTEGRATION_ARCHITECTURE.md](./INTEGRATION_ARCHITECTURE.md) - Детальная архитектура
- [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - Руководство для разработчиков
- [INTEGRATION.md](./INTEGRATION.md) - Общая информация об интеграции
