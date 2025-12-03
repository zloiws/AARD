# Feedback Learning Service

## Обзор

FeedbackLearningService реализует обучение на основе человеческой обратной связи. Система извлекает паттерны из утверждений/отклонений и применяет их к будущим решениям, создавая замкнутый цикл обучения.

## Концепция

Когда человек утверждает или отклоняет план/артефакт/промпт, система:
1. Извлекает паттерны из обратной связи
2. Сохраняет их как LearningPattern
3. Применяет изученные паттерны к будущим задачам

## Основные методы

### learn_from_approval_feedback

Извлекает паттерны из обратной связи по утверждению:

```python
from app.services.feedback_learning_service import FeedbackLearningService

service = FeedbackLearningService(db)
pattern = service.learn_from_approval_feedback(approval, "Good plan, well structured")
```

### apply_learned_patterns

Применяет изученные паттерны к задаче:

```python
recommendations = service.apply_learned_patterns(
    task_description="Generate code for data processing",
    task_category="code_generation"
)
```

### extract_improvements_from_feedback

Извлекает улучшения из текста обратной связи:

```python
improvements = service.extract_improvements_from_feedback(
    "The plan is too complex. Please simplify."
)
# Returns: {
#   "improvements": ["Simplify the approach"],
#   "keywords": ["simplicity"]
# }
```

## Типы паттернов

### Strategy Patterns

Извлекаются из утверждений планов:
- Структура успешных планов
- Рекомендации по упрощению
- Предложения по добавлению шагов

### Prompt Patterns

Извлекаются из утверждений промптов:
- Эффективные ключевые слова
- Улучшения ясности
- Рекомендации по специфичности

### Tool Selection Patterns

Извлекаются из утверждений артефактов:
- Эффективные инструменты
- Рекомендации по выбору

## Интеграция

FeedbackLearningService автоматически интегрирован в ApprovalService:

- При утверждении (`approve_request`) - извлекает успешные паттерны
- При отклонении (`reject_request`) - извлекает паттерны ошибок

## Примеры

### Пример 1: Обучение на утверждении

```python
# Человек утверждает план с комментарием
approval_service.approve_request(
    request_id=approval_id,
    approved_by="user",
    feedback="Excellent plan, well structured and clear steps"
)

# Система автоматически извлекает паттерн:
# - Тип: Strategy
# - Success rate: 1.0
# - Suggestion: "maintain_approach"
```

### Пример 2: Обучение на отклонении

```python
# Человек отклоняет план с комментарием
approval_service.reject_request(
    request_id=approval_id,
    rejected_by="user",
    feedback="Too complex, simplify the approach and add validation"
)

# Система извлекает паттерн:
# - Тип: Strategy
# - Success rate: 0.0
# - Suggestion: "simplify"
# - Improvements: ["Simplify the approach", "Add more validation steps"]
```

### Пример 3: Применение изученных паттернов

```python
# При создании нового плана система применяет изученные паттерны
recommendations = feedback_learning.apply_learned_patterns(
    task_description="Process user data",
    task_category="data_processing"
)

# recommendations содержит:
# - patterns_found: количество найденных паттернов
# - recommendations: список рекомендаций с success_rate
```

## Статистика

```python
stats = service.get_feedback_statistics(agent_id=agent_id, time_range_days=30)

# stats содержит:
# - total_approvals: общее количество утверждений
# - approved/rejected: количество утвержденных/отклоненных
# - with_feedback: количество с обратной связью
# - patterns_extracted: количество извлеченных паттернов
# - feedback_rate: процент утверждений с обратной связью
```

## Категоризация задач

Система автоматически категоризирует задачи:
- `code_generation` - генерация кода
- `data_processing` - обработка данных
- `testing` - тестирование
- `deployment` - развертывание
- `general` - общие задачи

## Тестирование

```bash
python -m pytest tests/integration/test_feedback_learning.py -v
```

## Преимущества

1. **Непрерывное обучение:** Система учится на каждом утверждении/отклонении
2. **Применение знаний:** Изученные паттерны применяются к новым задачам
3. **Улучшение качества:** Со временем качество планов улучшается
4. **Прозрачность:** Все паттерны сохраняются и могут быть просмотрены

## Следующие шаги

- [x] Реализация FeedbackLearningService
- [x] Интеграция в ApprovalService
- [ ] UI для просмотра изученных паттернов
- [ ] Метрики эффективности обучения
- [ ] Автоматическое применение паттернов в PlanningService

## См. также

- [Meta Learning](META_LEARNING.md) - общая система мета-обучения
- [Adaptive Approval](ADAPTIVE_APPROVAL.md) - адаптивные решения об утверждении

