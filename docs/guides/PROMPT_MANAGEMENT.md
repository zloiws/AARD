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

## Интеграция с RequestOrchestrator

### PromptManager

**Расположение:** `backend/app/core/prompt_manager.py`

**Функционал:**
- Управление жизненным циклом промптов в рамках запроса
- Получение активных промптов для каждого этапа (planning, execution, reflection)
- Отслеживание использования промптов
- Автоматическая запись метрик через PromptService
- Автоматический анализ производительности
- Автоматическое создание улучшенных версий при низкой производительности
- A/B тестирование версий (использование TESTING версий параллельно с ACTIVE)

**Использование:**
```python
from app.core.prompt_manager import PromptManager
from app.core.execution_context import ExecutionContext

context = ExecutionContext.from_db_session(db)
prompt_manager = PromptManager(context)
context.set_prompt_manager(prompt_manager)

# Получить промпт для этапа
prompt = await prompt_manager.get_prompt_for_stage("planning")

# Записать использование
await prompt_manager.record_prompt_usage(
    prompt_id=prompt.id,
    success=True,
    execution_time_ms=100.0,
    stage="planning"
)

# Анализировать и улучшить промпты
results = await prompt_manager.analyze_and_improve_prompts()
```

**Автоматическое улучшение:**
- После каждого использования промпта записываются метрики
- После завершения запроса автоматически анализируется производительность
- Если success_rate < 0.5 или execution_time > 10000ms, создается улучшенная версия
- Улучшенные версии получают статус TESTING и тестируются параллельно с ACTIVE

**A/B тестирование:**
- По умолчанию 10% запросов используют TESTING версии
- Метрики сравниваются автоматически
- При лучших показателях TESTING версия может быть переведена в ACTIVE

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

## Реализовано

### Этап 1.1: Базовое управление
- ✅ PromptService с базовыми методами управления
- ✅ Интеграция PromptService в PlanningService
- ✅ API endpoints для управления промптами
- ✅ Версионирование промптов
- ✅ Fallback механизм на хардкод
- ✅ Сохранение используемых промптов в Digital Twin context

### Этап 1.2: Метрики производительности
- ✅ Сбор метрик использования (usage_count, avg_execution_time)
- ✅ Расчет success_rate на основе скользящего окна (последние 100 результатов)
- ✅ API endpoints для просмотра метрик и сравнения версий
- ✅ Интеграция отслеживания успешности в PlanningService

## Метрики

### Отслеживаемые метрики

1. **usage_count** - количество использований промпта
2. **avg_execution_time** - среднее время выполнения (в миллисекундах)
3. **success_rate** - процент успешности (0.0 - 1.0)
4. **user_rating** - пользовательская оценка (0.0 - 1.0)

### Расчет метрик

- **avg_execution_time**: Используется экспоненциальное скользящее среднее (alpha=0.1)
- **success_rate**: Рассчитывается на основе скользящего окна последних 100 использований

### API для метрик

#### GET /api/prompts/{prompt_id}/metrics

Возвращает метрики конкретного промпта:
```json
{
  "prompt_id": "...",
  "prompt_name": "task_analysis",
  "version": 1,
  "usage_count": 42,
  "success_rate": 0.85,
  "avg_execution_time": 1250.5,
  "user_rating": null,
  "usage_history": [...],
  "total_history_entries": 50
}
```

#### GET /api/prompts/metrics/comparison

Сравнение метрик разных версий промпта:
- Query параметры: `prompt_name` или `parent_prompt_id`
- Возвращает сравнение всех версий одного промпта

### Этап 1.3: Рефлексия и улучшение промптов
- ✅ Интеграция ReflectionService для анализа производительности промптов
- ✅ Автоматические рекомендации по улучшению на основе метрик и истории
- ✅ Автоматическое создание улучшенных версий с использованием LLM
- ✅ Автоматический триггер создания версий при низких метриках

## Рефлексия и улучшение

### Анализ производительности

Метод `analyze_prompt_performance()` использует ReflectionService для анализа результатов использования промпта:

- **Для успешных использований**: генерирует предложения по улучшению
- **Для неудачных использований**: анализирует причины неудач и предлагает исправления

Результаты анализа сохраняются в `improvement_history`.

### Автоматические рекомендации

Метод `suggest_improvements()` генерирует рекомендации на основе:

1. **Анализа метрик**:
   - Низкий success_rate (< 0.5) → высокий приоритет
   - Высокое время выполнения (> 10s) → средний приоритет
   - Низкое использование (< 10) → низкий приоритет

2. **Анализа истории**:
   - Паттерны ошибок
   - Частые типы ошибок
   - Тренды производительности

3. **LLM-анализа**:
   - Использует планирующую модель для генерации конкретных рекомендаций
   - Анализирует промпт в контексте метрик и истории

### Автоматическое создание улучшенных версий

Метод `create_improved_version()`:
- Принимает рекомендации по улучшению
- Использует LLM для генерации улучшенной версии промпта
- Создает новую версию со статусом `TESTING`
- Связывает с родительским промптом через `parent_prompt_id`

Метод `auto_create_improved_version_if_needed()` автоматически создает улучшенную версию когда:
- `success_rate < threshold` (по умолчанию 0.5)
- `avg_execution_time > threshold` (по умолчанию 10000ms)

## Полный цикл улучшения

1. **Использование** → сбор метрик (usage_count, avg_execution_time, success_rate)
2. **Анализ** → ReflectionService анализирует результаты
3. **Рекомендации** → генерация предложений по улучшению
4. **Создание версии** → автоматическое создание улучшенной версии со статусом TESTING
5. **A/B тестирование** → сравнение метрик версий (в следующей фазе)

## Следующие шаги

- [ ] A/B тестирование версий промптов
- [ ] Автоматическое продвижение лучших версий в статус ACTIVE
- [ ] Интеграция улучшения промптов в другие сервисы (ExecutionService, ApprovalService)

