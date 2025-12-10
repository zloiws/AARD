# Реализация системы оценки и обработки неопределенности

## ✅ Выполнено

### UncertaintyService
**Файл:** `backend/app/services/uncertainty_service.py`

**Функциональность:**

#### 1. Уровни неопределенности
- **NONE** - Четкий и однозначный запрос
- **LOW** - Незначительная неоднозначность, может быть разрешена автоматически
- **MEDIUM** - Умеренная неоднозначность, может потребовать уточнения
- **HIGH** - Значительная неоднозначность, требует уточнения
- **CRITICAL** - Невозможно продолжить без уточнения

#### 2. Типы неопределенности
- **AMBIGUOUS_INTENT** - Неясное намерение пользователя
- **MISSING_CONTEXT** - Отсутствует необходимый контекст
- **MULTIPLE_INTERPRETATIONS** - Множественные валидные интерпретации
- **VAGUE_REQUIREMENTS** - Расплывчатые или неполные требования
- **CONFLICTING_INFORMATION** - Противоречивая информация в запросе
- **UNKNOWN_ENTITY** - Неизвестные сущности (имена, ссылки)
- **TEMPORAL_UNCERTAINTY** - Неясные временные ссылки
- **SCOPE_UNCERTAINTY** - Неясная область действия или границы

#### 3. Методы оценки

##### `assess_uncertainty()`
- Оценивает неопределенность в запросе пользователя
- Вычисляет оценку неопределенности (0.0-1.0)
- Определяет уровень и типы неопределенности
- Генерирует вопросы для уточнения при необходимости

##### Методы проверки
- `_check_ambiguous_intent()` - Проверка неясного намерения
- `_check_missing_context()` - Проверка отсутствующего контекста
- `_check_multiple_interpretations()` - Проверка множественных интерпретаций
- `_check_vague_requirements()` - Проверка расплывчатых требований
- `_check_conflicting_information()` - Проверка противоречивой информации
- `_check_unknown_entities()` - Проверка неизвестных сущностей
- `_check_temporal_uncertainty()` - Проверка временной неопределенности
- `_check_scope_uncertainty()` - Проверка неопределенности области действия

#### 4. Методы обработки

##### `handle_uncertainty()`
- Обрабатывает неопределенность на основе оценки
- Определяет действие: proceed, request_clarification, escalate
- Генерирует сообщения и вопросы для уточнения
- Создает предположения для среднего уровня неопределенности

##### `_generate_clarification_questions()`
- Генерирует вопросы для уточнения на основе типов неопределенности
- Ограничивает количество вопросов (максимум 5)

##### `_generate_assumptions()`
- Генерирует предположения для среднего уровня неопределенности
- Позволяет продолжить выполнение с разумными предположениями

## Интеграция

### Использование в RequestOrchestrator

```python
from app.services.uncertainty_service import UncertaintyService

# При получении запроса
uncertainty_service = UncertaintyService(db, ollama_client)
assessment = await uncertainty_service.assess_uncertainty(
    query=message,
    context={"previous_messages": history}
)

if assessment["requires_clarification"]:
    handling = await uncertainty_service.handle_uncertainty(assessment)
    if handling["action"] == "request_clarification":
        # Вернуть вопросы пользователю
        return OrchestrationResult(
            response=handling["message"] + "\n" + "\n".join(handling["clarification_questions"]),
            metadata={"uncertainty": assessment}
        )
```

## Примеры использования

### Оценка неопределенности

```python
assessment = await uncertainty_service.assess_uncertainty(
    query="Сделай что-то с файлами",
    context=None
)

# Результат:
# {
#   "uncertainty_level": "high",
#   "uncertainty_score": 0.6,
#   "uncertainty_types": ["ambiguous_intent", "vague_requirements"],
#   "issues": ["Неясное намерение: запрос слишком общий"],
#   "requires_clarification": True,
#   "can_proceed": False
# }
```

### Обработка неопределенности

```python
handling = await uncertainty_service.handle_uncertainty(assessment)

# Результат для HIGH uncertainty:
# {
#   "action": "request_clarification",
#   "message": "Запрос содержит неоднозначность. Пожалуйста, уточните следующие моменты:",
#   "clarification_questions": [
#     "Что именно вы хотите сделать?",
#     "Можете уточнить требования? (количество, время, область)"
#   ]
# }
```

## Алгоритм оценки

1. **Проверка всех типов неопределенности** - Каждый тип добавляет к общей оценке
2. **Нормализация оценки** - Ограничение до 0.0-1.0
3. **Определение уровня** - На основе нормализованной оценки
4. **Генерация вопросов** - Если требуется уточнение

## Стратегии обработки

- **CRITICAL/HIGH** - Запросить уточнение, не продолжать
- **MEDIUM** - Продолжить с предположениями, уведомить пользователя
- **LOW** - Продолжить нормально, залогировать для проверки
- **NONE** - Продолжить нормально

## Следующие шаги (опционально)

1. ⏳ Интеграция в RequestOrchestrator для автоматической проверки
2. ⏳ Использование LLM для более точной оценки неопределенности
3. ⏳ Обучение на исторических данных для улучшения точности
4. ⏳ API endpoints для управления неопределенностью
5. ⏳ Метрики и мониторинг неопределенности
6. ⏳ Автоматическое извлечение контекста из истории диалога

