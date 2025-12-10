# Рефакторинг UncertaintyService для саморазвития

## ✅ Выполнено

### Проблема
В исходном коде `UncertaintyService` было много хардкодных параметров:
- Веса типов неопределенности (0.2, 0.15, 0.25, 0.3, 0.1)
- Пороги уровней неопределенности (0.7, 0.5, 0.3, 0.1)
- Списки ключевых слов (vague_verbs, question_words, reference_words, etc.)
- Пороги для проверок (len < 5, count >= 2, etc.)

Это препятствовало саморазвитию системы, так как параметры не могли адаптироваться на основе опыта.

### Решение

#### 1. Модель UncertaintyParameter
**Файл:** `backend/app/models/uncertainty_parameters.py`

**Функциональность:**
- Хранение всех параметров в базе данных
- Версионирование параметров
- История изменений (learning_history)
- Метрики производительности (performance_metrics)
- Типы параметров: WEIGHT, THRESHOLD, KEYWORD_LIST, COUNT_THRESHOLD, SIMILARITY_THRESHOLD

#### 2. UncertaintyLearningService
**Файл:** `backend/app/services/uncertainty_learning_service.py`

**Функциональность:**
- `learn_from_feedback()` - Обучение на основе обратной связи
- `_adjust_parameters_for_over_escalation()` - Адаптация при переоценке
- `_adjust_parameters_for_under_escalation()` - Адаптация при недооценке
- `_improve_detection()` - Улучшение обнаружения
- `_reinforce_parameters()` - Подкрепление правильных параметров
- `update_keyword_lists_with_llm()` - Обновление ключевых слов через LLM

#### 3. Рефакторинг UncertaintyService
**Файл:** `backend/app/services/uncertainty_service.py`

**Изменения:**
- Все веса теперь загружаются из БД через `_get_parameter_value()`
- Все пороги теперь загружаются из БД
- Все списки ключевых слов теперь загружаются из БД
- Все пороги проверок теперь загружаются из БД
- Добавлен метод `learn_from_feedback()` для обучения
- Добавлен метод `update_keyword_lists_with_llm()` для обновления ключевых слов
- Ленивая загрузка параметров с кэшированием

## Механизм саморазвития

### 1. Обучение на основе обратной связи

```python
# После выполнения задачи
uncertainty_service = UncertaintyService(db, ollama_client)
assessment = await uncertainty_service.assess_uncertainty(query)

# ... задача выполнена ...

# Обучить на основе результата
await uncertainty_service.learn_from_feedback(
    assessment=assessment,
    actual_outcome="correct",  # или "over_escalated", "under_escalated", "missed"
    user_feedback={"rating": 5, "comment": "Оценка была точной"}
)
```

### 2. Адаптация параметров

**При переоценке (over_escalated):**
- Веса типов неопределенности уменьшаются на 10%
- Пороги уровней увеличиваются на 5%

**При недооценке (under_escalated):**
- Веса типов неопределенности увеличиваются на 10%
- Пороги уровней уменьшаются на 5%

**При пропуске (missed):**
- Все веса немного увеличиваются для улучшения обнаружения

**При правильной оценке (correct):**
- Параметры подкрепляются (увеличиваются метрики точности)

### 3. Обновление ключевых слов через LLM

```python
# Периодически обновлять ключевые слова на основе исторических данных
historical_queries = [
    {"query": "...", "uncertainty_type": "ambiguous_intent", "was_correct": True},
    # ...
]

result = await uncertainty_service.update_keyword_lists_with_llm(
    uncertainty_type="ambiguous_intent",
    historical_queries=historical_queries
)
```

LLM анализирует исторические запросы и предлагает:
- Новые ключевые слова для добавления
- Ключевые слова для удаления (ложные срабатывания)
- Обновленный полный список

## Структура параметров в БД

