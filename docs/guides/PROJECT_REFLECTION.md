# Система саморефлексии проекта

## Обзор

Система саморефлексии проекта (Phase 3) предназначена для автоматического сбора, анализа и визуализации метрик на уровне всего проекта. Она позволяет отслеживать производительность системы, успешность выполнения задач, тренды во времени и генерировать автоматические рекомендации по улучшению.

## Архитектура

Система состоит из трех основных этапов:

1. **Этап 3.1: Система метрик проекта** - сбор и хранение метрик
2. **Этап 3.2: Регулярный самоаудит** - автоматический анализ и рекомендации
3. **Этап 3.3: Dashboard метрик проекта** - визуализация и отчеты

## Этап 3.1: Система метрик проекта

### Модель ProjectMetric

Модель `ProjectMetric` (`backend/app/models/project_metric.py`) хранит агрегированные метрики проекта.

**Поля:**

- `id` (UUID): Уникальный идентификатор метрики
- `metric_type` (Enum `MetricType`): Тип метрики (PERFORMANCE, TASK_SUCCESS, EXECUTION_TIME, TASK_DISTRIBUTION, TREND, AGGREGATE)
- `metric_name` (String): Имя метрики (например, "task_success_rate", "avg_execution_time")
- `period` (Enum `MetricPeriod`): Период агрегации (HOUR, DAY, WEEK, MONTH)
- `period_start` (DateTime): Начало периода
- `period_end` (DateTime): Конец периода
- `value` (Float): Основное значение метрики
- `count` (Integer): Количество образцов
- `min_value` (Float): Минимальное значение в периоде
- `max_value` (Float): Максимальное значение в периоде
- `sum_value` (Float): Сумма значений (для расчета средних)
- `metric_metadata` (JSONB): Дополнительные данные метрики
- `created_at` (DateTime): Время создания
- `updated_at` (DateTime): Время последнего обновления

**Пример использования:**

```python
from app.models.project_metric import ProjectMetric, MetricType, MetricPeriod
from datetime import datetime, timedelta

period_start = datetime.utcnow() - timedelta(hours=1)
period_end = datetime.utcnow()

metric = ProjectMetric(
    metric_type=MetricType.PERFORMANCE,
    metric_name="task_success_rate",
    period=MetricPeriod.HOUR,
    period_start=period_start,
    period_end=period_end,
    value=0.85,
    count=100
)
```

### ProjectMetricsService

Сервис `ProjectMetricsService` (`backend/app/services/project_metrics_service.py`) предоставляет методы для работы с метриками проекта.

**Основные методы:**

- `record_metric()`: Записать метрику в базу данных
- `collect_performance_metrics()`: Собрать метрики производительности за период
- `collect_task_distribution()`: Собрать метрики распределения задач
- `get_overview()`: Получить обзор метрик за период
- `get_trends()`: Получить тренды метрики во времени
- `compare_periods()`: Сравнить метрики между двумя периодами

**Пример использования:**

```python
from app.services.project_metrics_service import ProjectMetricsService
from app.core.database import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()
service = ProjectMetricsService(db)

# Получить обзор за последние 30 дней
overview = service.get_overview(days=30)

# Получить тренды успешности задач
trends = service.get_trends(
    metric_name="task_success_rate",
    days=7,
    period=MetricPeriod.DAY
)

# Сравнить два периода
period1_start = datetime.utcnow() - timedelta(days=14)
period1_end = datetime.utcnow() - timedelta(days=7)
period2_start = datetime.utcnow() - timedelta(days=7)
period2_end = datetime.utcnow()

comparison = service.compare_periods(
    period1_start, period1_end,
    period2_start, period2_end
)
```

### Типы метрик

1. **PERFORMANCE**: Общая производительность системы
   - `task_success_rate`: Процент успешных задач
   - `avg_execution_time`: Среднее время выполнения

2. **TASK_SUCCESS**: Метрики успешности задач
   - Распределение по статусам
   - Процент успешных/проваленных задач

3. **EXECUTION_TIME**: Метрики времени выполнения
   - Среднее время выполнения
   - Минимальное/максимальное время
   - Распределение по времени

4. **TASK_DISTRIBUTION**: Распределение задач
   - По статусам
   - По приоритетам
   - По уровням автономии

5. **TREND**: Тренды во времени
   - Изменение метрик во времени
   - Прогнозирование

6. **AGGREGATE**: Агрегированные метрики
   - Сводные показатели
   - Комплексные метрики

## Миграции

Для создания таблицы `project_metrics` используется Alembic миграция: `backend/alembic/versions/022_add_project_metrics.py`.

## Тестирование

- **Unit тесты**: `backend/tests/test_project_metrics_service.py`
  - Тесты записи метрик
  - Тесты сбора метрик производительности
  - Тесты сбора распределения задач
  - Тесты получения обзора
  - Тесты получения трендов
  - Тесты сравнения периодов

## Этап 3.1.2: Сбор метрик в реальном времени

### Интеграция с сервисами

Метрики проекта автоматически собираются в следующих сервисах:

#### PlanningService

Метрики собираются при:
- **Анализе задачи** (`_analyze_task`): время анализа задачи
- **Декомпозиции задачи** (`_decompose_task`): время декомпозиции и количество шагов

**Собираемые метрики:**
- `task_analysis_time`: время анализа задачи (секунды)
- `task_decomposition_time`: время декомпозиции задачи (секунды)

#### ExecutionService

Метрики собираются при:
- **Выполнении шага** (`execute_step`): время выполнения каждого шага
- **Выполнении плана** (`execute_plan`): общее время выполнения и успешность

**Собираемые метрики:**
- `step_execution_time`: время выполнения шага (секунды)
- `plan_execution_time`: время выполнения плана (секунды)
- `plan_execution_success`: успешность выполнения плана (1.0 = успех, 0.0 = провал)

#### PromptService

Метрики собираются при:
- **Использовании промпта** (`record_usage`): время выполнения
- **Успешном использовании** (`record_success`): успешность промпта
- **Неудачном использовании** (`record_failure`): успешность промпта

**Собираемые метрики:**
- `prompt_execution_time`: время выполнения промпта (секунды)
- `prompt_success_rate`: процент успешных использований промпта

### Агрегация метрик

Метрики автоматически агрегируются по периодам:
- **HOUR**: Агрегация по часам
- **DAY**: Агрегация по дням
- **WEEK**: Агрегация по неделям
- **MONTH**: Агрегация по месяцам

Периоды округляются до границ (например, час начинается с :00:00), что обеспечивает консистентную агрегацию.

### Примеры использования

```python
from app.services.project_metrics_service import ProjectMetricsService
from app.core.database import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()
service = ProjectMetricsService(db)

# Метрики автоматически собираются при работе сервисов
# Например, при использовании PlanningService:
from app.services.planning_service import PlanningService

planning_service = PlanningService(db)
# При вызове create_plan метрики автоматически записываются

# Получить собранные метрики
overview = service.get_overview(days=7)
print(f"Success rate: {overview['performance']['success_rate']}")
print(f"Avg execution time: {overview['performance']['avg_execution_time']}")
```

## Дальнейшее развитие

- **Этап 3.1.3**: API endpoints для метрик проекта
- **Этап 3.2**: Регулярный самоаудит с автоматическими рекомендациями
- **Этап 3.3**: Dashboard для визуализации метрик

