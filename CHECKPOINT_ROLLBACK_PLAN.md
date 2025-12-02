# План реализации Checkpoint и Rollback

## Цель

Создать систему для сохранения состояний (checkpoints) и восстановления (rollback) для:
- Сохранения состояния перед критичными операциями
- Восстановления состояния при ошибках
- Отката к предыдущим версиям
- Транзакционной целостности

## Архитектура

### 1. Таблица `checkpoints`
```sql
CREATE TABLE checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Связь с сущностями
    entity_type VARCHAR(50) NOT NULL,  -- plan, task, artifact, etc.
    entity_id UUID NOT NULL,
    
    -- Состояние
    state_data JSONB NOT NULL,  -- Полное состояние сущности
    state_hash VARCHAR(64),  -- SHA-256 hash для проверки целостности
    
    -- Метаданные
    reason VARCHAR(255),  -- Причина создания checkpoint
    created_by VARCHAR(255),  -- Пользователь или система
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Связь с запросом/операцией
    request_id UUID REFERENCES request_logs(id),
    trace_id VARCHAR(255),  -- OpenTelemetry trace ID
);

CREATE INDEX idx_checkpoints_entity ON checkpoints(entity_type, entity_id);
CREATE INDEX idx_checkpoints_created ON checkpoints(created_at DESC);
```

## Компоненты

### 1. CheckpointService
- Создание checkpoint'ов
- Восстановление состояния из checkpoint'а
- Rollback к предыдущему checkpoint'у
- Автоматические checkpoint'и для критичных операций

### 2. Интеграция
- Интеграция с выполнением планов (checkpoint перед каждым шагом)
- Интеграция с генерацией артефактов
- Интеграция с изменением промптов

## Алгоритм

### Создание checkpoint:
1. Сериализовать текущее состояние сущности
2. Вычислить hash состояния
3. Сохранить в БД
4. Вернуть checkpoint ID

### Восстановление:
1. Получить checkpoint по ID
2. Проверить hash целостности
3. Восстановить состояние из JSONB
4. Применить к сущности

### Rollback:
1. Найти последний checkpoint для сущности
2. Восстановить состояние
3. Откатить все изменения после checkpoint'а

## Следующие шаги

1. Создать модель данных
2. Создать миграцию
3. Реализовать CheckpointService
4. Интегрировать с выполнением планов
5. Создать API для управления checkpoint'ами

