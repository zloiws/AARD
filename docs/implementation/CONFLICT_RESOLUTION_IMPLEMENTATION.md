# Реализация системы разрешения конфликтов целей

## ✅ Выполнено

### ConflictResolutionService
**Файл:** `backend/app/services/conflict_resolution_service.py`

**Функциональность:**

#### 1. Типы конфликтов
- **RESOURCE_CONFLICT** - Множественные агенты требуют один ресурс
- **GOAL_CONFLICT** - Противоречивые цели/объективы
- **PRIORITY_CONFLICT** - Разные уровни приоритета
- **DEPENDENCY_CONFLICT** - Циклические или блокирующие зависимости
- **TIMING_CONFLICT** - Конфликты расписания

#### 2. Уровни серьезности
- **LOW** - Может быть разрешен автоматически
- **MEDIUM** - Может потребовать вмешательства человека
- **HIGH** - Требует немедленного внимания
- **CRITICAL** - Система не может продолжить без разрешения

#### 3. Стратегии разрешения
- **PRIORITY_BASED** - Разрешение на основе приоритета задачи/агента
- **FIRST_COME_FIRST_SERVED** - Первая задача побеждает
- **NEGOTIATION** - Агенты ведут переговоры для решения
- **HUMAN_INTERVENTION** - Эскалация к человеку
- **RESOURCE_SHARING** - Разделение ресурса, если возможно
- **SEQUENTIAL_EXECUTION** - Последовательное выполнение задач
- **PARALLEL_EXECUTION** - Параллельное выполнение, если безопасно

#### 4. Методы обнаружения конфликтов

##### `detect_conflicts()`
- Обнаруживает все типы конфликтов между задачами
- Возвращает список конфликтов с деталями

##### `_detect_resource_conflicts()`
- Обнаруживает конфликты ресурсов
- Извлекает требования к ресурсам из метаданных задач

##### `_detect_goal_conflicts()`
- Обнаруживает противоречивые цели
- Использует паттерны ключевых слов (создать/удалить, включить/выключить)

##### `_detect_priority_conflicts()`
- Обнаруживает конфликты приоритетов
- Вычисляет схожесть задач и разницу в приоритетах

##### `_detect_dependency_conflicts()`
- Обнаруживает циклические зависимости
- Строит граф зависимостей и проверяет циклы

##### `_detect_timing_conflicts()`
- Обнаруживает конфликты расписания
- Проверяет перекрытие временных ограничений

#### 5. Методы разрешения конфликтов

##### `resolve_conflict()`
- Разрешает конфликт с использованием указанной стратегии
- Автоматически выбирает стратегию, если не указана

##### `_resolve_by_priority()`
- Разрешает конфликт на основе приоритета
- Высокоприоритетные задачи выполняются первыми

##### `_resolve_by_first_come()`
- Разрешает конфликт по принципу "первым пришел - первым обслужен"
- Первая созданная задача получает приоритет

##### `_resolve_by_negotiation()`
- Разрешает конфликт через переговоры агентов (заглушка для будущей реализации)

##### `_resolve_by_human_intervention()`
- Эскалирует конфликт к человеку для разрешения

##### `_resolve_by_resource_sharing()`
- Разрешает конфликт путем разделения ресурса
- Проверяет, может ли ресурс быть разделен

##### `_resolve_by_sequential_execution()`
- Разрешает конфликт путем последовательного выполнения
- Сортирует задачи по приоритету и времени создания

##### `_resolve_by_parallel_execution()`
- Разрешает конфликт путем параллельного выполнения
- Проверяет безопасность параллельного выполнения

## Интеграция

### Использование в PlanningService

```python
from app.services.conflict_resolution_service import ConflictResolutionService

# При создании плана
conflict_service = ConflictResolutionService(db)
conflicts = conflict_service.detect_conflicts([task1, task2, task3])

if conflicts:
    for conflict in conflicts:
        resolution = conflict_service.resolve_conflict(conflict)
        # Применить действия из resolution["actions"]
```

### Использование в ExecutionService

```python
# Перед выполнением плана
conflicts = conflict_service.detect_conflicts(active_tasks)

if conflicts:
    # Разрешить конфликты перед выполнением
    for conflict in conflicts:
        resolution = conflict_service.resolve_conflict(conflict)
        if resolution["resolved"]:
            # Применить действия
            for action in resolution["actions"]:
                if action["action"] == "delay":
                    # Отложить задачу
                    task.status = TaskStatus.ON_HOLD
```

## Алгоритмы приоритизации

1. **По приоритету задачи** - Задачи с более высоким приоритетом выполняются первыми
2. **По времени создания** - Первая созданная задача получает приоритет
3. **По статусу** - Задачи IN_PROGRESS имеют приоритет над PENDING

## Механизмы переговоров

Механизм переговоров между агентами пока не полностью реализован. Это требует:
- A2A коммуникации между агентами
- Протокол переговоров
- Механизм компромиссов

## Примеры использования

### Обнаружение конфликтов ресурсов

```python
conflict_service = ConflictResolutionService(db)
tasks = [task1, task2, task3]  # Все требуют доступ к базе данных
conflicts = conflict_service.detect_conflicts(tasks)

# Результат:
# [{
#   "type": "resource_conflict",
#   "severity": "medium",
#   "resource": "database",
#   "conflicting_tasks": ["task1", "task2", "task3"]
# }]
```

### Разрешение конфликта приоритетов

```python
conflict = {
    "type": "priority_conflict",
    "task_ids": [task1.id, task2.id],
    "priority_difference": 4
}

resolution = conflict_service.resolve_conflict(conflict, ConflictResolutionStrategy.PRIORITY_BASED)

# Результат:
# {
#   "resolved": True,
#   "strategy": "priority_based",
#   "actions": [
#     {"action": "proceed", "task_id": "task1", "reason": "Higher priority"},
#     {"action": "delay", "task_id": "task2", "reason": "Lower priority"}
#   ]
# }
```

## Следующие шаги (опционально)

1. ⏳ Интеграция в PlanningService для проверки конфликтов при планировании
2. ⏳ Интеграция в ExecutionService для проверки конфликтов перед выполнением
3. ⏳ Реализация механизма переговоров между агентами
4. ⏳ API endpoints для управления конфликтами
5. ⏳ Уведомления о конфликтах пользователю
6. ⏳ Метрики и мониторинг конфликтов

