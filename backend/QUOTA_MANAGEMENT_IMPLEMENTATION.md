# Реализация системы управления ресурсами и квотами

## ✅ Выполнено

### QuotaManagementService
**Файл:** `backend/app/services/quota_management_service.py`

**Функциональность:**

#### 1. Типы ресурсов
- **LLM_REQUESTS** - Количество запросов к LLM
- **LLM_TOKENS** - Количество токенов
- **DATABASE_QUERIES** - Количество запросов к БД
- **FILE_OPERATIONS** - Количество файловых операций
- **NETWORK_REQUESTS** - Количество сетевых запросов
- **EXECUTION_TIME** - Время выполнения (секунды)
- **MEMORY_USAGE** - Использование памяти (MB)
- **STORAGE_SPACE** - Использование хранилища (MB)
- **CONCURRENT_TASKS** - Количество одновременных задач
- **AGENT_CREATIONS** - Количество созданий агентов
- **TOOL_CREATIONS** - Количество созданий инструментов

#### 2. Периоды квот
- **PER_REQUEST** - На один запрос
- **PER_MINUTE** - В минуту
- **PER_HOUR** - В час
- **PER_DAY** - В день
- **PER_WEEK** - В неделю
- **PER_MONTH** - В месяц
- **TOTAL** - Общий лимит (без временного периода)

#### 3. Статусы квот
- **WITHIN_LIMIT** - В пределах лимита
- **APPROACHING_LIMIT** - Приближается к лимиту (80-95%)
- **AT_LIMIT** - На лимите (95-100%)
- **EXCEEDED** - Превышен лимит
- **UNKNOWN** - Не удается определить статус

#### 4. Методы управления

##### `check_quota()`
- Проверяет, позволяет ли квота использование ресурса
- Возвращает детальную информацию о статусе квоты
- Поддерживает пользовательские и агент-специфичные квоты

##### `record_usage()`
- Записывает использование ресурса для отслеживания
- Поддерживает отслеживание по периодам
- Ведет статистику использования

##### `check_task_quota()`
- Проверяет квоты для всех ресурсов, требуемых задачей
- Оценивает ресурсы на основе описания задачи
- Возвращает результаты для всех ресурсов

##### `get_quota_status()`
- Получает текущий статус квоты для типа ресурса
- Показывает использование, лимит и оставшееся количество

##### `get_all_quotas_status()`
- Получает статус всех квот
- Полезно для мониторинга и отчетности

#### 5. Оценка ресурсов

##### `_estimate_task_resources()`
- Оценивает требования к ресурсам на основе описания задачи
- Использует ключевые слова для определения типа операций
- Возвращает оценки для всех типов ресурсов

## Интеграция

### Использование в ExecutionService

```python
from app.services.quota_management_service import QuotaManagementService, ResourceType

# Перед выполнением задачи
quota_service = QuotaManagementService(db)
quota_check = quota_service.check_task_quota(task)

if not quota_check["all_allowed"]:
    # Задача не может быть выполнена из-за квот
    return {"error": "Quota exceeded", "details": quota_check}

# Выполнить задачу
# ...

# После выполнения, записать использование
quota_service.record_usage(
    resource_type=ResourceType.LLM_REQUESTS,
    amount=actual_requests_used,
    user_id=task.created_by,
    task_id=task.id
)
```

### Использование в RequestOrchestrator

```python
# Перед обработкой запроса
quota_check = quota_service.check_quota(
    resource_type=ResourceType.LLM_REQUESTS,
    requested_amount=1.0,
    user_id=user_id
)

if not quota_check["allowed"]:
    return OrchestrationResult(
        response=f"Достигнут лимит запросов. {quota_check['message']}",
        metadata={"quota_exceeded": True}
    )
```

## Конфигурация квот

### Значения по умолчанию

```python
default_quotas = {
    ResourceType.LLM_REQUESTS: {
        "limit": 1000,
        "period": "per_day",
        "warning_threshold": 0.8
    },
    ResourceType.LLM_TOKENS: {
        "limit": 1000000,  # 1M tokens
        "period": "per_day",
        "warning_threshold": 0.8
    },
    # ... другие ресурсы
}
```

### Пользовательские квоты

Квоты могут быть настроены для конкретных пользователей или агентов через конфигурацию или базу данных.

## Примеры использования

### Проверка квоты перед выполнением

```python
quota_check = quota_service.check_quota(
    resource_type=ResourceType.LLM_REQUESTS,
    requested_amount=5.0,
    user_id="user123"
)

if quota_check["allowed"]:
    # Продолжить выполнение
    pass
else:
    # Отклонить запрос
    logger.warning(f"Quota exceeded: {quota_check['message']}")
```

### Получение статуса всех квот

```python
all_statuses = quota_service.get_all_quotas_status(user_id="user123")

for resource_type, status in all_statuses["quotas"].items():
    if status["status"] == "approaching_limit":
        # Отправить предупреждение пользователю
        send_notification(f"Quota for {resource_type} is approaching limit")
```

### Запись использования

```python
# После выполнения LLM запроса
quota_service.record_usage(
    resource_type=ResourceType.LLM_REQUESTS,
    amount=1.0,
    user_id="user123"
)

# После обработки токенов
quota_service.record_usage(
    resource_type=ResourceType.LLM_TOKENS,
    amount=1500.0,
    user_id="user123"
)
```

## Уведомления о лимитах

Система автоматически генерирует сообщения о статусе квот:
- **EXCEEDED**: "Quota exceeded for [Resource]. Limit: [limit], cannot proceed."
- **AT_LIMIT**: "Quota at limit for [Resource]. Remaining: [remaining]/[limit]"
- **APPROACHING_LIMIT**: "Quota approaching limit for [Resource]. Remaining: [remaining]/[limit]"
- **WITHIN_LIMIT**: "Quota OK for [Resource]. Remaining: [remaining]/[limit]"

## Следующие шаги (опционально)

1. ⏳ Интеграция в ExecutionService для проверки перед выполнением
2. ⏳ Интеграция в RequestOrchestrator для проверки перед обработкой
3. ⏳ Персистентное хранение использования в базе данных
4. ⏳ API endpoints для управления квотами
5. ⏳ Уведомления пользователям о приближении к лимитам
6. ⏳ Автоматическое масштабирование квот на основе использования
7. ⏳ Интеграция с системой биллинга

