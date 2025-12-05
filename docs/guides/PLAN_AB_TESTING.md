# A/B Testing для планов

## Обзор

Система A/B тестирования планов позволяет генерировать несколько альтернативных вариантов плана для одной задачи и сравнивать их по различным критериям. Это помогает выбрать оптимальный план на основе конкретных требований и ограничений.

## Функциональность

### Генерация альтернативных планов

Метод `generate_alternative_plans()` в `PlanningService` генерирует 2-3 альтернативных плана с разными стратегическими подходами:

1. **Conservative (Консервативный)**: Минимальный риск, тщательное выполнение
   - Больше шагов
   - Больше проверок на каждом этапе
   - Фокус на надежности и корректности

2. **Balanced (Сбалансированный)**: Оптимальный баланс между скоростью и качеством
   - Умеренное количество шагов
   - Оптимизация для типичных случаев
   - Фокус на практичности и эффективности

3. **Aggressive (Агрессивный)**: Максимизация скорости, принятие более высокого риска
   - Минимум шагов
   - Предположение о лучших сценариях
   - Фокус на скорости и минимальном количестве шагов

### Параллельная генерация

Все альтернативные планы генерируются параллельно с использованием `asyncio.gather()`, что значительно ускоряет процесс по сравнению с последовательной генерацией.

### Метаданные альтернативных планов

Каждый альтернативный план содержит метаданные:

- В поле `strategy`:
  - `alternative_strategy`: Название стратегии (conservative, balanced, aggressive)
  - `alternative_description`: Описание стратегии
  - `alternative_approach`: Подход стратегии
  - `alternative_focus`: Фокус стратегии
  - `alternative_risk_tolerance`: Толерантность к риску

- В поле `alternatives`:
  - `is_alternative`: Флаг, что это альтернативный план
  - `alternative_index`: Индекс альтернативы (0, 1, 2)
  - `alternative_name`: Название альтернативы

## Использование

### Базовое использование (через generate_plan)

Рекомендуемый способ - использовать `generate_plan()` с параметром `generate_alternatives=True`:

```python
from app.services.planning_service import PlanningService
from app.core.database import SessionLocal

db = SessionLocal()
planning_service = PlanningService(db)

# Генерация плана с автоматическим выбором лучшего из альтернатив
best_plan = await planning_service.generate_plan(
    task_description="Create a REST API for user management",
    task_id=task_id,
    generate_alternatives=True,
    num_alternatives=3
)

# Лучший план автоматически выбран и возвращен
print(f"Best plan: {best_plan.goal}")
print(f"Evaluation score: {best_plan.alternatives.get('evaluation_score')}")
print(f"Ranking: {best_plan.alternatives.get('ranking')}")

# Все альтернативы сохранены в БД для сравнения
```

### Прямая генерация альтернатив

Для более детального контроля можно использовать `generate_alternative_plans()` напрямую:

```python
# Генерация альтернативных планов
alternative_plans = await planning_service.generate_alternative_plans(
    task_description="Create a REST API for user management",
    task_id=task_id,
    num_alternatives=2
)

# Обработка результатов
for plan in alternative_plans:
    print(f"Plan: {plan.goal}")
    print(f"Strategy: {plan.strategy.get('alternative_strategy')}")
    print(f"Steps: {len(plan.steps)}")
```

### С контекстом и кастомными весами

```python
context = {
    "existing_services": ["user-service", "product-service"],
    "constraints": ["Must use PostgreSQL", "Must be RESTful"]
}

# Кастомные веса для оценки (приоритет скорости)
weights = {
    "execution_time": 0.5,  # Приоритет скорости
    "approval_points": 0.1,
    "risk_level": 0.2,
    "efficiency": 0.2
}

best_plan = await planning_service.generate_plan(
    task_description="Create a microservice for order processing",
    task_id=task_id,
    context=context,
    generate_alternatives=True,
    num_alternatives=3,
    evaluation_weights=weights
)
```

## Параметры generate_plan() с A/B тестированием

- `task_description` (str): Описание задачи
- `task_id` (UUID, optional): ID задачи для связи планов
- `context` (Dict[str, Any], optional): Дополнительный контекст
- `generate_alternatives` (bool): Включить генерацию альтернатив и автоматический выбор лучшего (по умолчанию: False)
- `num_alternatives` (int): Количество альтернативных планов (2-3, по умолчанию: 3). Используется только если `generate_alternatives=True`
- `evaluation_weights` (Dict[str, float], optional): Веса для критериев оценки. Используется только если `generate_alternatives=True`

