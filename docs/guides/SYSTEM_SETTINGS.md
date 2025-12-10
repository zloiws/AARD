# Система управления настройками (System Settings)

## Обзор

Централизованная система управления настройками приложения через БД, позволяющая динамически изменять feature flags, уровни логирования и другие параметры без перезапуска приложения.

## Архитектура

### Модель данных

**SystemSetting** (`backend/app/models/system_setting.py`):
- `key` - уникальный ключ настройки
- `value` - значение (хранится как текст)
- `value_type` - тип значения (boolean, string, integer, float, json)
- `category` - категория (feature, logging, module, system)
- `module` - модуль (для модульных настроек)
- `description` - описание
- `is_active` - активность настройки
- `updated_by` - кто обновил

### Сервис

**SystemSettingService** (`backend/app/services/system_setting_service.py`):
- `get_setting(key, default)` - получить настройку
- `set_setting(key, value, category, ...)` - установить настройку
- `get_feature_flag(feature)` - получить feature flag
- `set_feature_flag(feature, enabled)` - установить feature flag
- `get_log_level(module)` - получить уровень логирования
- `set_log_level(level, module)` - установить уровень логирования
- `get_all_settings(category, module)` - получить все настройки
- `get_all_feature_flags()` - получить все feature flags
- `get_all_log_levels()` - получить все уровни логирования

### API Endpoints

**`/api/settings`**:
- `GET /` - список всех настроек
- `GET /{key}` - получить настройку по ключу
- `POST /` - создать/обновить настройку
- `DELETE /{key}` - удалить настройку

**Feature Flags**:
- `GET /features/all` - все feature flags
- `GET /features/{feature}` - конкретный flag
- `POST /features/` - установить flag

**Logging**:
- `GET /logging/all` - все уровни логирования
- `GET /logging/{module}` - уровень для модуля
- `POST /logging/` - установить уровень

**Modules**:
- `GET /modules/all` - список всех модулей с настройками

### UI

**`/settings`** - веб-интерфейс управления настройками:
- Вкладка "Feature Flags" - переключатели для включения/выключения функций
- Вкладка "Logging Levels" - выбор уровней логирования (глобально и по модулям)
- Вкладка "Module Settings" - просмотр всех настроек по категориям

## Использование

### 1. Миграция из .env

Перенести существующие настройки из `.env` в БД:

```bash
cd backend
python scripts/migrate_env_to_db.py
```

Это создаст настройки для:
- Feature flags: `agent_ops`, `a2a`, `planning`, `tracing`, `caching`
- Logging: глобальный уровень и уровни для основных модулей
- System: таймауты, лимиты и т.д.

### 2. Использование в коде

```python
from app.services.system_setting_service import SystemSettingService
from app.core.database import get_db

db = get_db()
service = SystemSettingService(db)

# Feature flag
if service.get_feature_flag('planning'):
    # Planning feature enabled
    pass

# Log level
log_level = service.get_log_level('app.services.planning_service')

# Custom setting
timeout = service.get_setting('system.llm.timeout_seconds', default=30)
```

### 3. Управление через API

```bash
# Получить все feature flags
curl http://localhost:8000/api/settings/features/all

# Включить feature
curl -X POST http://localhost:8000/api/settings/features/ \
  -H "Content-Type: application/json" \
  -d '{"feature": "planning", "enabled": true}'

# Установить уровень логирования
curl -X POST http://localhost:8000/api/settings/logging/ \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG", "module": "app.services.planning_service"}'
```

### 4. Управление через UI

Откройте `http://localhost:8000/settings` для визуального управления настройками.

## Структура ключей

### Feature Flags
```
feature.{feature_name}.enabled
```

Примеры:
- `feature.agent_ops.enabled`
- `feature.planning.enabled`
- `feature.a2a.enabled`
- `feature.tracing.enabled`
- `feature.caching.enabled`

### Logging Levels
```
logging.global.level              # Глобальный уровень
logging.module.{module_name}.level  # Уровень для модуля
```

Примеры:
- `logging.global.level` = "WARNING"
- `logging.module.app.api.routes.chat.level` = "INFO"
- `logging.module.app.services.planning_service.level` = "DEBUG"
- `logging.module.app.core.ollama_client.level` = "WARNING"

### System Settings
```
system.{component}.{parameter}
```

Примеры:
- `system.llm.timeout_seconds`
- `system.llm.max_tokens`
- `system.planning.max_steps`
- `system.execution.timeout_seconds`

## Модули с настройками

### API Routes
- `app.api.routes.chat`
- `app.api.routes.agents`
- `app.api.routes.plans`
- `app.api.routes.benchmarks`
- `app.api.routes.agent_dialogs`

### Services
- `app.services.planning_service`
- `app.services.execution_service`
- `app.services.agent_dialog_service`
- `app.services.agent_service`
- `app.services.tool_service`
- `app.services.memory_service`
- `app.services.workflow_event_service`
- `app.services.reflection_service`

### Core
- `app.core.ollama_client`
- `app.core.request_router`
- `app.core.tracing`

## Преимущества

1. **Динамическое изменение** - настройки меняются без перезапуска
2. **Централизованное управление** - все настройки в одном месте
3. **Удобный UI** - визуальное управление через веб-интерфейс
4. **API** - программное управление настройками
5. **История изменений** - `updated_at` и `updated_by`
6. **Модульность** - настройки группируются по модулям
7. **Отладка** - можно включить DEBUG для конкретного модуля

## Миграция

### Таблица: `system_settings`

```sql
CREATE TABLE system_settings (
    id UUID PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    value_type VARCHAR(20) NOT NULL DEFAULT 'string',
    category VARCHAR(50) NOT NULL,
    module VARCHAR(100),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(255)
);

CREATE INDEX idx_system_settings_key ON system_settings(key);
CREATE INDEX idx_system_settings_category ON system_settings(category);
CREATE INDEX idx_system_settings_module ON system_settings(module);
CREATE INDEX idx_settings_category_active ON system_settings(category, is_active);
```

Миграция: `backend/alembic/versions/029_add_system_settings.py`

## Дополнительная документация

- [Справочник настроек](SETTINGS_REFERENCE.md) - полный список всех 33 настроек
- [Восстановление данных](DATA_RESTORATION.md) - восстановление после очистки БД

## Дальнейшее развитие

1. ✅ **Редактирование системных настроек** через UI
2. ✅ **Staged Changes** - накопление изменений перед применением
3. **Интеграция с LoggingConfig** - автоматическое применение уровней логирования
4. **Валидация значений** - проверка допустимых значений и диапазонов
5. **Группы настроек** - объединение связанных настроек
6. **Импорт/экспорт** - сохранение и восстановление конфигураций
7. **Версионирование** - история изменений настроек
8. **Роли и права** - ограничение доступа к критичным настройкам

