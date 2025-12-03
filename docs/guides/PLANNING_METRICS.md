# Planning Metrics Service

## Обзор

PlanningMetricsService отслеживает качество и производительность планов, предоставляя метрики для анализа и улучшения процесса планирования.

## Концепция

Система собирает метрики по:
- **Качеству планов** - оценка структуры и эффективности
- **Успешности выполнения** - процент успешных выполнений
- **Производительности** - время выполнения, точность оценок
- **Статистике** - общие показатели по агентам/времени

## Метрики качества плана

### Quality Score (0.0 - 1.0)

Оценка качества рассчитывается на основе:

1. **Количество шагов** (30%)
   - Оптимально: 3-7 шагов → +0.3
   - Приемлемо: 2-10 шагов → +0.2
   - Другое: → +0.1

2. **Структура шагов** (20%)
   - Наличие обязательных полей (step_id, description, type)
   - Процент хорошо структурированных шагов

3. **Успешность выполнения** (30%)
   - Процент успешных выполнений
   - Учитывается только если есть история выполнения

4. **Точность оценки длительности** (20%)
   - Сравнение estimated_duration и actual_duration
   - Чем ближе, тем выше оценка

## Использование

### Расчет качества плана

```python
from app.services.planning_metrics_service import PlanningMetricsService

service = PlanningMetricsService(db)
quality_score = service.calculate_plan_quality_score(plan)

print(f"Plan quality: {quality_score:.2f}")
```

### Отслеживание выполнения

```python
service.track_plan_execution_success(
    plan_id=plan.id,
    success=True,
    execution_time_ms=5000
)
```

### Получение статистики

```python
stats = service.get_planning_statistics(
    agent_id=agent_id,
    time_range_days=30
)

# stats содержит:
# - total_plans: общее количество планов
# - completed/failed/executing/approved: по статусам
# - success_rate: процент успешных выполнений
# - average_quality_score: средняя оценка качества
# - average_steps_per_plan: среднее количество шагов
# - average_duration_seconds: средняя длительность
```

### Детальный анализ качества

```python
breakdown = service.get_plan_quality_breakdown(plan_id)

# breakdown содержит:
# - overall_quality_score: общая оценка
# - factors: детализация по факторам
# - execution_stats: статистика выполнения
```

## Интеграция

PlanningMetricsService автоматически интегрирован в:

- **PlanningService** - рассчитывает quality_score при создании плана
- **ExecutionService** - отслеживает успешность выполнения

## Примеры

### Пример 1: Расчет качества

```python
plan = planning_service.generate_plan(...)
quality_score = metrics_service.calculate_plan_quality_score(plan)

if quality_score < 0.5:
    print("Plan quality is low, consider improvements")
```

### Пример 2: Статистика за период

```python
stats = metrics_service.get_planning_statistics(time_range_days=7)

print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Average quality: {stats['average_quality_score']:.2f}")
```

### Пример 3: Детальный анализ

```python
breakdown = metrics_service.get_plan_quality_breakdown(plan_id)

print(f"Overall quality: {breakdown['overall_quality_score']:.2f}")
print(f"Step count score: {breakdown['factors']['step_count_score']:.2f}")
print(f"Execution success: {breakdown['execution_stats']['success_rate']:.2%}")
```

## Интерпретация метрик

### Quality Score

- **0.8 - 1.0**: Отличное качество
- **0.6 - 0.8**: Хорошее качество
- **0.4 - 0.6**: Приемлемое качество
- **0.0 - 0.4**: Низкое качество, требуется улучшение

### Success Rate

- **> 0.9**: Очень высокая успешность
- **0.7 - 0.9**: Высокая успешность
- **0.5 - 0.7**: Средняя успешность
- **< 0.5**: Низкая успешность, требуется анализ

## Тестирование

```bash
python -m pytest tests/integration/test_planning_metrics.py -v
```

## Применение метрик

Метрики можно использовать для:

1. **Автоматического улучшения** - низкие оценки → предложения по улучшению
2. **A/B тестирования** - сравнение качества разных стратегий
3. **Мониторинга** - отслеживание деградации качества
4. **Отчетности** - статистика для пользователей

## Следующие шаги

- [x] Реализация PlanningMetricsService
- [x] Интеграция в PlanningService и ExecutionService
- [ ] API endpoints для метрик
- [ ] Dashboard с визуализацией метрик
- [ ] Автоматические алерты при снижении качества
- [ ] Интеграция с Prometheus (если используется)

## См. также

- [Planning Service](../archive/PLANNING_API_TEST_RESULTS.md) - генерация планов
- [Execution Service](../archive/PLAN_APPROVAL_INTEGRATION.md) - выполнение планов
- [Meta Learning](META_LEARNING.md) - самоусовершенствование

