# Task Queue Manager - Завершено

## Реализованные компоненты

### 1. Модели данных
- ✅ `TaskQueue` - модель для управления очередями
- ✅ `QueueTask` - модель для задач в очередях
- ✅ Миграция `007_add_task_queues.py` применена

### 2. Сервис управления очередями
- ✅ `TaskQueueManager` - основной сервис:
  - Создание и управление очередями
  - Добавление задач в очереди
  - Получение следующей задачи для worker'а
  - Завершение/провал задач
  - Retry механизм с exponential backoff
  - Dead Letter Queue для неудачных задач
  - Статистика по очередям

### 3. API для управления очередями
- ✅ `POST /api/queues/` - создание очереди
- ✅ `GET /api/queues/` - список очередей
- ✅ `GET /api/queues/{queue_id}` - детали очереди
- ✅ `POST /api/queues/{queue_id}/tasks` - добавление задачи
- ✅ `GET /api/queues/{queue_id}/tasks` - список задач в очереди
- ✅ `POST /api/queues/{queue_id}/tasks/next` - получение следующей задачи
- ✅ `POST /api/queues/tasks/{task_id}/complete` - завершение задачи
- ✅ `POST /api/queues/tasks/{task_id}/fail` - провал задачи
- ✅ `GET /api/queues/{queue_id}/stats` - статистика очереди
- ✅ `GET /api/queues/failed-tasks` - Dead Letter Queue

## Алгоритм retry

### Exponential Backoff:
```python
delay = base_delay * (2 ** (retry_count - 1))
max_delay = 3600  # 1 hour
```

### Логика retry:
1. При провале задачи увеличивается `retry_count`
2. Если `retry_count <= max_retries`:
   - Задача переходит в статус `queued`
   - Устанавливается `next_retry_at` с задержкой
3. Если `retry_count > max_retries`:
   - Задача переходит в статус `failed` (Dead Letter Queue)

## Приоритизация

Задачи выбираются по:
1. Приоритету (9 - наивысший)
2. Времени создания (старые задачи первыми)

## Ограничение параллельности

Каждая очередь имеет `max_concurrent` - максимальное количество одновременно обрабатываемых задач. Система автоматически проверяет это ограничение перед назначением задачи worker'у.

## Использование

### Создание очереди:
```python
from app.services.task_queue_manager import TaskQueueManager

manager = TaskQueueManager(db)
queue = manager.create_queue(
    name="plan_execution",
    description="Queue for plan execution",
    max_concurrent=3,
    priority=8
)
```

### Добавление задачи:
```python
task = manager.add_task(
    queue_id=queue.id,
    task_type="plan_execution",
    task_data={"plan_id": str(plan.id)},
    priority=7,
    max_retries=3
)
```

### Получение следующей задачи:
```python
task = manager.get_next_task(
    queue_id=queue.id,
    worker_id="worker_1"
)
```

### Завершение задачи:
```python
manager.complete_task(
    task_id=task.id,
    result_data={"status": "success", "output": "..."}
)
```

### Провал задачи:
```python
manager.fail_task(
    task_id=task.id,
    error_message="Error message",
    retry=True
)
```

## Следующие шаги

1. Интегрировать с `execution_service.py` - использовать очереди для выполнения планов
2. Интегрировать с `planning_service.py` - автоматически добавлять планы в очередь
3. Создать worker pool для обработки задач из очередей
4. Добавить веб-интерфейс для мониторинга очередей
5. Добавить автоматическое восстановление зависших задач

