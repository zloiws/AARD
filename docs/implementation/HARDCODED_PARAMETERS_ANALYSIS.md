# Анализ хардкодных параметров в основном коде

## ✅ Исправлено

### UncertaintyService
- Все параметры вынесены в БД через `UncertaintyParameter`
- Создан `UncertaintyLearningService` для обучения

## ❌ Требуют рефакторинга

### 1. AdaptiveApprovalService
**Файл:** `backend/app/services/adaptive_approval_service.py`

**Хардкодные параметры:**

#### Пороги для принятия решений:
```python
TRUST_SCORE_THRESHOLD = 0.8  # Строка 30
HIGH_RISK_THRESHOLD = 0.7    # Строка 31
MEDIUM_RISK_THRESHOLD = 0.4  # Строка 32
MIN_EXECUTIONS_FOR_TRUST = 5 # Строка 35
```

#### Веса для расчета trust score:
```python
success_rate * 0.6 +           # Строка 268
min(1.0, total_tasks / 100.0) * 0.2 +  # Строка 269
recent_performance * 0.2        # Строка 270
```

#### Пороги для расчета риска:
```python
if num_steps > 10: risk_score += 0.3      # Строка 463
elif num_steps > 5: risk_score += 0.2     # Строка 465
elif num_steps > 2: risk_score += 0.1     # Строка 467

if high_risk_count >= 3: risk_score += 0.4  # Строка 480
elif high_risk_count >= 2: risk_score += 0.3 # Строка 482
elif high_risk_count >= 1: risk_score += 0.2 # Строка 484

if steps_with_deps > 3: risk_score += 0.1    # Строка 500
elif steps_with_deps > 1: risk_score += 0.05 # Строка 502
```

#### Другие пороги:
```python
if task_risk_level < 0.9:  # Строка 125 - для автономии уровня 4
if agent_trust_score < 0.5:  # Строка 165 - для низкого доверия
```

**Рекомендация:** Вынести все параметры в БД через модель `ApprovalParameter` (аналогично `UncertaintyParameter`).

---

### 2. ConflictResolutionService
**Файл:** `backend/app/services/conflict_resolution_service.py`

**Хардкодные параметры:**

```python
if len(active_tasks) < 2:  # Строка 91
if similarity > 0.7:  # Строка 194 - порог схожести задач
if abs(priority1 - priority2) >= 3:  # Строка 199 - значительная разница приоритетов
```

**Списки ключевых слов:**
```python
# Строки 156-158 - пары противоречивых действий
(["создать", "create", "добавить", "add"], ["удалить", "delete", "удалить", "remove"]),
(["включить", "enable", "активировать", "activate"], ["выключить", "disable", "деактивировать", "deactivate"]),
(["увеличить", "increase", "расширить", "expand"], ["уменьшить", "decrease", "сократить", "reduce"]),

# Строки 539-542 - ключевые слова для определения типов ресурсов
"database": ["база данных", "database", "db", "postgres", "mysql"],
"file": ["файл", "file", "директория", "directory"],
"network": ["сеть", "network", "http", "https"],

# Строка 690 - ключевые слова для операций записи
write_keywords = ["write", "create", "delete", "update", "modify", "изменить", "создать", "удалить"]
```

**Рекомендация:** Вынести пороги и списки ключевых слов в БД.

---

### 3. CriticService
**Файл:** `backend/app/services/critic_service.py`

**Хардкодные параметры:**

#### Пороги валидации:
```python
is_valid = overall_score >= 0.6 and len(all_issues) == 0  # Строка 103
quality_threshold = requirements.get("quality_threshold", 0.7)  # Строка 422
is_valid=score >= 0.7,  # Строка 429
```

#### Штрафы за ошибки:
```python
score -= 0.2  # Строка 160 - за отсутствие обязательных полей
score -= 0.1  # Строка 186 - за несоответствие типов
score -= 0.1  # Строка 193 - за несоответствие типов
score -= 0.5  # Строка 255 - за отсутствие результата
score -= 0.3  # Строка 266 - за низкое совпадение ключевых слов
score -= 0.2  # Строка 269 - за среднее совпадение
score -= 0.3  # Строка 277 - за отсутствие ключевых слов
score -= 0.3  # Строка 346 - за критические проблемы
score -= 0.2  # Строка 361 - за предупреждения
score -= 0.1  # Строка 368 - за информационные сообщения
score -= 0.3  # Строка 405 - за короткий результат
score -= 0.2  # Строка 413 - за низкое качество
score -= 0.1  # Строка 418 - за отсутствие пунктуации
```

