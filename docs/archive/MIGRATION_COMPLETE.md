# Миграция Ollama серверов в БД - Завершено

## Выполнено

### ✅ 1. Применена миграция

Миграция `002_ollama_servers_models.py` успешно применена:
- Создана таблица `ollama_servers`
- Создана таблица `ollama_models`
- Созданы все необходимые индексы

### ✅ 2. Добавлены серверы в БД

Из `.env` конфигурации добавлены два сервера:

1. **Server 1 - General/Reasoning**
   - URL: `http://10.39.0.101:11434`
   - API Version: `v1`
   - Capabilities: `["general", "reasoning", "conversation"]`
   - Max Concurrent: `2`
   - Priority: `1`
   - Is Default: `True`
   - Description: Default server from .env configuration

2. **Server 2 - Coding**
   - URL: `http://10.39.0.6:11434`
   - API Version: `v1`
   - Capabilities: `["coding", "code_generation"]`
   - Max Concurrent: `1`
   - Priority: `0`
   - Is Default: `False`
   - Description: Secondary server from .env configuration

## Следующие шаги

### 1. Обнаружить модели на серверах

Используйте API для обнаружения моделей:

```bash
# Для сервера 1 (нужно узнать ID сервера)
curl -X POST http://localhost:8000/api/servers/{server_id}/discover

# Или через Swagger UI
# Откройте http://localhost:8000/docs и используйте POST /api/servers/{server_id}/discover
```

### 2. Проверить список серверов

```bash
curl http://localhost:8000/api/servers
```

### 3. Управление серверами

Теперь все серверы хранятся в БД и доступны через API:
- `GET /api/servers` - список серверов
- `POST /api/servers` - создать новый сервер
- `GET /api/servers/{id}` - получить сервер
- `PUT /api/servers/{id}` - обновить сервер
- `DELETE /api/servers/{id}` - удалить сервер
- `POST /api/servers/{id}/discover` - обнаружить модели
- `GET /api/servers/{id}/models` - список моделей сервера

## Важно

- Конфигурация серверов теперь хранится в БД, а не в `.env`
- При указании `server_url` и `model` в запросе, используется именно запрошенная модель, без fallback на конфигурацию
- Можно динамически добавлять новые серверы через API
- Поддерживается авторизация (поля `auth_type` и `auth_config` в БД)

