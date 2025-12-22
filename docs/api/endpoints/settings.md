# Settings API Endpoints

API для управления настройками системы.

## GET /api/settings/

Получить список всех настроек.

### Query Parameters

- `category` (string, optional): Фильтр по категории
- `module` (string, optional): Фильтр по модулю
- `active_only` (boolean, optional): Только активные настройки. По умолчанию: true

---

## GET /api/settings/{key}

Получить настройку по ключу.

---

## POST /api/settings/

Создать или обновить настройку.

### Request Body

```json
{
  "key": "app.max_concurrent_tasks",
  "value": "10",
  "value_type": "integer",
  "category": "performance",
  "module": "execution",
  "description": "Максимальное количество одновременных задач"
}
```

---

## DELETE /api/settings/{key}

Удалить настройку.

---

## GET /api/settings/features/all

Получить все feature flags.

---

## GET /api/settings/features/{feature}

Получить значение feature flag.

---

## POST /api/settings/features/

Установить feature flag.

---

## GET /api/settings/logging/all

Получить все настройки логирования.

---

## GET /api/settings/logging/{module}

Получить уровень логирования для модуля.

---

## POST /api/settings/logging/

Установить уровень логирования.

---

## GET /api/settings/modules/all

Получить список всех модулей.

