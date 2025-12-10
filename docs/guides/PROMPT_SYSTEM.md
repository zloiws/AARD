# Система управления промптами

## Обзор

Система управления промптами (Prompt Management System) - это комплексное решение для управления, версионирования, отслеживания производительности и автоматического улучшения промптов, используемых в различных сервисах AARD.

## Архитектура

### Основные компоненты

1. **PromptService** (`backend/app/services/prompt_service.py`)
   - Управление промптами (CRUD операции)
   - Версионирование
   - Сбор метрик
   - Анализ производительности
   - Генерация рекомендаций
   - Создание улучшенных версий

2. **Модель Prompt** (`backend/app/models/prompt.py`)
   - Хранение промптов в БД
   - Метрики: success_rate, avg_execution_time, usage_count
   - История улучшений (improvement_history)

3. **PromptManager** (`backend/app/core/prompt_manager.py`)
   - Менеджер промптов для оркестратора
   - Автоматическое получение промптов для этапов
   - Отслеживание использования и запись метрик
   - Автоматический анализ и улучшение
   - A/B тестирование версий

4. **Интеграция с сервисами**
   - RequestOrchestrator: использует PromptManager для получения промптов
   - PlanningService: использует промпты для анализа и декомпозиции задач
   - ExecutionService: использует промпты для выполнения
   - ReflectionService: анализирует производительность промптов

## Функциональность

### 1. Базовое управление

- Создание, чтение, обновление, удаление промптов
- Версионирование через `parent_prompt_id`
- Фильтрация по типу, статусу, уровню, имени
- Fallback механизм на хардкод если промпт не найден

### 2. Метрики производительности

- **usage_count**: количество использований
- **avg_execution_time**: среднее время выполнения (экспоненциальное скользящее среднее)
- **success_rate**: процент успешности (скользящее окно последних 100 результатов)
- **user_rating**: пользовательская оценка

### 3. Рефлексия и улучшение

- Автоматический анализ производительности через ReflectionService
- Генерация рекомендаций на основе метрик и истории
- Автоматическое создание улучшенных версий с использованием LLM
- Автоматический триггер при низких метриках

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
    level=0
)
```

### Получение активного промпта

```python
prompt = service.get_active_prompt(
    name="task_analysis",
    prompt_type=PromptType.SYSTEM
)
```

### Отслеживание метрик

```python
# При использовании промпта
service.record_usage(prompt.id, execution_time_ms=1500.0)

# При успешном выполнении
service.record_success(prompt.id)

# При неудаче
service.record_failure(prompt.id)
```

### Анализ и улучшение

```python
# Анализ производительности
analysis = await service.analyze_prompt_performance(
    prompt_id=prompt.id,
    task_description="Task description",
    result=result,
    success=True,
    execution_metadata={"duration_ms": 1500}
)

# Генерация рекомендаций
suggestions = await service.suggest_improvements(prompt.id)

# Создание улучшенной версии
improved = await service.create_improved_version(
    prompt_id=prompt.id,
    suggestions=suggestions["suggestions"]
)

# Автоматическое создание при необходимости
improved = await service.auto_create_improved_version_if_needed(
    prompt_id=prompt.id,
    success_rate_threshold=0.5,
    execution_time_threshold_ms=10000.0
)
```

## API Endpoints

### Управление промптами

- `GET /api/prompts/` - список промптов
- `GET /api/prompts/{prompt_id}` - детали промпта
- `POST /api/prompts/` - создание промпта
- `PUT /api/prompts/{prompt_id}` - обновление
- `POST /api/prompts/{prompt_id}/version` - создание версии
- `POST /api/prompts/{prompt_id}/deprecate` - отключение
- `GET /api/prompts/{prompt_id}/versions` - список версий

### Метрики

- `GET /api/prompts/{prompt_id}/metrics` - метрики промпта
- `GET /api/prompts/metrics/comparison` - сравнение версий

## Полный цикл улучшения

1. **Использование**: Промпт используется в PlanningService
2. **Сбор метрик**: Автоматически собираются usage_count, execution_time
3. **Отслеживание успешности**: record_success/record_failure обновляют success_rate
4. **Анализ**: analyze_prompt_performance анализирует результаты через ReflectionService
5. **Рекомендации**: suggest_improvements генерирует предложения по улучшению
6. **Создание версии**: create_improved_version создает новую версию со статусом TESTING
7. **A/B тестирование**: (в следующей фазе) сравнение метрик версий

## Статусы промптов

- **ACTIVE**: Активный промпт, используется по умолчанию
- **TESTING**: Тестовая версия, используется для A/B тестирования
- **DEPRECATED**: Устаревший промпт, не используется

## Версионирование

Промпты поддерживают версионирование:
- При создании новой версии автоматически увеличивается номер версии
- Версии связываются через `parent_prompt_id`
- Можно получить все версии промпта через `get_prompt_versions()`
- Последняя версия получается через `get_latest_version()`

## Best Practices

1. **Использование именованных промптов**: Всегда используйте осмысленные имена
2. **Fallback механизм**: Всегда предусматривайте fallback на хардкод
3. **Версионирование**: При значительных изменениях создавайте новую версию
4. **Статусы**: Используйте TESTING для новых версий перед активацией
5. **Метрики**: Регулярно проверяйте метрики и создавайте улучшенные версии
6. **A/B тестирование**: Тестируйте новые версии перед активацией

## Тестирование

### Unit тесты

- `backend/tests/test_prompt_service.py` - базовые методы
- `backend/tests/test_prompt_metrics.py` - метрики
- `backend/tests/test_prompt_success_rate.py` - success_rate
- `backend/tests/test_prompt_reflection.py` - рефлексия
- `backend/tests/test_prompt_improvement_suggestions.py` - рекомендации
- `backend/tests/test_prompt_version_creation.py` - создание версий

### Интеграционные тесты

- `backend/tests/integration/test_prompt_service_integration.py` - интеграция с БД
- `backend/tests/integration/test_planning_with_prompts.py` - интеграция с PlanningService
- `backend/tests/integration/test_prompt_improvement_cycle.py` - полный цикл улучшения

## Следующие шаги

- A/B тестирование версий промптов
- Автоматическое продвижение лучших версий в статус ACTIVE
- Интеграция в другие сервисы (ExecutionService, ApprovalService)
- Визуализация метрик и трендов
- Уведомления о необходимости улучшения

