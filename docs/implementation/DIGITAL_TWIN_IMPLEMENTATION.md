# Реализация системы цифрового двойника задачи

## ✅ Выполнено

### 1. Модель Task с полем context (JSONB)
**Файл:** `backend/app/models/task.py`

**Функциональность:**
- Поле `context` (JSONB) для хранения всех данных задачи
- Методы `get_context()`, `update_context()`, `add_to_history()`
- Уже интегрировано в модель

**Структура context:**
```json
{
  "original_user_request": "Original user request/query",
  "active_todos": ["Current ToDo list from plan steps"],
  "historical_todos": ["Historical ToDo lists (plan versions)"],
  "artifacts": ["Generated artifacts (prompts, code, tables, etc.)"],
  "execution_logs": ["Execution logs, errors, validation results"],
  "interaction_history": ["History of human interactions"],
  "planning_decisions": {
    "replanning_history": [],
    "plan_versions": []
  },
  "metadata": {
    "created_at": "ISO timestamp",
    "last_updated": "ISO timestamp"
  }
}
```

### 2. Сервис TaskDigitalTwinService
**Файл:** `backend/app/services/task_digital_twin_service.py`

**Методы:**

#### Инициализация и обновление
- `initialize_context()` - Инициализация контекста с дефолтной структурой
- `add_user_request()` - Добавление оригинального запроса пользователя
- `update_active_todos()` - Обновление активного ToDo списка
- `update_metadata()` - Обновление метаданных

#### Добавление данных
- `add_artifact()` - Добавление сгенерированного артефакта
- `add_execution_log()` - Добавление лога выполнения
- `add_interaction()` - Добавление взаимодействия с человеком
- `add_planning_decision()` - Добавление решения планирования

#### Получение данных
- `get_full_context()` - Получение полного контекста
- `get_active_todos()` - Получение активного ToDo списка
- `get_artifacts()` - Получение артефактов (с фильтром по типу)
- `get_execution_logs()` - Получение логов выполнения (с фильтром по step_id)
- `get_interaction_history()` - Получение истории взаимодействий (с фильтром по типу)
- `get_planning_decisions()` - Получение решений планирования

### 3. Интеграция в PlanningService
**Файл:** `backend/app/services/planning_service.py`

**Использование:**
- Уже используется `task.get_context()` и `task.update_context()`
- Обновление Digital Twin при перепланировании
- Сохранение истории перепланирования в контексте

## Использование

### Инициализация контекста при создании задачи

```python
from app.services.task_digital_twin_service import TaskDigitalTwinService

twin_service = TaskDigitalTwinService(db)

# При создании задачи
twin_service.initialize_context(
    task=task,
    user_request="Найти все модели айфонов с 2020 года"
)
```

### Обновление ToDo списка

```python
# При создании плана
todos = [
    {"step_id": "step_1", "description": "Search for iPhone models", "status": "pending"},
    {"step_id": "step_2", "description": "Filter by year >= 2020", "status": "pending"}
]

twin_service.update_active_todos(task, todos)
```

### Добавление артефакта

```python
# При создании инструмента/агента
twin_service.add_artifact(
    task=task,
    artifact={
        "id": str(artifact_id),
        "type": "tool",
        "name": "iPhoneSearchTool",
        "description": "Tool for searching iPhone models",
        "content": "def search_iphones(year): ..."
    }
)
```

### Добавление лога выполнения

```python
# После выполнения шага
twin_service.add_execution_log(
    task=task,
    log_entry={
        "step_id": "step_1",
        "status": "completed",
        "output": "Found 15 iPhone models",
        "execution_time": 1.2
    }
)
```

### Добавление взаимодействия

```python
# При одобрении/отклонении
twin_service.add_interaction(
    task=task,
    interaction_type="approval",
    data={
        "approved": True,
        "approved_by": "user@example.com",
        "comment": "Looks good"
    }
)
```

## Преимущества

1. **Единый источник данных** - Все данные задачи в одном месте
2. **История изменений** - Полная история всех взаимодействий
3. **Быстрый доступ** - JSONB индексы для быстрого поиска
4. **Гибкость** - Легко добавлять новые типы данных
5. **Аудит** - Полная история для анализа и отладки

## Следующие шаги

1. ⏳ Интеграция TaskDigitalTwinService в PlanningService для автоматического обновления
2. ⏳ Интеграция в ExecutionService для логирования выполнения
3. ⏳ Интеграция в ArtifactGenerator для сохранения артефактов
4. ⏳ API endpoints для доступа к Digital Twin
5. ⏳ Визуализация Digital Twin в UI