#### Пороги для семантической валидации:
```python
if overlap < len(task_keywords) * 0.3:  # Строка 267 - 30% совпадения
if len(result_str) < 10:  # Строка 403 - минимальная длина результата
```

**Рекомендация:** Вынести все пороги и штрафы в БД через модель `CriticParameter`.

---

### 4. QuotaManagementService
**Файл:** `backend/app/services/quota_management_service.py`

**Хардкодные параметры:**

#### Пороги предупреждений:
```python
"warning_threshold": 0.8  # Строки 76, 81, 86, 91, 96, 101, 106, 111, 116, 121
usage_percentage >= 0.95  # Строки 185, 377
usage_percentage >= 1.0   # Строка 375
```

#### Списки ключевых слов для определения типов ресурсов:
```python
# Строка 542
if any(word in description_lower for word in ["найти", "find", "получить", "get", "список", "list"]):

# Строка 548
if any(word in description_lower for word in ["файл", "file", "директория", "directory"]):

# Строка 554
if any(word in description_lower for word in ["api", "запрос", "request", "http", "сеть", "network"]):

# Строка 560
if any(word in description_lower for word in ["сложн", "complex", "больш", "large", "много", "many"]):
```

#### Пороги для оценки ресурсов:
```python
if len(task.description.split()) > 50:  # Строка 531
    estimates[ResourceType.LLM_REQUESTS] = 10.0
elif len(task.description.split()) > 20:  # Строка 533
    estimates[ResourceType.LLM_REQUESTS] = 5.0
```

**Рекомендация:** Вынести пороги и списки ключевых слов в БД.

---

### 5. PlanningService
**Файл:** `backend/app/services/planning_service.py`

**Хардкодные параметры:**

#### Пороги для оценки планов:
```python
min_success_rate=0.7,  # Строка 933
impact_score=0.7,      # Строка 1256
impact_score=0.3,     # Строка 1266
overall_risk > 0.7,   # Строка 2913
overall_risk > 0.4,   # Строка 2915
success_rate > 0.7,   # Строки 3507, 3517
```

#### Веса для оценки планов:
```python
# Строка 710 - веса для оценки планов
execution_time=0.25, approval_points=0.20, risk_level=0.25, efficiency=0.30
```

#### Пороги для важности:
```python
importance=0.7,  # Строка 3416 - высокая важность для истории планов
importance=0.8,  # Строка 3521 - высокая важность для изученных паттернов
```

**Рекомендация:** Вынести пороги и веса в БД.

---

### 6. MemoryService
**Файл:** `backend/app/services/memory_service.py`

**Хардкодные параметры:**

```python
similarity_threshold: float = 0.7,  # Строка 505 - порог схожести по умолчанию
importance: float = 0.5,  # Строки 81, 164 - важность по умолчанию
strength: float = 0.5,   # Строка 954 - сила ассоциации по умолчанию
```

**Рекомендация:** Вынести значения по умолчанию в БД.

---

## План рефакторинга

### Приоритет 1 (Критично для саморазвития):
1. **AdaptiveApprovalService** - влияет на все решения об одобрении
2. **CriticService** - влияет на валидацию результатов
3. **PlanningService** - влияет на создание планов

### Приоритет 2 (Важно):
4. **ConflictResolutionService** - влияет на разрешение конфликтов
5. **QuotaManagementService** - влияет на управление ресурсами

### Приоритет 3 (Желательно):
6. **MemoryService** - значения по умолчанию

## Рекомендуемый подход

Для каждого сервиса создать:
1. Модель параметров (например, `ApprovalParameter`, `CriticParameter`)
2. Сервис обучения (например, `ApprovalLearningService`, `CriticLearningService`)
3. Рефакторинг основного сервиса для использования параметров из БД

Можно использовать общую модель `SystemParameter` вместо отдельных моделей для каждого сервиса.

