# Реализация системы управления версиями артефактов

## ✅ Выполнено

### 1. Модель ArtifactVersion
**Файл:** `backend/app/models/artifact_version.py`

**Функциональность:**
- Хранит полный снимок артефакта на каждой версии
- Changelog для описания изменений
- Метрики производительности для сравнения
- Информация об откате (rolled_back_from_version, rollback_reason)
- Статус активности версии (is_active)
- Индексы для эффективных запросов

**Поля:**
- `artifact_id` - ID артефакта
- `version` - Номер версии
- `name`, `description`, `code`, `prompt`, `type` - Снимок данных артефакта
- `changelog` - Описание изменений
- `metrics` (JSONB) - Метрики производительности
- `test_results` (JSON) - Результаты тестирования
- `security_rating` - Рейтинг безопасности
- `is_active` - Активна ли версия
- `promoted_at`, `deprecated_at` - Временные метки
- `rolled_back_from_version`, `rollback_reason` - Информация об откате

### 2. Сервис ArtifactVersionService
**Файл:** `backend/app/services/artifact_version_service.py`

**Методы:**

#### `create_version()`
- Создает новую версию артефакта
- Деактивирует предыдущую активную версию
- Обновляет версию в основном артефакте
- Автоматически создает снимок всех данных

#### `get_version()`, `get_active_version()`, `get_all_versions()`
- Получение версий по различным критериям

#### `compare_versions()`
- Сравнение двух версий
- Анализ метрик (success_rate, avg_execution_time, error_rate, security_rating)
- Определение улучшений и деградаций

#### `should_rollback()`
- Проверка необходимости отката на основе деградации метрик
- Порог деградации (по умолчанию 15%)
- Возвращает (should_rollback: bool, reason: str)

#### `rollback_to_version()`
- Откат артефакта к предыдущей версии
- Восстановление данных из снимка
- Создание новой версии с пометкой об откате

#### `auto_rollback_if_degraded()`
- Автоматический откат при деградации метрик
- Использует `should_rollback()` для проверки
- Выполняет откат к предыдущей версии

### 3. Интеграция в ArtifactGenerator
**Файл:** `backend/app/services/artifact_generator.py`

**Изменения:**
- Добавлен `ArtifactVersionService` в конструктор
- При создании нового артефакта автоматически создается первая версия
- Changelog генерируется автоматически
- Инициализируются базовые метрики (success_rate, avg_execution_time, error_rate)

### 4. Обновление моделей
**Файл:** `backend/app/models/__init__.py`

- Добавлен импорт `ArtifactVersion`
- Добавлен в `__all__` для экспорта

## Использование

### Создание версии при обновлении артефакта

```python
from app.services.artifact_version_service import ArtifactVersionService

version_service = ArtifactVersionService(db)

# При обновлении артефакта
artifact.name = "New Name"
artifact.code = "Updated code"
# ... другие изменения

# Создать новую версию
version_service.create_version(
    artifact=artifact,
    changelog="Updated name and code",
    metrics={
        "success_rate": 0.95,
        "avg_execution_time": 1.2,
        "error_rate": 0.05
    },
    created_by="user@example.com"
)
```

### Автоматический откат при деградации

```python
# Проверить и откатить при необходимости
rolled_back = version_service.auto_rollback_if_degraded(
    artifact_id=artifact.id,
    threshold_percent=15.0  # 15% деградация
)

if rolled_back:
    print(f"Artifact rolled back due to metric degradation")
```

### Сравнение версий

```python
comparison = version_service.compare_versions(
    artifact_id=artifact.id,
    version1=1,
    version2=2
)

print(f"Improved: {comparison['improved']}")
print(f"Degraded: {comparison['degraded']}")
print(f"Metrics diff: {comparison['metrics_diff']}")
```

## Следующие шаги

1. ⏳ Интеграция версионирования при активации артефакта (в AgentService.activate_agent)
2. ⏳ Интеграция версионирования при обновлении артефакта
3. ⏳ Автоматический сбор метрик после выполнения артефакта
4. ⏳ Периодическая проверка метрик и автоматический откат
5. ⏳ API endpoints для управления версиями

## Миграция базы данных

Необходимо создать миграцию Alembic для таблицы `artifact_versions`:

```python
# alembic/versions/xxxx_add_artifact_versions.py
def upgrade():
    op.create_table(
        'artifact_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        # ... остальные поля
    )
    op.create_index('idx_artifact_version', 'artifact_versions', ['artifact_id', 'version'], unique=True)
    op.create_index('idx_artifact_active', 'artifact_versions', ['artifact_id', 'is_active'])
```

