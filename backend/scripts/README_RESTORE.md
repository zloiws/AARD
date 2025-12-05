# Скрипты восстановления базы данных

## Проблема

После очистки базы данных (`clear_database.py`) все таблицы и данные удаляются, но структура таблиц и начальные данные должны быть восстановлены.

## Решение

### Автоматическое восстановление

Скрипт `clear_database.py` автоматически вызывает `restore_after_clear.py` после очистки, который восстанавливает:

1. **Все таблицы** (если отсутствуют) - через `Base.metadata.create_all()`
2. **Ollama серверы** - из `.env` конфигурации
3. **Начальные промпты** - для PlanningService (task_analysis, task_decomposition, task_replan)

### Ручное восстановление

Если нужно восстановить БД вручную:

```bash
# Полное восстановление (таблицы + серверы + промпты)
python backend/scripts/restore_after_clear.py

# Только серверы
python backend/scripts/restore_servers.py

# Только таблицы
python backend/create_all_tables.py
```

## Скрипты

### `clear_database.py`
Очищает все данные из БД (кроме `alembic_version`) и автоматически восстанавливает структуру.

**Использование:**
```bash
# С подтверждением
python backend/scripts/clear_database.py

# Без подтверждения
python backend/scripts/clear_database.py --yes
```

### `restore_after_clear.py`
Полное восстановление после очистки:
- Проверяет и создает отсутствующие таблицы
- Восстанавливает Ollama серверы из `.env`
- Создает начальные промпты для PlanningService

**Использование:**
```bash
python backend/scripts/restore_after_clear.py
```

### `restore_servers.py`
Восстанавливает только Ollama серверы из `.env` конфигурации.

**Использование:**
```bash
python backend/scripts/restore_servers.py
```

### `clear_and_restore.py`
Очищает БД и восстанавливает серверы (старый скрипт, используйте `clear_database.py`).

## Что восстанавливается

### Таблицы
Все таблицы из моделей SQLAlchemy (34 таблицы):
- tasks, plans, artifacts, approval_requests
- ollama_servers, ollama_models, prompts
- agents, tools, checkpoints, traces
- и другие...

### Ollama серверы
Из `.env` конфигурации:
- `OLLAMA_URL_1` → Server 1 - General/Reasoning
- `OLLAMA_URL_2` → Server 2 - Coding

### Начальные промпты
Для PlanningService:
- `task_analysis` - анализ задач
- `task_decomposition` - декомпозиция задач
- `task_replan` - перепланирование

## Рекомендации

1. **После очистки БД** всегда запускайте `restore_after_clear.py`
2. **Перед очисткой** убедитесь, что `.env` настроен правильно
3. **После восстановления** проверьте, что серверы активны и модели синхронизированы