### Веса типов неопределенности
- `weight_ambiguous_intent` (default: 0.2)
- `weight_missing_context` (default: 0.15)
- `weight_multiple_interpretations` (default: 0.25)
- `weight_vague_requirements` (default: 0.15)
- `weight_conflicting_information` (default: 0.3)
- `weight_unknown_entity` (default: 0.1)
- `weight_temporal_uncertainty` (default: 0.1)
- `weight_scope_uncertainty` (default: 0.15)

### Пороги уровней
- `threshold_critical` (default: 0.7)
- `threshold_high` (default: 0.5)
- `threshold_medium` (default: 0.3)
- `threshold_low` (default: 0.1)

### Списки ключевых слов
- `keywords_ambiguous_intent_verbs`
- `keywords_ambiguous_intent_questions`
- `keywords_ambiguous_intent_actions`
- `keywords_missing_context_references`
- `keywords_missing_context_pronouns`
- `keywords_missing_context_temporal`
- `keywords_multiple_interpretations_alternatives`
- `keywords_multiple_interpretations_conjunctions`
- `keywords_multiple_interpretations_actions`
- `keywords_vague_requirements_quantifiers`
- `keywords_vague_requirements_time`
- `keywords_vague_requirements_incomplete`
- `keywords_conflicting_information_pairs`
- `keywords_conflicting_information_indicators`
- `keywords_temporal_uncertainty_relative`
- `keywords_temporal_uncertainty_questions`
- `keywords_temporal_uncertainty_vague`
- `keywords_scope_uncertainty_general`
- `keywords_scope_uncertainty_domains`
- `keywords_scope_uncertainty_extreme`

### Пороги проверок
- `threshold_ambiguous_intent_min_length` (default: 5)
- `threshold_multiple_interpretations_min_items` (default: 2)
- `threshold_unknown_entities_max_capitalized` (default: 3)
- `threshold_unknown_entities_min_length` (default: 2)
- `threshold_clarification_max_questions` (default: 5)

## Интеграция с системой самообучения

### С MetaLearningService
- Анализ паттернов успешных/неуспешных оценок
- Выявление оптимальных значений параметров
- Автоматическая адаптация на основе метрик

### С AgentEvolutionService
- A/B тестирование различных наборов параметров
- Выбор лучших параметров на основе результатов
- Автоматическое применение улучшений

## Примеры использования

### Обучение на основе обратной связи

```python
# После выполнения задачи
assessment = await uncertainty_service.assess_uncertainty("Сделай что-то")
# Система определила HIGH uncertainty и запросила уточнение

# Пользователь ответил, задача выполнена успешно
# Но пользователь сказал, что уточнение не было нужно
await uncertainty_service.learn_from_feedback(
    assessment=assessment,
    actual_outcome="over_escalated",
    user_feedback={"comment": "Запрос был понятен, уточнение не требовалось"}
)

# Параметры автоматически адаптируются:
# - Вес ambiguous_intent уменьшится на 10%
# - Порог high увеличится на 5%
```

### Обновление ключевых слов

```python
# Собрать исторические данные
historical = [
    {"query": "сделай что-то", "type": "ambiguous_intent", "correct": False},
    {"query": "обработай файлы", "type": "ambiguous_intent", "correct": True},
    # ...
]

# Обновить через LLM
result = await uncertainty_service.update_keyword_lists_with_llm(
    uncertainty_type="ambiguous_intent",
    historical_queries=historical
)

# LLM проанализирует и предложит новые ключевые слова
# Система автоматически обновит параметр в БД
```

## Преимущества

1. **Саморазвитие:** Параметры адаптируются на основе опыта
2. **Гибкость:** Легко настраивать параметры без изменения кода
3. **Отслеживаемость:** История всех изменений параметров
4. **Метрики:** Отслеживание производительности параметров
5. **LLM-улучшения:** Автоматическое обновление ключевых слов

## Следующие шаги

1. ⏳ Интеграция в RequestOrchestrator для автоматического обучения
2. ⏳ Периодический анализ и обновление параметров
3. ⏳ A/B тестирование наборов параметров
4. ⏳ API endpoints для управления параметрами
5. ⏳ Визуализация истории изменений параметров