## Возвращаемое значение

- Если `generate_alternatives=False`: Один объект `Plan` в статусе `DRAFT` или `APPROVED`
- Если `generate_alternatives=True`: Лучший план из альтернатив (объект `Plan`). Все альтернативы сохраняются в БД для сравнения

## Ограничения

- Количество альтернатив ограничено диапазоном 2-3
- Если запрошено больше 3, будет сгенерировано максимум 3
- Если запрошено меньше 2, будет сгенерировано минимум 2

## Тестирование

Тесты находятся в `backend/tests/test_alternative_plan_generation.py`:

- `test_generate_alternative_plans_basic`: Базовый тест генерации альтернативных планов
- `test_generate_alternative_plans_three_variants`: Тест генерации 3 вариантов
- `test_generate_alternative_plans_parallel_execution`: Тест параллельного выполнения
- `test_generate_alternative_plans_different_strategies`: Тест различных стратегий
- `test_generate_alternative_plans_with_context`: Тест с контекстом
- `test_generate_alternative_plans_limit_enforcement`: Тест ограничений

## Оценка планов

### PlanEvaluationService

Сервис `PlanEvaluationService` оценивает планы по четырем критериям:

1. **Execution Time (Время выполнения)** - 25%
   - Оценивает ожидаемое время выполнения
   - Более короткое время = выше оценка

2. **Approval Points (Точки утверждения)** - 20%
   - Подсчитывает количество точек утверждения
   - Меньше точек = выше оценка

3. **Risk Level (Уровень риска)** - 25%
   - Анализирует уровень риска плана
   - Меньше риска = выше оценка

4. **Efficiency (Эффективность)** - 30%
   - Оценивает оптимальность количества шагов
   - Оптимальный диапазон: 3-7 шагов

### Использование

```python
from app.services.plan_evaluation_service import PlanEvaluationService

evaluation_service = PlanEvaluationService(db)

# Оценка одного плана
result = evaluation_service.evaluate_plan(plan)
print(f"Total score: {result.total_score}")
print(f"Scores: {result.scores}")
print(f"Recommendations: {result.recommendations}")

# Оценка и ранжирование нескольких планов
results = evaluation_service.evaluate_plans(alternative_plans)
for result in results:
    print(f"Plan {result.ranking}: {result.total_score}")

# Сравнение планов
comparison = evaluation_service.compare_plans(alternative_plans)
print(f"Best plan: {comparison['best_plan']['goal']}")
```

### Кастомные веса

Можно настроить веса критериев:

```python
weights = {
    "execution_time": 0.5,  # Приоритет скорости
    "approval_points": 0.1,
    "risk_level": 0.1,
    "efficiency": 0.3
}

result = evaluation_service.evaluate_plan(plan, weights)
```

## Интеграция в PlanningService

A/B тестирование полностью интегрировано в `PlanningService.generate_plan()`. 

### Автоматический выбор лучшего плана

При включении `generate_alternatives=True`:
1. Генерируются альтернативные планы параллельно
2. Все планы оцениваются через `PlanEvaluationService`
3. Выбирается лучший план на основе оценки
4. Все альтернативы сохраняются в БД с метаданными:
   - `is_best`: Флаг лучшего плана
   - `evaluation_score`: Общая оценка плана
   - `ranking`: Ранг плана среди альтернатив

### Пример использования

```python
# Простое использование - автоматический выбор лучшего
best_plan = await planning_service.generate_plan(
    task_description="Build a web application",
    generate_alternatives=True
)

# План уже выбран и готов к использованию
print(f"Best plan selected: {best_plan.goal}")
print(f"Score: {best_plan.alternatives.get('evaluation_score')}")

# Все альтернативы доступны в БД для сравнения
```

## Следующие шаги

После генерации и оценки альтернативных планов можно:

1. Сравнить планы в UI (см. Шаг 6.2.1)
2. Использовать выбранный лучший план для выполнения
3. Просмотреть все альтернативы для анализа

## См. также

- [PlanningService](../backend/app/services/planning_service.py)
- [PlanEvaluationService](../backend/app/services/plan_evaluation_service.py)
- [Plan Model](../backend/app/models/plan.py)

