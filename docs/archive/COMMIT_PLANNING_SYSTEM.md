# Сообщение для коммита

```
feat: Система планирования задач

## Основные изменения

### 1. Сервис планирования
- Добавлен `backend/app/services/planning_service.py`
- Генерация планов через LLM с анализом задачи и декомпозицией
- Создание стратегии, разбиение на шаги, оценка рисков
- Утверждение, выполнение и перепланирование планов
- Защита от зацикливания: таймауты 5 минут на каждый этап

### 2. API endpoints для планов
- Добавлен `backend/app/api/routes/plans.py`
- POST /api/plans/ - создание плана
- GET /api/plans/ - список планов с фильтрацией
- GET /api/plans/{plan_id} - детали плана
- PUT /api/plans/{plan_id} - обновление плана
- POST /api/plans/{plan_id}/approve - утверждение плана
- POST /api/plans/{plan_id}/execute - начало выполнения
- POST /api/plans/{plan_id}/replan - перепланирование
- GET /api/plans/{plan_id}/status - статус выполнения

### 3. Исправления модели Plan
- Изменен тип статуса с SQLEnum на String (lowercase для соответствия БД)
- Исправлены все места использования plan.status.value на plan.status

### 4. Улучшения OllamaClient
- Увеличен таймаут для задач планирования до 10 минут (600 секунд)
- Добавлено логирование для задач планирования

### 5. Настройка основных моделей
- Добавлен скрипт `backend/scripts/setup_main_models.py`
- Настроены модели deepseek-r1 и qwen3-coder с приоритетом 100
- Назначены capabilities для каждой модели

### 6. Тестирование
- Добавлен `backend/test_planning_api.py` - полный тест
- Добавлен `backend/test_planning_api_simple.py` - упрощенный тест
- Тесты не создают планы автоматически (используют существующие)
- Защита от зацикливания в тестах

## Файлы изменены

Backend:
- backend/app/services/planning_service.py (новый)
- backend/app/api/routes/plans.py (новый)
- backend/app/models/plan.py
- backend/app/core/ollama_client.py
- backend/main.py
- backend/scripts/setup_main_models.py (новый)

Тесты:
- backend/test_planning_api.py (новый)
- backend/test_planning_api_simple.py (новый)

Документация:
- PLANNING_SYSTEM_PLAN.md (новый)
- PLANNING_SYSTEM_STATUS.md (новый)
- PLANNING_API_TEST_RESULTS.md (новый)
- PLANNING_TEST_SAFETY.md (новый)
- PLANNING_SYSTEM_COMPLETE.md (новый)
- CURRENT_STATUS.md (новый)
- NEXT_STEPS.md (обновлен)

## Результаты тестирования

✅ Оба теста пройдены успешно
✅ Генерация планов работает с приемлемым временем
✅ Защита от зацикливания работает корректно
✅ Таймауты настроены правильно

## TODO для будущего

- Веб-интерфейс для планов (список, детали, создание, визуализация)
- Интеграция с системой утверждений
- Интеграция с генератором артефактов
- Мониторинг выполнения планов
```

