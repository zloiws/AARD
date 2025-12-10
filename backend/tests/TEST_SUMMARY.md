# Сводка интеграционных тестов

## Конфигурация

Все тесты используют конкретную модель из БД:
- **Сервер:** 10.39.0.6
- **Модель:** gemma3:4b

## Список тестов

### 1. test_integration_basic.py
- `test_basic_orchestrator_works` - Базовый тест работы оркестратора

### 2. test_integration_simple_question.py (5 тестов)
- `test_simple_question_basic` - Простой вопрос (2+2)
- `test_simple_question_greeting` - Приветствие
- `test_simple_question_factual` - Фактический вопрос (столица Франции)
- `test_simple_question_explanation` - Объяснение (что такое Python)
- `test_simple_question_prompt_manager_integration` - Интеграция PromptManager

### 3. test_integration_code_generation.py (4 теста)
- `test_code_generation_simple_function` - Генерация простой функции
- `test_code_generation_with_planning` - Генерация кода с планированием
- `test_code_generation_prompt_metrics` - Метрики промптов при генерации кода
- `test_planning_only` - Только планирование (без выполнения)

## Запуск тестов

```powershell
cd backend

# Все тесты
python -m pytest tests/test_integration_*.py -v -s

# Конкретный файл
python -m pytest tests/test_integration_basic.py -v -s
python -m pytest tests/test_integration_simple_question.py -v -s
python -m pytest tests/test_integration_code_generation.py -v -s

# Конкретный тест
python -m pytest tests/test_integration_basic.py::test_basic_orchestrator_works -v -s
```

## Ожидаемые результаты

Все тесты должны:
1. Найти сервер 10.39.0.6 в БД
2. Найти модель gemma3:4b на этом сервере
3. Успешно выполнить запрос через RequestOrchestrator
4. Получить валидный ответ от LLM
5. Проверить, что модель соответствует указанной (gemma3:4b)

## Возможные проблемы

1. **Сервер не найден** - проверьте, что сервер с IP 10.39.0.6 добавлен в БД и активен
2. **Модель не найдена** - проверьте, что модель gemma3:4b добавлена на сервер и активна
3. **Ошибка подключения** - проверьте доступность Ollama сервера по адресу 10.39.0.6:11434
4. **Модель не поддерживает chat** - убедитесь, что модель поддерживает чат (не embedding модель)
