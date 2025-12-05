# Управление промптами

## Обзор

Система управления промптами (Prompt Management System) позволяет хранить, версионировать и отслеживать производительность промптов, используемых в различных сервисах AARD.

## Основные компоненты

### PromptService

Сервис для управления промптами с поддержкой версионирования и метрик.

**Расположение:** `backend/app/services/prompt_service.py`

**Основные методы:**

- `create_prompt()` - создание нового промпта
- `get_prompt()` - получение промпта по ID
- `get_active_prompt()` - получение активного промпта по имени/типу/уровню
- `list_prompts()` - список промптов с фильтрацией
- `update_prompt()` - обновление промпта
- `create_version()` - создание новой версии промпта
- `deprecate_prompt()` - отключение промпта
- `get_prompt_versions()` - получение всех версий промпта
- `get_latest_version()` - получение последней версии по имени

### Модель Prompt

**Расположение:** `backend/app/models/prompt.py`

**Поля:**
- `id` - UUID промпта
- `name` - имя промпта
- `prompt_text` - текст промпта
- `prompt_type` - тип (SYSTEM, AGENT, TOOL, META, CONTEXT)
- `level` - уровень (0-4)
- `version` - версия
- `parent_prompt_id` - ID родительского промпта (для версий)
- `status` - статус (ACTIVE, DEPRECATED, TESTING)
- `success_rate` - процент успешности
- `avg_execution_time` - среднее время выполнения
- `usage_count` - количество использований
- `improvement_history` - история улучшений (JSON)

## Использование

### Создание промпта

```python
from app.services.prompt_service import PromptService
from app.models.prompt import PromptType

service = PromptService(db)

prompt = service.create_prompt(
    name="task_analysis",
    prompt_text="You are an expert at task analysis...",
    prompt_type=PromptType.SYSTEM,
    level=0,
    created_by="user123"
)
```

### Получение активного промпта

```python
# Получить активный промпт по имени и типу
prompt = service.get_active_prompt(
    name="task_analysis",
    prompt_type=PromptType.SYSTEM
)

if prompt:
    prompt_text = prompt.prompt_text
else:
    # Fallback на хардкод
    prompt_text = default_prompt
```

### Создание версии

```python
# Создать новую версию существующего промпта
new_version = service.create_version(
    parent_prompt_id=prompt.id,
    prompt_text="Improved prompt text...",
    created_by="user123"
)
```

### Версионирование

Промпты поддерживают версионирование через `parent_prompt_id`. При создании новой версии:
- Автоматически увеличивается номер версии
- Связывается с родительским промптом
- Может иметь статус TESTING для A/B тестирования

## Интеграция с сервисами

### PlanningService

PlanningService использует промпты для:
- Анализа задач (`_analyze_task`)
- Декомпозиции задач (`_decompose_task`)
- Перепланирования (`replan`)

**Пример интеграции:**

```python
class PlanningService:
    def __init__(self, db: Session):
        self.db = db
        self.prompt_service = PromptService(db)
    
    def _get_analysis_prompt(self) -> str:
        """Get prompt for task analysis"""
        prompt = self.prompt_service.get_active_prompt(
            name="task_analysis",
            prompt_type=PromptType.SYSTEM
        )
        
        if prompt:
            return prompt.prompt_text
        
        # Fallback to hardcoded prompt
        return DEFAULT_ANALYSIS_PROMPT
```

## API Endpoints

### GET /api/prompts/

Список промптов с фильтрацией.

**Query параметры:**
- `prompt_type` - фильтр по типу
- `status` - фильтр по статусу
- `level` - фильтр по уровню
- `name` - поиск по имени (частичное совпадение)
- `limit` - лимит результатов (по умолчанию 50)
- `offset` - смещение для пагинации

### GET /api/prompts/{prompt_id}

Получение промпта по ID.

### POST /api/prompts/

Создание нового промпта.

**Body:**
```json
{
  "name": "task_analysis",
  "prompt_text": "You are an expert...",
  "prompt_type": "system",
  "level": 0
}
```

### PUT /api/prompts/{prompt_id}

Обновление промпта.

### POST /api/prompts/{prompt_id}/version

Создание новой версии промпта.

**Body:**
```json
{
  "prompt_text": "Improved prompt text..."
}
```

### POST /api/prompts/{prompt_id}/deprecate

Отключение промпта (изменение статуса на DEPRECATED).

### GET /api/prompts/{prompt_id}/versions

Получение всех версий промпта.

## Тестирование

### Unit тесты

**Файл:** `backend/tests/test_prompt_service.py`

Тесты всех методов PromptService.

### Интеграционные тесты

**Файл:** `backend/tests/integration/test_prompt_service_integration.py`

Тесты с реальной базой данных, включая:
- Полный жизненный цикл промпта
- Версионирование
- Фильтрация и поиск

## Best Practices

1. **Использование именованных промптов**: Всегда используйте осмысленные имена для промптов (например, `task_analysis`, `task_decomposition`)

2. **Fallback механизм**: Всегда предусматривайте fallback на хардкод, если промпт не найден в БД

3. **Версионирование**: При значительных изменениях создавайте новую версию вместо обновления существующей

4. **Статусы**: Используйте статус TESTING для новых версий перед активацией

5. **Логирование**: Всегда логируйте использование промптов для отслеживания метрик

## Реализовано (Этап 1.1)

- ✅ PromptService с базовыми методами управления
- ✅ Интеграция PromptService в PlanningService
- ✅ API endpoints для управления промптами
- ✅ Версионирование промптов
- ✅ Fallback механизм на хардкод
- ✅ Сохранение используемых промптов в Digital Twin context

## Следующие шаги

- [ ] Интеграция метрик использования (Шаг 1.2.1)
- [ ] Расчет success_rate (Шаг 1.2.2)
- [ ] API для метрик (Шаг 1.2.3)
- [ ] Интеграция с ReflectionService (Шаг 1.3.1)
- [ ] Автоматические рекомендации по улучшению (Шаг 1.3.2)
- [ ] Автоматическое создание улучшенных версий (Шаг 1.3.3)

