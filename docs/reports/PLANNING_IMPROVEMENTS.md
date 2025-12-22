# Улучшения логики планирования с Digital Twin

## Выполненные улучшения

### 1. ✅ Интеграция Digital Twin контекста в промпты

#### Метод `_build_enhanced_analysis_prompt`
- Использует Digital Twin контекст для построения промпта
- Включает:
  - Исходный запрос пользователя
  - Предыдущие планы (последние 2 версии)
  - Существующие артефакты (последние 5)
  - Недавние взаимодействия (последние 3)
  - Дополнительный контекст из параметров

**Пример промпта:**
```
Task: Сравнить цены на товары

Original Request:
Сравнить цены на товары

Previous Plans (for reference):
[...]

Existing Artifacts:
[...]

Recent Interactions:
[...]

Analyze this task considering the context above and create a strategic plan.
```

### 2. ✅ Улучшенная валидация и парсинг JSON

#### Метод `_parse_and_validate_json`
Реализовано 4 метода извлечения JSON:
1. Поиск JSON объекта/массива в ответе
2. Парсинг всего ответа как JSON
3. Исправление распространенных ошибок (trailing commas)
4. Извлечение JSON из markdown code blocks

**Дополнительные возможности:**
- Валидация структуры (dict/list)
- Проверка наличия обязательных ключей
- Установка значений по умолчанию для отсутствующих ключей

**Пример использования:**
```python
strategy = self._parse_and_validate_json(
    response.response,
    expected_keys=["approach", "assumptions", "constraints", "success_criteria"]
)

steps = self._parse_and_validate_json(
    response.response,
    expected_structure="list"
)
```

### 3. ✅ Улучшенные промпты для декомпозиции задачи

Метод `_decompose_task` теперь:
- Использует Digital Twin контекст
- Включает существующие артефакты (для понимания зависимостей)
- Предоставляет структурированный контекст с стратегией

## Преимущества

1. **Полная наблюдаемость**: Модель видит всю историю задачи
2. **Улучшенное планирование**: Модель может использовать предыдущие планы и артефакты
3. **Надежность**: Улучшенный парсинг JSON снижает количество ошибок
4. **Контекстность**: Промпты содержат всю необходимую информацию

## Использование

Все улучшения работают автоматически при вызове `PlanningService.generate_plan()`:

```python
planning_service = PlanningService(db)
plan = await planning_service.generate_plan(
    task_description="Сравнить цены на товары",
    task_id=existing_task_id,  # Если задача уже существует
    context={"additional": "context"}  # Дополнительный контекст
)
```

## Логирование

Все операции логируются через tracing:
- `planning.analyze_task` - анализ задачи
- `planning.decompose_task` - декомпозиция задачи

## Тестирование

Для тестирования с моделью gemma3:4b:

1. Убедитесь, что модель активна:
   ```bash
   python backend/scripts/switch_model_for_tests.py
   ```

2. Создайте задачу через API или UI

3. Просмотрите логи для проверки использования контекста

## Следующие шаги

1. ⏳ Добавить примеры успешных планов в промпты
2. ⏳ Интеграция в ExecutionService для записи логов выполнения в Digital Twin
3. ⏳ UI для просмотра Digital Twin контекста

## Связанные документы

- `DIGITAL_TWIN_IMPLEMENTATION.md` - описание Digital Twin
- `PLANNING_LOGIC_ANALYSIS.md` - анализ логики планирования

