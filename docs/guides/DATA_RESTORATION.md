# Восстановление важных данных в БД

## Проблема

После очистки БД или при первом запуске могут отсутствовать важные начальные данные:
- Benchmark задачи (для тестирования моделей)
- Начальные промпты (для PlanningService)
- Серверы Ollama (если не были созданы)

## Решение

Использовать скрипт `backend/scripts/restore_initial_data.py` для автоматического восстановления всех важных данных.

### Запуск восстановления

```bash
cd backend
python scripts/restore_initial_data.py
```

### Что восстанавливается

1. **Benchmark задачи** (40 задач)
   - 10 задач code_generation
   - 5 задач code_analysis
   - 10 задач reasoning
   - 10 задач planning
   - 5 задач general_chat
   - Источник: `backend/data/benchmarks/*.json`

2. **Начальные промпты** (3 промпта)
   - `task_analysis` - анализ задач
   - `task_decomposition` - разбиение на шаги
   - `task_replan` - перепланирование

3. **Серверы Ollama**
   - Восстанавливаются из `.env` конфигурации
   - Используется `scripts/init_ollama_servers.py`

## Проверка данных

После восстановления можно проверить:

```python
from app.core.database import SessionLocal
from app.models.benchmark_task import BenchmarkTask
from app.models.prompt import Prompt
from app.models.ollama_server import OllamaServer

db = SessionLocal()
print(f"Benchmark задач: {db.query(BenchmarkTask).count()}")
print(f"Промптов: {db.query(Prompt).count()}")
print(f"Серверов: {db.query(OllamaServer).count()}")
db.close()
```

## Когда использовать

- После очистки БД
- При первом запуске проекта
- После миграций, которые могли удалить данные
- Если на странице `/benchmarks` нет тестов
- Если PlanningService не может найти промпты

## Важно

- Скрипт **не удаляет** существующие данные
- Если данные уже есть, они пропускаются
- БД не очищается - только добавляются недостающие данные

