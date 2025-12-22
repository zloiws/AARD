# Анализ проблемы с отсутствующими таблицами

## Проблема

В базе данных отсутствовало 20+ таблиц, хотя версия миграции показывала `019_add_chat_sessions`.

## Причина

**Миграции не были применены правильно.** 

### Что произошло:

1. **В миграциях определены 33 таблицы:**
   - `001_initial_tables.py` - tasks, artifacts, artifact_dependencies
   - `002_ollama_servers_models.py` - ollama_servers, ollama_models
   - `003_evolution_system.py` - plans, approval_requests, evolution_history, feedback, prompts
   - `005_add_execution_traces.py` - execution_traces
   - `006_add_request_logs.py` - request_logs, request_consequences
   - `007_add_task_queues.py` - task_queues, queue_tasks
   - `008_add_checkpoints.py` - checkpoints
   - `009_add_agents.py` - agents
   - `010_add_tools.py` - tools
   - `012_add_agent_experiments.py` - agent_experiments, experiment_results
   - `013_add_agent_gym.py` - agent_tests, agent_test_runs, agent_benchmarks, agent_benchmark_runs
   - `014_add_agent_memory.py` - agent_memories, memory_entries, memory_associations
   - `015_add_authentication.py` - users, sessions
   - `016_add_learning_patterns.py` - learning_patterns
   - `019_add_chat_sessions.py` - chat_sessions, chat_messages
   - `020_add_workflow_events.py` - workflow_events

2. **В моделях определены те же 33 таблицы** - соответствие 100%

3. **В БД было только 3 таблицы:**
   - `agents` (создана вручную через create_agents_table.py)
   - `tools` (непонятно откуда)
   - `alembic_version` (версия миграции)

4. **Версия миграции показывала `019`**, но таблицы не были созданы

## Вывод

**Миграции не были применены**, хотя версия в `alembic_version` была обновлена. Возможные причины:

1. Миграции были применены частично, но потом таблицы были удалены
2. Версия была обновлена вручную без применения миграций
3. Миграции были применены с ошибками, которые были проигнорированы
4. База данных была пересоздана, но миграции не были применены заново

## Решение

Создали все таблицы через `create_all_tables.py`, который использует `Base.metadata.create_all()` из SQLAlchemy. Это создало все таблицы напрямую из моделей, минуя миграции.

## Проверка на дубликаты

✅ **Дубликатов нет** - все 34 таблицы уникальны:
- 33 таблицы из моделей/миграций
- 1 служебная таблица (alembic_version)

## Именование

✅ **Именование согласовано** - нет расхождений:
- Модели используют те же имена таблиц, что и миграции
- Нет старых/новых имен (например, `traces` всегда было `execution_traces`)

## Рекомендации

1. **Проверить историю миграций** - возможно, миграции были откачены или применены неправильно
2. **Синхронизировать версию миграции** - обновить `alembic_version` до актуальной версии
3. **В будущем** - применять миграции через `alembic upgrade head` перед запуском приложения

