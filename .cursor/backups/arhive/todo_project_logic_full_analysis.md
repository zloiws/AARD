# Полный анализ логики работы проекта AARD

**Дата создания:** 2025-01-27  
**Статус:** Анализ завершен

---

## Оглавление

1. [Общая архитектура и поток запросов](#общая-архитектура-и-поток-запросов)
2. [Граф логики работы проекта](#граф-логики-работы-проекта)
3. [Узкие места и проблемы производительности](#узкие-места-и-проблемы-производительности)
4. [Неиспользуемые компоненты](#неиспользуемые-компоненты)
5. [Компоненты, используемые неверно](#компоненты-используемые-неверно)
6. [Критические проблемы](#критические-проблемы)
7. [Рекомендации по улучшению](#рекомендации-по-улучшению)

---

## Общая архитектура и поток запросов

### Точка входа: API Endpoints

Проект имеет несколько точек входа для обработки запросов:

#### 1. Основной endpoint: `/api/chat` (POST)
**Файл:** `backend/app/api/routes/chat.py`

**Поток обработки:**
```
User Request → chat.py → ExecutionContext → WorkflowTracker → RequestOrchestrator.process_request()
```

**Детали:**
- Создается `ExecutionContext` с `db`, `workflow_id`, `trace_id`, `session_id`, `user_id`
- Создается `WorkflowTracker` (singleton, in-memory)
- Вызывается `RequestOrchestrator.process_request()` с параметрами:
  - `message`: текст запроса пользователя
  - `context`: ExecutionContext
  - `task_type`: тип задачи (опционально)
  - `model`, `server_id`, `temperature`: параметры LLM

#### 2. Прямые endpoints для планов: `/api/plans` (POST, GET, PUT, DELETE)
**Файл:** `backend/app/api/routes/plans.py`

**Поток обработки:**
```
POST /api/plans → PlanningService.generate_plan() (обходит RequestOrchestrator)
POST /api/plans/{id}/execute → ExecutionService.execute_plan() (обходит RequestOrchestrator)
```

**Проблема:** Эти endpoints обходят централизованную обработку через `RequestOrchestrator`, что может привести к:
- Несогласованному логированию
- Отсутствию workflow state management
- Пропуску интеграции с MemoryService, ReflectionService, MetaLearningService

#### 3. Endpoint для workflow событий: `/api/workflow` (GET)
**Файл:** `backend/app/api/routes/workflow.py`

**Поток обработки:**
```
GET /api/workflow/{workflow_id}/events → WorkflowEventService + WorkflowTracker
```

---

### Центральный компонент: RequestOrchestrator

**Файл:** `backend/app/core/request_orchestrator.py`

#### Определение типа запроса

`RequestOrchestrator` использует `RequestRouter` для классификации запросов:

**Типы запросов (RequestType):**
- `SIMPLE_QUESTION`: простые вопросы
- `INFORMATION_QUERY`: информационные запросы
- `CODE_GENERATION`: генерация кода
- `COMPLEX_TASK`: сложные задачи (требуют планирования)
- `PLANNING_ONLY`: только планирование без выполнения

**Метод определения:** `RequestRouter.determine_request_type()`
- Анализ ключевых слов в сообщении
- Использование явного `task_type` из параметров запроса

#### Обработка каждого типа запроса

##### 1. SIMPLE_QUESTION → `_handle_simple_question()`
**Поток:**
```
RequestOrchestrator → OllamaClient.generate() → Response
```
- Прямой запрос к LLM без планирования
- Использует `PromptManager` для выбора промпта
- Сохраняет метрики через `PromptManager`

##### 2. INFORMATION_QUERY → `_handle_information_query()`
**Поток:**
```
RequestOrchestrator → MemoryService.search_memories() → 
  [Если найдено] → Возврат результатов
  [Если не найдено] → TODO: WebSearchTool (НЕ ИНТЕГРИРОВАН) → _handle_simple_question()
```

**Проблема:** `WebSearchTool` существует (`backend/app/tools/web_search_tool.py`), но не интегрирован. В коде есть TODO комментарий на строке 407:
```python
# TODO: Интеграция WebSearchTool для поиска в интернете (с одобрением)
```

##### 3. CODE_GENERATION → `_handle_code_generation()`
**Поток:**
```
RequestOrchestrator → MemoryService.search_memories() (поиск похожего кода) →
  PlanningService.generate_plan() → Plan (DRAFT) →
  AdaptiveApprovalService.should_require_approval() →
    [Если требуется одобрение] → ApprovalService.create_approval_request() → Plan (PENDING_APPROVAL)
    [Если не требуется] → Plan (APPROVED) →
  ExecutionService.execute_plan() → Result
```

**Интеграция MemoryService:**
- Поиск похожих примеров кода в долгосрочной памяти
- Использование найденных паттернов в промпте для генерации

##### 4. COMPLEX_TASK → `_handle_complex_task()`
**Поток:**
```
RequestOrchestrator → 
  WorkflowEngine.transition_to(PLANNING) →
  PlanningService.generate_plan() →
  AdaptiveApprovalService.should_require_approval() →
    [Если требуется одобрение] → WorkflowEngine.transition_to(APPROVAL_PENDING) → ApprovalService
    [Если не требуется] → WorkflowEngine.transition_to(APPROVED) →
  ExecutionService.execute_plan() →
    [Успех] → ReflectionService.analyze_success() → MetaLearningService.analyze_execution_patterns() →
    [Ошибка] → ReflectionService.analyze_failure() → PlanningService.auto_replan_on_error() →
  WorkflowEngine.transition_to(COMPLETED/FAILED)
```

**Интеграция сервисов:**
- **MemoryService**: используется для поиска похожих задач и паттернов
- **ReflectionService**: анализирует успехи и неудачи выполнения
- **MetaLearningService**: анализирует паттерны выполнения для улучшения будущих планов

##### 5. PLANNING_ONLY → `_handle_planning_only()`
**Поток:**
```
RequestOrchestrator → PlanningService.generate_plan() → Plan (DRAFT)
```
- Только генерация плана без выполнения

---

### PlanningService: Генерация планов

**Файл:** `backend/app/services/planning_service.py`

#### Основной метод: `generate_plan()`

**Поток генерации плана:**

1. **Применение procedural memory patterns** (`_apply_procedural_memory_patterns()`)
   - Поиск похожих успешных планов в MemoryService
   - Поиск паттернов в MetaLearningService
   - Если найден паттерн с success_rate > 0.7 → адаптация шаблона

2. **Анализ задачи** (`_analyze_task()`)
   - Запрос к LLM для анализа задачи
   - Генерация стратегии (approach, assumptions, constraints, success_criteria)
   - Использует `PromptService` для выбора промпта
   - Сохраняет метрики через `PromptManager`

3. **Декомпозиция задачи** (`_decompose_task()`)
   - Запрос к LLM для разбиения задачи на шаги
   - Генерация списка шагов с типами, зависимостями, таймаутами
   - Использует `PromptService` для выбора промпта
   - Сохраняет метрики через `PromptManager`

4. **Оценка рисков** (`_assess_risks()`)
   - Простая эвристика на основе шагов
   - Подсчет high-risk шагов и шагов, требующих одобрения
   - Расчет overall_risk (0.0-1.0)

5. **Создание альтернатив** (`_create_alternatives()`)
   - **ТЕКУЩАЯ РЕАЛИЗАЦИЯ:** Возвращает пустой список `[]`
   - **ПОТЕНЦИАЛ:** Может генерировать альтернативные подходы через LLM

6. **Оценка длительности** (`_estimate_duration()`)
   - Суммирование таймаутов всех шагов

7. **Создание объекта Plan**
   - Сохранение в БД
   - Сохранение в episodic memory (`_save_plan_to_episodic_memory()`)
   - Сохранение в working memory как ToDo список (`_save_todo_to_working_memory()`)

8. **Создание запроса на одобрение** (`_create_plan_approval_request()`)
   - Использование `AdaptiveApprovalService` для определения необходимости одобрения
   - Если требуется → создание `ApprovalRequest` через `ApprovalService`
   - Если не требуется → автоматическое одобрение плана

#### Альтернативные планы: `generate_alternative_plans()`

**Поток:**
```
PlanningService.generate_alternative_plans() →
  [Параллельно] → generate_plan() с разными стратегиями:
    - Conservative (низкий риск, больше шагов)
    - Balanced (средний риск, оптимальные шаги)
    - Aggressive (высокий риск, меньше шагов) →
  PlanEvaluationService.evaluate_plans() →
  Выбор лучшего плана по оценке
```

**Использование:** Вызывается из `_generate_plan_with_alternatives()`, если `generate_alternatives=True` в контексте.

---

### ExecutionService: Выполнение планов

**Файл:** `backend/app/services/execution_service.py`

#### Основной метод: `execute_plan()`

**Поток выполнения:**

1. **Загрузка плана из БД**
   - Проверка статуса (должен быть APPROVED)
   - Загрузка шагов

2. **Инициализация контекста выполнения**
   - Создание `ExecutionContext` для шагов
   - Инициализация `WorkflowEngine` для отслеживания состояния

3. **Выполнение шагов последовательно** (`StepExecutor.execute_step()`)

   **Для каждого шага:**
   
   **a) Определение типа шага:**
   - `action`: выполнение действия
   - `decision`: принятие решения (placeholder)
   - `validation`: валидация (placeholder)
   
   **b) Выполнение action шага** (`_execute_action_step()`):
   
   **Определение исполнителя:**
   - Если `team_id` → `_execute_with_team()` → **ОШИБКА: МЕТОД НЕ РЕАЛИЗОВАН**
   - Если `agent_id` → `_execute_with_agent()`
   - Если `tool_id` → `_execute_with_tool()`
   - Иначе → LLM напрямую
   
   **c) Выполнение decision шага** (`_execute_decision_step()`):
   - **ПРОБЛЕМА:** Placeholder, возвращает "Decision made" без реальной логики
   
   **d) Выполнение validation шага** (`_execute_validation_step()`):
   - **ПРОБЛЕМА:** Placeholder, возвращает "Validation passed" без реальной логики

4. **Обработка результатов:**
   - Успех → сохранение результатов, переход к следующему шагу
   - Ошибка → анализ через `ReflectionService`, попытка перепланирования через `PlanningService.auto_replan_on_error()`

5. **Завершение:**
   - Обновление статуса плана (COMPLETED/FAILED)
   - Сохранение метрик через `PlanningMetricsService`
   - Вызов `MetaLearningService.analyze_execution_patterns()` для анализа паттернов

#### Критическая проблема: `_execute_with_team()` не реализован

**Местоположение:** `backend/app/services/execution_service.py:228`

**Код:**
```python
if team_id:
    try:
        return await self._execute_with_team(step, plan, context, result, team_id, tool_id)
    except Exception as e:
        logger.warning(...)
        # Fall back to agent or LLM execution
```

**Проблема:** Метод `_execute_with_team()` вызывается, но его определение отсутствует в классе `ExecutionService`.

**Последствия:**
- При выполнении шага с `team_id` будет `AttributeError`
- Fallback на agent/LLM может не соответствовать намерениям плана

**Существующий компонент:** `AgentTeamCoordination` (`backend/app/services/agent_team_coordination.py`) существует и имеет метод `distribute_task_to_team()`, но не используется в `ExecutionService`.

---

## Граф логики работы проекта

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                    │
│                    (POST /api/chat или /api/plans)                      │
└────────────────────────────┬──────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │   RequestRouter      │
                    │  (определение типа)  │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ SIMPLE_      │ │ INFORMATION_ │ │ CODE_        │
        │ QUESTION     │ │ QUERY        │ │ GENERATION   │
        └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
               │                 │                 │
               │                 │                 │
               ▼                 ▼                 ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ OllamaClient │ │ MemoryService │ │ MemoryService│
        │ .generate()  │ │ .search_      │ │ .search_     │
        │              │ │ memories()   │ │ memories()   │
        └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
               │                 │                 │
               │                 │                 │
               ▼                 ▼                 ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │   Response   │ │ [Найдено?]   │ │ Planning     │
        │              │ │   Да → Return│ │ Service      │
        │              │ │   Нет → TODO │ │ .generate_   │
        │              │ │   WebSearch  │ │ plan()       │
        └──────────────┘ └──────────────┘ └──────┬───────┘
                                                   │
                                                   ▼
                                    ┌──────────────────────────┐
                                    │   COMPLEX_TASK           │
                                    └──────────┬───────────────┘
                                               │
                                               ▼
                                    ┌──────────────────────────┐
                                    │  WorkflowEngine         │
                                    │  .transition_to()       │
                                    │  (PLANNING)             │
                                    └──────────┬───────────────┘
                                               │
                                               ▼
                                    ┌──────────────────────────┐
                                    │  PlanningService         │
                                    │  .generate_plan()       │
                                    └──────────┬───────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
        ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
        │ _apply_procedural│      │ _analyze_task()  │      │ _decompose_task()│
        │ _memory_patterns()│      │ (LLM)           │      │ (LLM)           │
        └────────┬─────────┘      └────────┬────────┘      └────────┬────────┘
                 │                          │                          │
                 │                          │                          │
                 ▼                          ▼                          ▼
        ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
        │ MemoryService    │      │ Strategy JSON    │      │ Steps Array      │
        │ MetaLearning     │      │                  │      │                  │
        │ Service          │      │                  │      │                  │
        └──────────────────┘      └──────────────────┘      └──────────────────┘
                    │                          │                          │
                    └──────────┬───────────────┴───────────────┐
                               │                               │
                               ▼                               ▼
                    ┌──────────────────┐          ┌──────────────────┐
                    │ _assess_risks()  │          │ _create_         │
                    │                  │          │ alternatives()   │
                    │                  │          │ (placeholder)   │
                    └────────┬─────────┘          └────────┬─────────┘
                             │                            │
                             └────────────┬───────────────┘
                                          │
                                          ▼
                               ┌──────────────────┐
                               │  Plan Object     │
                               │  (DRAFT)         │
                               └────────┬─────────┘
                                        │
                                        ▼
                               ┌──────────────────┐
                               │ AdaptiveApproval │
                               │ Service          │
                               │ .should_require_ │
                               │ approval()       │
                               └────────┬─────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │ Approval         │  │ Auto-approved    │  │ WorkflowEngine   │
        │ Required         │  │                  │  │ .transition_to()  │
        │                  │  │                  │  │ (APPROVED)        │
        └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                 │                     │                      │
                 │                     │                      │
                 ▼                     │                      │
        ┌──────────────────┐          │                      │
        │ ApprovalService  │          │                      │
        │ .create_         │          │                      │
        │ approval_        │          │                      │
        │ request()        │          │                      │
        └────────┬─────────┘          │                      │
                 │                    │                      │
                 │                    │                      │
                 └──────────┬─────────┴──────────────────────┘
                            │
                            ▼
                 ┌──────────────────┐
                 │ ExecutionService │
                 │ .execute_plan()  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ WorkflowEngine   │
                 │ .transition_to() │
                 │ (EXECUTING)      │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ StepExecutor      │
                 │ .execute_step()  │
                 └────────┬─────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ _execute_    │ │ _execute_    │ │ _execute_    │
│ _with_team() │ │ _with_agent()│ │ _with_tool() │
│ ❌ НЕТ       │ │              │ │              │
│ РЕАЛИЗАЦИИ   │ │              │ │              │
└──────────────┘ └──────┬───────┘ └──────┬───────┘
                        │                 │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ Step Result      │
                        │ (success/fail)   │
                        └────────┬─────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
        ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
        │ Success          │ │ Error           │ │ All Steps Done   │
        │                  │ │                 │ │                  │
        └────────┬─────────┘ └────────┬───────┘ └────────┬─────────┘
                 │                     │                  │
                 │                     │                  │
                 ▼                     ▼                  ▼
        ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
        │ Reflection       │ │ Reflection      │ │ WorkflowEngine  │
        │ Service          │ │ Service        │ │ .transition_to()│
        │ .analyze_        │ │ .analyze_      │ │ (COMPLETED)     │
        │ success()        │ │ failure()      │ │                 │
        └────────┬─────────┘ └────────┬───────┘ └────────┬─────────┘
                 │                     │                  │
                 │                     │                  │
                 │                     ▼                  │
                 │            ┌──────────────────┐        │
                 │            │ PlanningService  │        │
                 │            │ .auto_replan_    │        │
                 │            │ on_error()       │        │
                 │            └────────┬─────────┘        │
                 │                     │                  │
                 │                     │                  │
                 └─────────────────────┼──────────────────┘
                                       │
                                       ▼
                            ┌──────────────────┐
                            │ MetaLearning     │
                            │ Service          │
                            │ .analyze_        │
                            │ execution_       │
                            │ patterns()       │
                            └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ Final Response   │
                            │                  │
                            └──────────────────┘
```

---

## Узкие места и проблемы производительности

### 1. Дублирование Workflow Tracking

**Проблема:** Два компонента для отслеживания workflow:
- `WorkflowTracker` (in-memory singleton, `backend/app/core/workflow_tracker.py`)
- `WorkflowEngine` (database-backed, context-aware, `backend/app/core/workflow_engine.py`)

**Использование:**
- `WorkflowTracker` используется в `RequestOrchestrator` и `PlanningService`
- `WorkflowEngine` используется в `RequestOrchestrator` и `ExecutionService`

**Последствия:**
- Дублирование логики
- Потенциальная рассинхронизация состояний
- Увеличение сложности кода

**Рекомендация:** Унифицировать на `WorkflowEngine`, удалить `WorkflowTracker`.

---

### 2. Множественные запросы к LLM в PlanningService

**Проблема:** `PlanningService.generate_plan()` делает несколько последовательных запросов к LLM:
1. `_analyze_task()` → 1 запрос
2. `_decompose_task()` → 1 запрос
3. `_adapt_template_to_task()` (если используется шаблон) → 1 запрос

**Последствия:**
- Высокая задержка генерации плана (3+ запроса × время ответа LLM)
- Высокая нагрузка на LLM серверы
- Потенциальные таймауты при медленных моделях

**Рекомендация:** Объединить анализ и декомпозицию в один запрос к LLM с structured output.

---

### 3. Отсутствие кэширования результатов MemoryService

**Проблема:** `MemoryService.search_memories()` выполняет векторный поиск в БД при каждом запросе без кэширования.

**Последствия:**
- Высокая нагрузка на PostgreSQL + pgvector
- Медленный ответ при больших объемах данных
- Дублирование запросов для одинаковых задач

**Рекомендация:** Добавить кэширование результатов поиска (Redis или in-memory cache) с TTL.

---

### 4. Синхронные вызовы MetaLearningService

**Проблема:** `MetaLearningService.analyze_execution_patterns()` вызывается синхронно после выполнения плана.

**Последствия:**
- Блокировка ответа пользователю до завершения анализа
- Увеличение времени ответа

**Рекомендация:** Выполнять анализ асинхронно в фоновом режиме.

---

### 5. Прямые вызовы PlanningService и ExecutionService через API

**Проблема:** Endpoints `/api/plans` позволяют обходить `RequestOrchestrator`.

**Последствия:**
- Отсутствие централизованного логирования
- Пропуск интеграции с MemoryService, ReflectionService, MetaLearningService
- Несогласованное управление workflow states

**Рекомендация:** Перенаправить эти endpoints через `RequestOrchestrator` или добавить интеграцию сервисов в сами endpoints.

---

## Неиспользуемые компоненты

### 1. CriticService

**Файл:** `backend/app/services/critic_service.py`

**Назначение:** Валидация и оценка результатов выполнения задач.

**Реализованность:** ✅ Полностью реализован (494 строки кода)

**Функционал:**
- **Структурная валидация** (`_validate_structure()`): проверка формата, схемы, типов данных
- **Семантическая валидация** (`_validate_semantic()`): проверка соответствия результата задаче через LLM
- **Функциональная валидация** (`_validate_functional()`): проверка выполнения требований (must_contain, must_not_contain, длина)
- **Оценка качества** (`_assess_quality()`): метрики качества результата
- **Комплексная валидация** (`validate_result()`): объединяет все типы валидации

**Текущее использование:** 
- ❌ Только в `DecisionPipeline` (который сам не используется в основном потоке)
- ❌ Не используется в `ExecutionService` после выполнения шагов

**Где должен использоваться:**
- В `ExecutionService` после выполнения каждого шага плана для валидации результатов
- В `RequestOrchestrator._handle_code_generation()` для оценки качества сгенерированного кода
- В `ReflectionService` для анализа качества решений

---

### 2. DecisionPipeline

**Файл:** `backend/app/services/decision_pipeline.py`

**Назначение:** Многоэтапный pipeline для выполнения задач (Planner → Router → Executor → Critic → Reflection).

**Реализованность:** ✅ Полностью реализован (423 строки кода)

**Функционал:**
- **Stage 1: Planning** (`_planning_stage()`): разбиение задачи на шаги через `PlanningService`
- **Stage 2: Routing** (`_routing_stage()`): выбор инструментов/агентов/промптов через `DecisionRouter`
- **Stage 3: Execution** (`_execution_stage()`): выполнение шагов через `ExecutionService`
- **Stage 4: Critic** (`_critic_stage()`): валидация результатов через `CriticService`
- **Stage 5: Reflection** (`_reflection_stage()`): анализ ошибок и генерация исправлений через `ReflectionService`
- **Retry механизм:** автоматический retry с исправлениями при неудачной валидации

**Текущее использование:**
- ❌ Только в тестах (`test_phase6_consistency.py`)
- ❌ Не используется в `RequestOrchestrator`

**Где должен использоваться:**
- Альтернативный путь обработки сложных задач в `RequestOrchestrator._handle_complex_task()`
- Для задач, требующих строгой валидации и автоматического исправления ошибок

---

### 3. DecisionRouter

**Файл:** `backend/app/services/decision_router.py`

**Назначение:** Выбор инструментов, агентов и промптов на основе требований задачи.

**Реализованность:** ✅ Полностью реализован (575 строк кода)

**Функционал:**
- **Анализ задачи** (`_analyze_task()`): определение потребностей (tool, agent, prompt) на основе ключевых слов
- **Выбор инструмента** (`select_tool()`): фильтрация и оценка релевантности инструментов
- **Выбор агента** (`select_agent()`): фильтрация по capabilities и оценка релевантности
- **Выбор промпта** (`select_prompt()`): фильтрация по типу задачи и оценка релевантности
- **Оценка релевантности** (`_score_tool_relevance()`, `_score_agent_relevance()`, `_score_prompt_relevance()`): алгоритмы оценки соответствия компонентов задаче

**Текущее использование:**
- ❌ Только в `DecisionPipeline` (который не используется)

**Где должен использоваться:**
- В `PlanningService` для автоматического выбора инструментов/агентов для шагов плана
- В `RequestOrchestrator` для выбора компонентов перед выполнением задачи
- В `ExecutionService` для динамического выбора исполнителя шага

---

### 4. A2ARouter

**Файл:** `backend/app/services/a2a_router.py`

**Назначение:** Маршрутизация сообщений между агентами (Agent-to-Agent протокол).

**Реализованность:** ✅ Полностью реализован (288 строк кода)

**Функционал:**
- **Отправка сообщений** (`send_message()`): отправка сообщения конкретному агенту, broadcast или multicast
- **Direct message** (`_send_to_agent()`): отправка сообщения конкретному агенту через HTTP
- **Broadcast** (`_broadcast()`): отправка сообщения всем активным агентам
- **Multicast** (`_multicast()`): отправка сообщения агентам, соответствующим фильтру (capabilities, status, health_status)
- **Обработка входящих** (`handle_incoming_message()`): обработка REQUEST, RESPONSE, NOTIFICATION, HEARTBEAT сообщений
- **Поддержка протокола A2A:** синхронные request-response и асинхронные уведомления

**Текущее использование:**
- ⚠️ `AgentTeamCoordination` (не используется в `ExecutionService`)
- ⚠️ `AgentDialogService` (диалоги между агентами)
- ⚠️ `AgentTeamService` (управление командами)
- ⚠️ API route `/api/a2a` (прямые вызовы)

**Где должен использоваться:**
- В `ExecutionService._execute_with_team()` для координации команд агентов
- Для распределения задач между агентами в команде
- Для обмена информацией между агентами при выполнении сложных задач

---

### 5. ArtifactGenerator

**Файл:** `backend/app/services/artifact_generator.py`

**Назначение:** Генерация артефактов (агентов и инструментов) через LLM.

**Реализованность:** ✅ Полностью реализован (387 строк кода)

**Функционал:**
- **Анализ требований** (`_analyze_requirements()`): анализ описания через LLM для извлечения требований
- **Поиск похожих артефактов** (`_find_similar_artifacts()`): поиск в БД похожих артефактов для использования как примеры
- **Генерация кода инструментов** (`_generate_tool_code()`): генерация Python кода для инструментов через LLM
- **Генерация промптов агентов** (`_generate_agent_prompt()`): генерация промптов для агентов через LLM
- **Валидация** (`_validate_artifact()`): базовая проверка синтаксиса кода
- **Оценка безопасности** (`_assess_security()`): проверка на опасные паттерны (eval, exec, os.system)
- **Создание запросов на одобрение**: автоматическое создание `ApprovalRequest` для новых артефактов

**Текущее использование:**
- ⚠️ API route `/api/artifacts` (прямые вызовы)
- ❌ Не используется в основном потоке обработки запросов

**Где должен использоваться:**
- В будущем: когда агенты будут создавать инструменты и других агентов
- Для автоматической генерации инструментов на основе описания задачи
- Для создания специализированных агентов для конкретных задач

---

### 6. AgentGymService

**Файл:** `backend/app/services/agent_gym_service.py`

**Назначение:** Автоматизированное тестирование и бенчмаркинг агентов.

**Реализованность:** ✅ Полностью реализован (583+ строк кода)

**Функционал:**
- **Создание тестов** (`create_test()`): создание функциональных, производительностных и других типов тестов
- **Запуск тестов** (`run_test()`, `run_test_suite()`): выполнение тестов для агентов
- **Создание бенчмарков** (`create_benchmark()`): создание наборов тестов для бенчмаркинга
- **Запуск бенчмарков** (`run_benchmark()`): выполнение бенчмарков и сбор метрик
- **Анализ результатов** (`get_test_results()`, `get_benchmark_results()`): статистика по тестам и бенчмаркам
- **Управление тестами**: CRUD операции для тестов и бенчмарков

**Текущее использование:**
- ⚠️ API routes `/api/agent-gym/*` (прямые вызовы)
- ❌ Не используется в основном потоке обработки запросов

**Где должен использоваться:**
- Автоматическое тестирование агентов после создания/обновления
- Периодический бенчмаркинг агентов для оценки производительности
- В CI/CD pipeline для проверки качества агентов

---

### 7. AgentExperimentService

**Файл:** `backend/app/services/agent_experiment_service.py`

**Назначение:** A/B тестирование агентов.

**Реализованность:** ✅ Полностью реализован (438+ строк кода)

**Функционал:**
- **Создание экспериментов** (`create_experiment()`): создание A/B экспериментов с настройкой traffic split
- **Управление трафиком** (`assign_to_variant()`): распределение запросов между вариантами A и B
- **Сбор метрик** (`record_result()`): сбор результатов выполнения для каждого варианта
- **Статистический анализ** (`analyze_results()`): расчет статистической значимости, confidence intervals
- **Автоматическое определение победителя** (`determine_winner()`): автоматический выбор лучшего варианта
- **Управление статусами** (`start_experiment()`, `stop_experiment()`, `pause_experiment()`): управление жизненным циклом экспериментов
- **Метрики**: success_rate, execution_time_ms, quality_score и другие

**Текущее использование:**
- ⚠️ API routes `/api/experiments/*` (прямые вызовы)
- ❌ Не используется в основном потоке обработки запросов

**Где должен использоваться:**
- Для A/B тестирования разных версий агентов
- Для сравнения разных стратегий выполнения задач
- Для оптимизации выбора агентов на основе реальных результатов

---

### 8. ModelBenchmarkService

**Файл:** `backend/app/services/model_benchmark_service.py`

**Назначение:** Бенчмаркинг LLM моделей для выбора на основе производительности.

**Реализованность:** ✅ Полностью реализован (348+ строк кода)

**Функционал:**
- **Бенчмарк одной модели** (`benchmark_model()`): тестирование модели на конкретном типе задачи
- **Бенчмарк всех моделей** (`benchmark_all_models()`): массовое тестирование всех моделей
- **Тестирование на разных типах задач**: PLANNING, CODE_GENERATION с соответствующими тестовыми промптами
- **Измерение метрик**: время ответа, количество токенов, качество ответа
- **Сохранение результатов**: сохранение результатов в БД для использования в `ModelSelector`
- **Обработка ошибок**: таймауты, обработка недоступных моделей

**Текущее использование:**
- ❌ Только в тестах (`test_model_benchmark_real.py`)
- ❌ Не используется в `ModelSelector`

**Где должен использоваться:**
- В `ModelSelector` для автоматического выбора лучших моделей на основе бенчмарков
- Периодический запуск для обновления метрик производительности моделей
- При добавлении новых моделей для их оценки

---

### 9. SelfAuditService

**Файл:** `backend/app/services/self_audit_service.py`

**Назначение:** Автоматизированный самоаудит системы.

**Реализованность:** ✅ Полностью реализован (1247+ строк кода)

**Функционал:**
- **Аудит производительности** (`audit_performance()`): анализ времени выполнения, success rate, throughput
- **Аудит качества планов** (`audit_quality()`): анализ качества планов, успешности выполнения, паттернов ошибок
- **Аудит эффективности промптов** (`audit_prompts()`): анализ использования промптов, их эффективности, рекомендации по улучшению
- **Анализ паттернов ошибок** (`audit_errors()`): классификация ошибок, поиск повторяющихся проблем
- **Трендовый анализ** (`audit_trends()`): анализ трендов производительности, качества, использования ресурсов
- **Генерация рекомендаций**: автоматические рекомендации по улучшению системы
- **Создание отчетов** (`create_audit_report()`): создание структурированных отчетов с результатами аудита

**Текущее использование:**
- ❌ Не используется нигде в основном потоке
- ❌ Не запускается периодически

**Где должен использоваться:**
- Периодический запуск через scheduler (например, раз в день/неделю)
- Автоматический запуск при обнаружении проблем (высокий процент ошибок, деградация производительности)
- Для генерации отчетов о состоянии системы для администраторов

---

## Сводная таблица неиспользуемых компонентов

| Компонент | Реализованность | Используется | Где должен использоваться |
|-----------|----------------|--------------|--------------------------|
| **CriticService** | ✅ 100% (494 строки) | ❌ Только в DecisionPipeline | ExecutionService после выполнения шагов |
| **DecisionPipeline** | ✅ 100% (423 строки) | ❌ Только в тестах | RequestOrchestrator._handle_complex_task() |
| **DecisionRouter** | ✅ 100% (575 строк) | ❌ Только в DecisionPipeline | PlanningService для выбора компонентов |
| **A2ARouter** | ✅ 100% (288 строк) | ⚠️ Частично (не в основном потоке) | ExecutionService._execute_with_team() |
| **ArtifactGenerator** | ✅ 100% (387 строк) | ⚠️ API routes | Будущее: создание артефактов агентами |
| **AgentGymService** | ✅ 100% (583+ строк) | ⚠️ API routes | Автоматическое тестирование агентов |
| **AgentExperimentService** | ✅ 100% (438+ строк) | ⚠️ API routes | A/B тестирование агентов |
| **ModelBenchmarkService** | ✅ 100% (348+ строк) | ❌ Только в тестах | ModelSelector для выбора моделей |
| **SelfAuditService** | ✅ 100% (1247+ строк) | ❌ Не используется | Периодический самоаудит системы |

---

## Выводы по неиспользуемым компонентам

1. **Все компоненты полностью реализованы** и готовы к использованию
2. **Основная проблема:** компоненты не интегрированы в основной поток обработки запросов через `RequestOrchestrator`
3. **Некоторые компоненты доступны через отдельные API endpoints**, но не используются автоматически
4. **Рекомендация:** 
   - Интегрировать критичные компоненты (`CriticService`, `DecisionRouter`, `A2ARouter`) в основной поток
   - Использовать остальные компоненты по необходимости или через планировщик задач
   - Настроить периодический запуск `SelfAuditService` и `ModelBenchmarkService`

---

## Компоненты, используемые неверно

### 1. WorkflowTracker vs WorkflowEngine

**Проблема:** Два компонента выполняют схожую функцию, используются параллельно.

**Текущее использование:**
- `WorkflowTracker`: в `RequestOrchestrator`, `PlanningService` (in-memory singleton)
- `WorkflowEngine`: в `RequestOrchestrator`, `ExecutionService` (database-backed, context-aware)

**Рекомендация:** Унифицировать на `WorkflowEngine`, удалить `WorkflowTracker`.

---

### 2. ServiceRegistry

**Файл:** `backend/app/core/service_registry.py`

**Статус:** Реализован, но используется не везде.

**Проблема:** Сервисы создаются напрямую через конструкторы вместо использования `ServiceRegistry`.

**Примеры:**
- `RequestOrchestrator` создает сервисы напрямую
- `PlanningService` создает сервисы напрямую
- `ExecutionService` создает сервисы напрямую

**Рекомендация:** Использовать `ServiceRegistry` для централизованного управления зависимостями.

---

### 3. ExecutionContext

**Файл:** `backend/app/core/execution_context.py`

**Статус:** Используется не везде, где должен.

**Проблема:** Некоторые сервисы не получают `ExecutionContext`, создают свои DB сессии.

**Примеры:**
- `PlanningService` может работать без `ExecutionContext`
- `MemoryService` может работать без `ExecutionContext`

**Рекомендация:** Передавать `ExecutionContext` во все сервисы для согласованного управления ресурсами.

---

### 4. PromptManager vs PromptService

**Проблема:** Два компонента для управления промптами:
- `PromptManager` (`backend/app/core/prompt_manager.py`) - новый, интегрирован в `ExecutionContext`
- `PromptService` (`backend/app/services/prompt_service.py`) - старый, используется в `PlanningService`

**Текущее использование:**
- `PromptManager`: используется в `RequestOrchestrator` через `ExecutionContext`
- `PromptService`: используется в `PlanningService` напрямую

**Рекомендация:** Унифицировать на `PromptManager`, обновить `PlanningService` для использования `PromptManager` из `ExecutionContext`.

---

## Критические проблемы

### 1. ❌ КРИТИЧНО: `_execute_with_team()` не реализован

**Файл:** `backend/app/services/execution_service.py:228`

**Проблема:** Метод вызывается, но его определение отсутствует.

**Код:**
```python
if team_id:
    try:
        return await self._execute_with_team(step, plan, context, result, team_id, tool_id)
    except Exception as e:
        logger.warning(...)
        # Fall back to agent or LLM execution
```

**Последствия:**
- `AttributeError` при выполнении шага с `team_id`
- Планы с командами не могут быть выполнены

**Решение:**
- Реализовать `_execute_with_team()` используя `AgentTeamCoordination.distribute_task_to_team()`
- Или удалить вызов и обработать `team_id` через `_execute_with_agent()`

---

### 2. ❌ КРИТИЧНО: Placeholder методы `_execute_decision_step()` и `_execute_validation_step()`

**Файл:** `backend/app/services/execution_service.py:652-683`

**Проблема:** Методы возвращают фиктивные результаты без реальной логики.

**Код:**
```python
async def _execute_decision_step(...) -> Dict[str, Any]:
    """Execute a decision step"""
    result["status"] = "completed"
    result["output"] = "Decision made"
    result["message"] = "Decision step executed (placeholder)"
    return result

async def _execute_validation_step(...) -> Dict[str, Any]:
    """Execute a validation step"""
    result["status"] = "completed"
    result["output"] = "Validation passed"
    result["message"] = "Validation step executed (placeholder)"
    return result
```

**Последствия:**
- Планы с decision/validation шагами не выполняются корректно
- Нет реальной валидации результатов

**Решение:**
- Реализовать логику принятия решений через LLM
- Реализовать логику валидации через LLM или правила

---

### 3. ⚠️ ВАЖНО: WebSearchTool не интегрирован

**Файл:** `backend/app/tools/web_search_tool.py` существует, но не используется.

**Местоположение проблемы:** `backend/app/core/request_orchestrator.py:407`

**Код:**
```python
# Если воспоминаний нет, используем обычный поиск
# TODO: Интеграция WebSearchTool для поиска в интернете (с одобрением)
return await self._handle_simple_question(message, context)
```

**Последствия:**
- Информационные запросы без результатов в памяти не могут использовать веб-поиск
- Ограниченные возможности системы для получения актуальной информации

**Решение:**
- Интегрировать `WebSearchTool` в `_handle_information_query()`
- Добавить проверку через `AdaptiveApprovalService` для одобрения веб-поиска

---

### 4. ⚠️ ВАЖНО: Дублирование Workflow Tracking

**Проблема:** Два компонента для отслеживания workflow.

**Последствия:**
- Рассинхронизация состояний
- Увеличение сложности кода
- Потенциальные баги

**Решение:**
- Унифицировать на `WorkflowEngine`
- Удалить `WorkflowTracker` или сделать его оберткой над `WorkflowEngine`

---

### 5. ⚠️ ВАЖНО: Прямые вызовы PlanningService и ExecutionService

**Проблема:** Endpoints `/api/plans` обходят `RequestOrchestrator`.

**Последствия:**
- Отсутствие централизованного логирования
- Пропуск интеграции с MemoryService, ReflectionService, MetaLearningService

**Решение:**
- Перенаправить endpoints через `RequestOrchestrator`
- Или добавить интеграцию сервисов в сами endpoints

---

## Рекомендации по улучшению

### Приоритет 1: Критические исправления

1. **Реализовать `_execute_with_team()` в ExecutionService**
   - Использовать `AgentTeamCoordination.distribute_task_to_team()`
   - Обработать результаты распределения задач

2. **Реализовать `_execute_decision_step()` и `_execute_validation_step()`**
   - Добавить логику принятия решений через LLM
   - Добавить логику валидации через LLM или правила

3. **Интегрировать WebSearchTool**
   - Добавить в `_handle_information_query()`
   - Добавить проверку через `AdaptiveApprovalService`

---

### Приоритет 2: Архитектурные улучшения

1. **Унифицировать Workflow Tracking**
   - Удалить `WorkflowTracker` или сделать его оберткой над `WorkflowEngine`
   - Обновить все использования

2. **Унифицировать Prompt Management**
   - Использовать `PromptManager` везде вместо `PromptService`
   - Обновить `PlanningService` для использования `PromptManager` из `ExecutionContext`

3. **Централизовать создание сервисов**
   - Использовать `ServiceRegistry` везде
   - Передавать `ExecutionContext` во все сервисы

---

### Приоритет 3: Оптимизация производительности

1. **Оптимизировать PlanningService**
   - Объединить `_analyze_task()` и `_decompose_task()` в один запрос к LLM
   - Использовать structured output для получения стратегии и шагов одновременно

2. **Добавить кэширование MemoryService**
   - Кэшировать результаты поиска в памяти
   - Использовать Redis для распределенного кэширования

3. **Асинхронизировать MetaLearningService**
   - Выполнять анализ паттернов в фоновом режиме
   - Не блокировать ответ пользователю

---

### Приоритет 4: Интеграция неиспользуемых компонентов

1. **Интегрировать CriticService**
   - Использовать для валидации результатов выполнения шагов
   - Оценивать качество сгенерированного кода

2. **Рассмотреть использование DecisionPipeline**
   - Как альтернативный путь обработки сложных задач
   - Или удалить, если не планируется использовать

3. **Интегрировать AgentTeamCoordination**
   - Использовать в `ExecutionService._execute_with_team()`
   - Обеспечить координацию команд агентов

---

## Заключение

Проект AARD имеет сложную архитектуру с множеством компонентов. Основной поток обработки запросов работает через `RequestOrchestrator`, который интегрирует различные сервисы для планирования, выполнения и обучения.

**Ключевые проблемы:**
1. Критическая: отсутствие реализации `_execute_with_team()`
2. Критическая: placeholder методы для decision/validation шагов
3. Важная: неинтегрированный WebSearchTool
4. Важная: дублирование Workflow Tracking
5. Важная: прямые вызовы сервисов через API

**Рекомендации:**
- Сначала исправить критические проблемы
- Затем унифицировать архитектуру (Workflow, Prompt Management)
- Оптимизировать производительность
- Интегрировать неиспользуемые компоненты или удалить их

---

**Следующие шаги:**
1. Создать задачи для исправления критических проблем
2. Провести рефакторинг для унификации компонентов
3. Добавить тесты для проверки исправлений
4. Обновить документацию
