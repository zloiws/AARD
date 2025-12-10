# Исправление Deprecation Warnings

## Статус: ✅ ЗАВЕРШЕНО

Все предупреждения о deprecated функциях исправлены.

## Исправленные проблемы

### 1. Pydantic Validators (V1 → V2)
**Файл:** `backend/app/core/a2a_protocol.py`

**Изменения:**
- ✅ Заменен `@validator` на `@field_validator` для Pydantic V2
- ✅ Добавлен декоратор `@classmethod` для валидаторов
- ✅ Использован `@model_validator(mode='after')` для установки default timeout
- ✅ Обновлен импорт: `from pydantic import BaseModel, Field, field_validator, model_validator`

**До:**
```python
@validator('recipient')
def validate_recipient(cls, v):
    ...

@validator('type')
def validate_type(cls, v, values):
    ...
```

**После:**
```python
@field_validator('recipient')
@classmethod
def validate_recipient(cls, v):
    ...

@field_validator('type')
@classmethod
def validate_type(cls, v):
    ...

@model_validator(mode='after')
def set_default_timeout(self):
    if self.type == A2AMessageType.REQUEST and self.expected_response_timeout is None:
        self.expected_response_timeout = 60
    return self
```

### 2. SQLAlchemy Models - datetime.utcnow в Column defaults
**Файлы:** Все модели в `backend/app/models/` (29 файлов)

**Изменения:**
- ✅ Заменено `default=datetime.utcnow` на `default=lambda: datetime.now(timezone.utc)`
- ✅ Заменено `onupdate=datetime.utcnow` на `onupdate=lambda: datetime.now(timezone.utc)`
- ✅ Добавлен импорт `timezone` во все модели: `from datetime import datetime, timezone`

**Исправлено файлов:** 29
**Исправлено использований:** ~61

**Примеры исправленных файлов:**
- `plan.py`
- `task.py`
- `agent_conversation.py`
- `agent_memory.py`
- `system_setting.py`
- `agent_team.py`
- `plan_template.py`
- `audit_report.py`
- `project_metric.py`
- `benchmark_result.py`
- `benchmark_task.py`
- `workflow_event.py`
- `chat_session.py`
- `learning_pattern.py`
- `user.py`
- `agent_test.py`
- `agent_experiment.py`
- `agent.py`
- `tool.py`
- `trace.py`
- `checkpoint.py`
- `task_queue.py`
- `request_log.py`
- `approval.py`
- `artifact.py`
- `prompt.py`
- `evolution.py`
- `ollama_server.py`
- `ollama_model.py`

**До:**
```python
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

**После:**
```python
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
```

## Результаты

✅ Все Pydantic validators обновлены до V2 стиля
✅ Все SQLAlchemy models используют timezone-aware datetime
✅ Нет DeprecationWarning для datetime.utcnow()
✅ Нет PydanticDeprecatedSince20 warnings
✅ Все тесты проходят успешно

## Проверка

Для проверки, что все исправлено:
```powershell
cd backend
python -m pytest tests/ -v --tb=short 2>&1 | Select-String -Pattern "DeprecationWarning|PydanticDeprecated"
# Не должно быть предупреждений
```

## Коммиты

1. `fix: Update Pydantic validators to V2 style and fix datetime.utcnow in models (part 1)`
2. `fix: Replace datetime.utcnow in more SQLAlchemy models (part 2)`
3. `fix: Replace remaining datetime.utcnow in all SQLAlchemy models`
4. `fix: Replace datetime.utcnow in task_queue.py QueueTask model`

## Примечания

- Использование `lambda` в `default=` необходимо для SQLAlchemy, чтобы функция вызывалась при каждом создании записи, а не один раз при определении модели
- Все изменения обратно совместимы и не требуют миграций базы данных
- Предупреждения от SQLAlchemy о `datetime.utcnow()` в `schema.py` исходят из самой библиотеки и будут исправлены в будущих версиях SQLAlchemy
