# Adaptive Approval Service

## Обзор

AdaptiveApprovalService реализует интеллектуальную систему принятия решений об утверждении планов на основе:
- **Trust Score агента** - история успешных выполнений
- **Уровень риска задачи** - сложность, тип операций
- **Сложность плана** - количество шагов, зависимости

Это улучшает Human-in-the-Loop механизм, автоматически определяя, когда действительно требуется человеческое утверждение.

## Концепция

Вместо того, чтобы требовать утверждение для всех планов, система адаптивно определяет необходимость утверждения:

- **Высокий риск** → всегда требует утверждения
- **Средний риск + низкий trust** → требует утверждения
- **Средний риск + высокий trust** → может быть автоматически одобрен
- **Низкий риск + высокий trust** → автоматически одобряется

## Trust Score агента

Trust Score рассчитывается на основе:

1. **Success Rate** (вес 60%) - общий процент успешных выполнений
2. **Опыт** (вес 20%) - количество выполненных задач
3. **Недавняя производительность** (вес 20%) - успешность за последние 30 дней

### Формула

```
trust_score = (
    success_rate * 0.6 +
    min(1.0, total_tasks / 100.0) * 0.2 +
    recent_performance * 0.2
)
```

### Пороги

- **Высокий trust**: > 0.8
- **Средний trust**: 0.5 - 0.8
- **Низкий trust**: < 0.5

## Уровень риска задачи

Риск рассчитывается на основе:

1. **Количество шагов** (0.0 - 0.3)
   - > 10 шагов: +0.3
   - > 5 шагов: +0.2
   - > 2 шагов: +0.1

2. **Высокорисковые операции** (0.0 - 0.4)
   - Ключевые слова: delete, remove, drop, destroy, format, write, modify, execute, system, shell
   - ≥ 3 ключевых слова: +0.4
   - ≥ 2 ключевых слова: +0.3
   - ≥ 1 ключевое слово: +0.2

3. **Шаги, требующие утверждения** (0.0 - 0.2)
   - Каждый шаг с `approval_required=true`: +0.1

4. **Типы шагов высокого риска** (0.0 - 0.1)
   - validation, approval шаги: +0.05 каждый

5. **Сложные зависимости** (0.0 - 0.1)
   - > 3 шагов с зависимостями: +0.1
   - > 1 шага с зависимостями: +0.05

### Пороги риска

- **Высокий риск**: ≥ 0.7
- **Средний риск**: 0.4 - 0.7
- **Низкий риск**: < 0.4

## Логика принятия решений

```python
if task_risk >= 0.7:
    require_approval = True  # Всегда требует утверждения
elif task_risk >= 0.4:
    if agent_trust < 0.8:
        require_approval = True  # Средний риск + низкий trust
    else:
        require_approval = False  # Средний риск + высокий trust
else:
    if agent_trust < 0.5:
        require_approval = True  # Низкий риск + очень низкий trust
    else:
        require_approval = False  # Низкий риск + приемлемый trust
```

## Использование

### Базовое использование

```python
from app.services.adaptive_approval_service import AdaptiveApprovalService

service = AdaptiveApprovalService(db)

# Определить необходимость утверждения
requires_approval, metadata = service.should_require_approval(
    plan=plan,
    agent_id=agent_id,
    task_risk_level=0.5
)

if requires_approval:
    # Создать approval request
    pass
else:
    # Автоматически одобрить
    plan.status = "approved"
```

### Расчет Trust Score

```python
trust_score = service.calculate_agent_trust_score(agent_id)
print(f"Agent trust score: {trust_score:.2f}")
```

### Расчет уровня риска

```python
risk_level = service.calculate_task_risk_level(
    task_description="Delete all files",
    steps=plan.steps
)
print(f"Task risk level: {risk_level:.2f}")
```

## Интеграция в PlanningService

PlanningService автоматически использует AdaptiveApprovalService:

```python
# В _create_plan_approval_request:
requires_approval, decision_metadata = adaptive_approval.should_require_approval(
    plan=plan,
    agent_id=agent_id,
    task_risk_level=risks.get("overall_risk")
)

if not requires_approval:
    # Автоматически одобрить план
    plan.status = "approved"
    plan.approved_at = datetime.utcnow()
    return None
```

## Статистика утверждений

```python
stats = service.get_approval_statistics(agent_id=agent_id)

# stats содержит:
# - total_requests: общее количество запросов
# - pending: ожидающие утверждения
# - approved: одобренные
# - rejected: отклоненные
# - approval_rate: процент одобрения
```

## Примеры

### Пример 1: Высокий риск - всегда требует утверждения

```python
plan = Plan(goal="Delete all production data", steps=[...])
requires_approval, metadata = service.should_require_approval(
    plan=plan,
    task_risk_level=0.8
)
# requires_approval = True
# metadata["reason"] = "high_risk"
```

### Пример 2: Низкий риск + высокий trust - автоматическое одобрение

```python
plan = Plan(goal="Simple calculation", steps=[...])
requires_approval, metadata = service.should_require_approval(
    plan=plan,
    agent_id=high_trust_agent.id,
    task_risk_level=0.2
)
# requires_approval = False
# metadata["reason"] = "low_risk_acceptable_trust"
```

### Пример 3: Средний риск + низкий trust - требует утверждения

```python
plan = Plan(goal="Modify database schema", steps=[...])
requires_approval, metadata = service.should_require_approval(
    plan=plan,
    agent_id=low_trust_agent.id,
    task_risk_level=0.5
)
# requires_approval = True
# metadata["reason"] = "medium_risk_low_trust"
```

## Тестирование

```bash
python -m pytest tests/integration/test_adaptive_approval.py -v
```

## Настройка порогов

Пороги можно настроить в `AdaptiveApprovalService`:

```python
TRUST_SCORE_THRESHOLD = 0.8  # Порог для высокого trust
HIGH_RISK_THRESHOLD = 0.7    # Порог для высокого риска
MEDIUM_RISK_THRESHOLD = 0.4  # Порог для среднего риска
MIN_EXECUTIONS_FOR_TRUST = 5  # Минимум выполнений для расчета trust
```

## Преимущества

1. **Снижение нагрузки на человека:** Автоматическое одобрение низкорисковых задач
2. **Безопасность:** Высокорисковые задачи всегда требуют утверждения
3. **Адаптивность:** Система учится на истории агентов
4. **Прозрачность:** Все решения логируются с метаданными

## Следующие шаги

- [x] Реализация AdaptiveApprovalService
- [x] Интеграция в PlanningService
- [ ] FeedbackLearningService для обучения на обратной связи
- [ ] Метрики и мониторинг trust scores
- [ ] UI для просмотра trust scores агентов

## См. также

- [Planning Service](../archive/PLANNING_API_TEST_RESULTS.md) - документация по планированию
- [Approval Service](../archive/PLAN_APPROVAL_INTEGRATION.md) - базовая система утверждений

