# План реализации Task Queue Manager

## Цель

Создать систему управления очередями задач для:
- Приоритизации задач
- Распределения задач по worker'ам
- Retry механизм с exponential backoff
- Dead Letter Queue для неудачных задач

## Архитектура

### 1. Таблица `task_queues`
```sql
CREATE TABLE task_queues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    max_concurrent INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 5,  -- 0-9, где 9 - наивысший
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Таблица `queue_tasks`
```sql
CREATE TABLE queue_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_id UUID NOT NULL REFERENCES task_queues(id) ON DELETE CASCADE,
    
    -- Задача
    task_type VARCHAR(50) NOT NULL,  -- plan_execution, artifact_generation, etc.
    task_data JSONB NOT NULL,
    priority INTEGER DEFAULT 5,  -- 0-9
    
    -- Статус
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'queued', 'processing', 'completed', 'failed', 'cancelled')),
    
    -- Retry
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP,
    
    -- Результат
    result_data JSONB,
    error_message TEXT,
    
    -- Метаданные
    assigned_worker VARCHAR(255),  -- Worker ID
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_queue_tasks_status ON queue_tasks(status);
CREATE INDEX idx_queue_tasks_priority ON queue_tasks(priority DESC);
CREATE INDEX idx_queue_tasks_next_retry ON queue_tasks(next_retry_at);
CREATE INDEX idx_queue_tasks_queue ON queue_tasks(queue_id);
```

## Компоненты

### 1. TaskQueueManager
- Добавление задач в очередь
- Приоритизация задач
- Распределение задач по worker'ам
- Retry механизм
- Dead Letter Queue

### 2. Worker Pool
- Управление worker'ами
- Назначение задач worker'ам
- Мониторинг выполнения

### 3. Интеграция
- Интеграция с планированием
- Интеграция с выполнением планов
- Интеграция с генерацией артефактов

## Алгоритм retry

```python
def calculate_next_retry(retry_count, base_delay=10):
    """Exponential backoff"""
    delay = base_delay * (2 ** retry_count)
    max_delay = 3600  # 1 hour
    return min(delay, max_delay)
```

## Следующие шаги

1. Создать модели данных
2. Создать миграцию
3. Реализовать TaskQueueManager
4. Интегрировать с планированием и выполнением
5. Создать API для управления очередями

