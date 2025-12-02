# План системы ранжирования запросов

## Цель

Создать систему для хранения всех запросов (успешных и неуспешных) и их последствий с возможностью ранжирования для анализа и оптимизации.

## Требования

1. **Хранение всех запросов:**
   - Успешные запросы
   - Неуспешные запросы
   - Метаданные запросов (время, модель, тип задачи, результат)

2. **Отслеживание последствий:**
   - Какие артефакты были созданы/изменены
   - Какие планы были выполнены
   - Какие утверждения были созданы
   - Влияние на систему

3. **Ранжирование:**
   - По успешности
   - По важности
   - По влиянию на систему
   - По частоте использования паттернов

## Архитектура

### 1. Таблица `request_logs`

```sql
CREATE TABLE request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Запрос
    request_type VARCHAR(50) NOT NULL,  -- chat, plan_generation, artifact_generation, etc.
    request_data JSONB NOT NULL,  -- Полные данные запроса
    model_used VARCHAR(255),  -- Модель, которая использовалась
    server_url VARCHAR(255),  -- Сервер Ollama
    
    -- Результат
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failed', 'timeout', 'cancelled')),
    response_data JSONB,  -- Данные ответа
    error_message TEXT,  -- Сообщение об ошибке (если есть)
    duration_ms INTEGER,  -- Время выполнения в миллисекундах
    
    -- Последствия
    created_artifacts UUID[],  -- ID созданных артефактов
    created_plans UUID[],  -- ID созданных планов
    created_approvals UUID[],  -- ID созданных утверждений
    modified_artifacts UUID[],  -- ID измененных артефактов
    
    -- Ранжирование
    success_score FLOAT DEFAULT 0.5,  -- Оценка успешности (0.0-1.0)
    importance_score FLOAT DEFAULT 0.5,  -- Оценка важности (0.0-1.0)
    impact_score FLOAT DEFAULT 0.5,  -- Оценка влияния на систему (0.0-1.0)
    overall_rank FLOAT DEFAULT 0.5,  -- Общий ранг (вычисляется)
    
    -- Метаданные
    user_id VARCHAR(255),  -- Пользователь (если есть)
    session_id VARCHAR(255),  -- ID сессии
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_request_logs_status ON request_logs(status);
CREATE INDEX idx_request_logs_type ON request_logs(request_type);
CREATE INDEX idx_request_logs_rank ON request_logs(overall_rank DESC);
CREATE INDEX idx_request_logs_created_at ON request_logs(created_at DESC);
CREATE INDEX idx_request_logs_model ON request_logs(model_used);
```

### 2. Таблица `request_consequences`

```sql
CREATE TABLE request_consequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES request_logs(id) ON DELETE CASCADE,
    
    -- Тип последствия
    consequence_type VARCHAR(50) NOT NULL,  -- artifact_created, plan_created, approval_created, etc.
    entity_type VARCHAR(50) NOT NULL,  -- artifact, plan, approval, etc.
    entity_id UUID NOT NULL,  -- ID сущности
    
    -- Влияние
    impact_type VARCHAR(50),  -- positive, negative, neutral
    impact_description TEXT,
    impact_score FLOAT DEFAULT 0.0,  -- Оценка влияния (-1.0 до 1.0)
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_consequences_request ON request_consequences(request_id);
CREATE INDEX idx_consequences_entity ON request_consequences(entity_type, entity_id);
```

### 3. Алгоритм ранжирования

```python
def calculate_rank(request_log):
    """
    Вычисляет общий ранг запроса на основе:
    - Успешности (success_score)
    - Важности (importance_score)
    - Влияния на систему (impact_score)
    - Времени (более свежие запросы имеют больший вес)
    """
    
    # Базовые веса
    success_weight = 0.3
    importance_weight = 0.3
    impact_weight = 0.3
    recency_weight = 0.1
    
    # Вычисление релевантности по времени (0.0-1.0)
    days_old = (datetime.now() - request_log.created_at).days
    recency_score = max(0.0, 1.0 - (days_old / 365.0))  # За год полностью теряет актуальность
    
    # Общий ранг
    overall_rank = (
        request_log.success_score * success_weight +
        request_log.importance_score * importance_weight +
        request_log.impact_score * impact_weight +
        recency_score * recency_weight
    )
    
    return overall_rank
```

### 4. Вычисление оценок

**success_score:**
- Успешный запрос: 1.0
- Неуспешный запрос: 0.0
- Частично успешный: 0.5-0.9 (на основе качества результата)

**importance_score:**
- Создание артефакта: 0.8
- Создание плана: 0.7
- Обычный чат: 0.3
- Запрос на утверждение: 0.6

**impact_score:**
- Количество созданных артефактов: +0.1 за каждый
- Количество созданных планов: +0.1 за каждый
- Количество утверждений: +0.05 за каждое
- Изменение существующих артефактов: +0.15 за каждый

## Интеграция

### 1. Логирование запросов

Интегрировать в:
- `chat.py` - логирование чат-запросов
- `planning_service.py` - логирование создания планов
- `artifact_generator.py` - логирование создания артефактов
- `execution_service.py` - логирование выполнения планов

### 2. Отслеживание последствий

После каждого запроса:
1. Определить созданные/измененные сущности
2. Создать записи в `request_consequences`
3. Вычислить `impact_score`
4. Обновить `overall_rank`

### 3. API для анализа

- `GET /api/requests/` - список запросов с фильтрами
- `GET /api/requests/{id}` - детали запроса
- `GET /api/requests/ranked` - топ запросов по рангу
- `GET /api/requests/statistics` - статистика по запросам
- `GET /api/requests/{id}/consequences` - последствия запроса

## Следующие шаги

1. ⏳ Создать миграцию для таблиц `request_logs` и `request_consequences`
2. ⏳ Создать модели SQLAlchemy
3. ⏳ Реализовать сервис для логирования запросов
4. ⏳ Интегрировать логирование в существующие endpoints
5. ⏳ Реализовать алгоритм ранжирования
6. ⏳ Создать API для анализа запросов
7. ⏳ Создать UI для просмотра и анализа запросов

