# Реализация концепции Digital Twin для задач

## Обзор

Реализована концепция "Цифрового Двойника Задачи" (Digital Twin of the Task), которая обеспечивает единую точку истины для хранения всего контекста задачи.

## Проблема, которую решает

**Было:** Контекст задачи разбросан по разным местам:
- Исходный запрос пользователя - в `tasks.description`
- Планы - в таблице `plans`
- Артефакты - в таблице `artifacts`
- Логи выполнения - в разных таблицах
- История взаимодействий - в разных местах

**Стало:** Весь контекст хранится в одном месте - поле `context` (JSONB) в таблице `tasks`.

## Реализация

### 1. Миграция базы данных

Создана миграция `018_add_task_digital_twin.py`, которая:
- Добавляет поле `context` типа JSONB в таблицу `tasks`
- Создает GIN индекс для эффективных запросов по JSONB полю

**Применение миграции:**
```bash
cd backend
alembic upgrade head
```

### 2. Обновление модели Task

Добавлены методы для работы с контекстом:

- `get_context()` - получить контекст задачи (инициализирует пустой словарь, если отсутствует)
- `update_context(updates, merge=True)` - обновить контекст задачи
- `add_to_history(history_type, data)` - добавить запись в историю взаимодействий

### 3. Структура Digital Twin контекста

```json
{
  "original_user_request": "Описание исходного запроса пользователя",
  "active_todos": [
    {
      "step_id": "step_1",
      "description": "Описание шага",
      "status": "pending",
      "completed": false
    }
  ],
  "historical_todos": [
    // История всех ToDo списков (версии планов)
  ],
  "plan": {
    "plan_id": "uuid",
    "version": 1,
    "goal": "Цель плана",
    "strategy": {},
    "steps_count": 5,
    "status": "draft",
    "created_at": "2025-12-03T20:00:00"
  },
  "artifacts": [
    {
      "artifact_id": "uuid",
      "type": "agent|tool",
      "name": "Название",
      "version": 1,
      "created_at": "2025-12-03T20:00:00"
    }
  ],
  "execution_logs": [
    {
      "timestamp": "2025-12-03T20:00:00",
      "level": "info|error|warning",
      "message": "Сообщение",
      "data": {}
    }
  ],
  "interaction_history": [
    {
      "type": "approval|correction|feedback",
      "timestamp": "2025-12-03T20:00:00",
      "data": {}
    }
  ],
  "metadata": {
    "created_at": "2025-12-03T20:00:00",
    "task_id": "uuid",
    "plan_id": "uuid",
    "model_used": "gemma3:4b",
    "server_used": "Server 2 - Coding"
  }
}
```

### 4. Интеграция в PlanningService

При создании плана автоматически заполняется Digital Twin контекст:
- Исходный запрос пользователя
- Активный ToDo список (из шагов плана)
- Информация о плане
- Метаданные (timestamp, task_id, plan_id)

### 5. Преимущества

1. **Единая точка истины** - весь контекст задачи в одном месте
2. **Полная наблюдаемость** - можно восстановить состояние задачи на любом этапе
3. **Воспроизводимость** - можно воссоздать состояние системы на любой момент
4. **Эффективные запросы** - GIN индекс позволяет быстро искать по JSONB полю
5. **Гибкость** - структура может расширяться без изменения схемы БД

## Использование

### Получение контекста

```python
task = db.query(Task).filter(Task.id == task_id).first()
context = task.get_context()

# Доступ к конкретным полям
original_request = context.get("original_user_request")
active_todos = context.get("active_todos", [])
```

### Обновление контекста

```python
# Обновить контекст (merge=True - объединить с существующим)
task.update_context({
    "plan": {
        "plan_id": str(plan.id),
        "version": plan.version
    }
}, merge=True)

# Полностью заменить контекст
task.update_context(new_context, merge=False)
```

### Добавление в историю

```python
# Добавить запись в историю взаимодействий
task.add_to_history("approval", {
    "approved_by": "user@example.com",
    "plan_id": str(plan.id),
    "comment": "План утвержден"
})
```

### Запросы по контексту

```python
# Поиск задач с определенным артефактом
tasks = db.query(Task).filter(
    Task.context['artifacts'].astext.contains('artifact_id')
).all()

# Поиск задач с определенным статусом в active_todos
tasks = db.query(Task).filter(
    Task.context['active_todos'][0]['status'].astext == 'completed'
).all()
```

## Следующие шаги

1. ✅ Добавление поля context в таблицу tasks
2. ✅ Обновление модели Task для работы с контекстом
3. ✅ Интеграция в PlanningService
4. ⏳ Интеграция в другие сервисы (ExecutionService, ArtifactService)
5. ⏳ Использование контекста в промптах для моделей
6. ⏳ UI для просмотра Digital Twin контекста

## Связанные документы

- [PLANNING_LOGIC_ANALYSIS.md](PLANNING_LOGIC_ANALYSIS.md) - Анализ логики планирования
- Миграция: `backend/alembic/versions/018_add_task_digital_twin.py`
- Модель: `backend/app/models/task.py`
- Сервис: `backend/app/services/planning_service.py`

