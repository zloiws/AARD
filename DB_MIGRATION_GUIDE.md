# Руководство по миграции Ollama серверов в БД

## Проблема

Сейчас конфигурация Ollama серверов хранится в `.env`, и при выборе другого сервера/модели система всё равно использует модель из `.env`.

## Решение

Хранить конфигурацию Ollama серверов в БД PostgreSQL. Это позволяет динамически управлять серверами через API.

## Шаги миграции

### 1. Применить миграции

```bash
cd backend
python run_migration.py
```

Это создаст таблицы:
- `ollama_servers` - серверы Ollama
- `ollama_models` - модели на серверах

### 2. Создать серверы в БД

Можно через API или скрипт:

```python
# Скрипт для миграции из .env в БД
from app.core.database import SessionLocal
from app.models.ollama_server import OllamaServer

db = SessionLocal()

# Создать сервер 1
server1 = OllamaServer(
    name="Server 1 - General/Reasoning",
    url="http://10.39.0.101:11434",
    api_version="v1",
    capabilities=["general", "reasoning", "conversation"],
    max_concurrent=2,
    priority=1,
    is_default=True,
    is_active=True
)
db.add(server1)
db.commit()

# Создать сервер 2
server2 = OllamaServer(
    name="Server 2 - Coding",
    url="http://10.39.0.6:11434",
    api_version="v1",
    capabilities=["coding", "code_generation"],
    max_concurrent=1,
    priority=0,
    is_active=True
)
db.add(server2)
db.commit()

# Обнаружить модели на серверах
# POST /api/servers/{server_id}/discover
```

### 3. Изменить логику выбора моделей

Теперь при указанном `server_url` и `model`:
- Создается динамический instance с указанными параметрами
- НЕ используется fallback на конфигурацию из .env
- Используется именно запрошенная модель

## API для управления

- `GET /api/servers` - список серверов
- `POST /api/servers` - создать сервер
- `POST /api/servers/{id}/discover` - обнаружить модели на сервере
- `GET /api/servers/{id}/models` - список моделей сервера

## Важные изменения

1. **При указанном server_url и model:**
   - Сразу создается динамический instance
   - Используется именно запрошенная модель
   - Нет fallback на .env конфигурацию

2. **Авторизация:**
   - В таблице `ollama_servers` есть поля `auth_type` и `auth_config`
   - Поддерживаются: "none", "basic", "bearer", "api_key"

3. **Динамические серверы:**
   - Если сервер не в БД, но указан в запросе, создается временный instance
   - Это позволяет использовать серверы без предварительной регистрации

## Пример использования

```python
# Использование сервера из БД
response = await client.generate(
    prompt="Hello",
    model="qwen3-vl:8b",
    server_url="http://10.39.0.101:11434/v1"
)

# Используется именно qwen3-vl:8b, а не модель из .env
```

