# Сообщение для коммита

```
feat: Улучшения интерфейса, логирования и управления моделями

## Основные изменения

### 1. Система логирования
- Добавлен модуль `backend/app/core/logging_config.py` для централизованного управления логированием
- Отключено логирование SQLAlchemy по умолчанию (контролируется через LOG_SQLALCHEMY)
- Отключено логирование Uvicorn access logs по умолчанию
- Настройка уровней логирования для отдельных модулей через LOG_MODULE_LEVELS

### 2. Улучшения интерфейса
- Добавлена поддержка Markdown и подсветки синтаксиса (marked.js + highlight.js)
- Исправлена кнопка остановки генерации ответа от модели
- Устранено дублирование переменных в JavaScript
- Улучшена обработка ошибок в чате

### 3. Управление моделями
- Добавлен endpoint `POST /api/models/{model_id}/unload` для выгрузки модели
- Добавлен endpoint `POST /api/models/{model_id}/unload-from-gpu` (заглушка с TODO)
- Добавлена кнопка "Выгрузить" в настройках для каждой модели
- Улучшена обработка ошибок при работе с моделями

### 4. Исправления
- Исправлена ошибка с `request_base_url` в `ollama_client.py`
- Исправлено дублирование запросов (убраны HTMX атрибуты из формы)
- Исправлено логирование SQLAlchemy (отключен echo, настроен logger)

## Файлы изменены

Backend:
- backend/app/core/logging_config.py (новый)
- backend/app/core/database.py
- backend/app/core/config.py
- backend/app/core/ollama_client.py
- backend/app/api/routes/chat.py
- backend/app/api/routes/models_management.py
- backend/main.py

Frontend:
- frontend/templates/main.html
- frontend/templates/base.html
- frontend/templates/message_fragment.html
- frontend/templates/settings/index.html

Документация:
- LOGGING_AND_MARKDOWN_SETUP.md (новый)
- TODO_MODEL_MANAGEMENT.md (новый)
- FEATURES_IMPLEMENTATION_SUMMARY.md (новый)
- DEVELOPMENT_ROADMAP.md (новый)
- QUICK_FIX_INTERFACE.md (новый)

## TODO для будущего

- Правильное чтение состояния модели (загружена или нет в GPU)
- Правильная выгрузка модели из GPU (требует исследования Ollama API)
- Динамическая замена модели при переключении
- См. TODO_MODEL_MANAGEMENT.md для деталей
```

