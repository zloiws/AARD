<!-- 6d8dd0f8-6800-4f1f-98ce-2702569f3c9f 6a59fe0b-4d3b-4e90-b590-1ed736d5b1bf -->
# План: Dual-Model Architecture и Self-Improvement

## Этап 1: Dual-Model Architecture - Разделение моделей планирования и кода

### 1.1. ModelSelector для специализированных моделей

**Файл:** `backend/app/core/model_selector.py`

**Задачи:**

1. Создать класс `ModelSelector` с методами:

   - `get_planning_model(db: Session)` - получение модели для планирования (reasoning модели)
   - `get_code_model(db: Session)` - получение модели для генерации кода (code модели)
   - `get_model_by_capabilities(db: Session, capabilities: List[str])` - выбор по capabilities

2. Интегрировать в `PlanningService` - использовать `get_planning_model()`
3. Интегрировать в `ExecutionService` - использовать `get_code_model()` для генерации кода
4. Обновить `OllamaClient` для поддержки явного выбора типа модели

**Приоритет:** Высокий

### 1.2. Function Calling Protocol

**Файл:** `backend/app/core/function_calling.py`

**Задачи:**

1. Создать класс `FunctionCallProtocol`:

   - `create_function_call(function_name, parameters, validation_schema)` - создание структурированного вызова
   - `validate_function_call(call)` - валидация перед выполнением
   - `parse_function_call_from_llm(response)` - парсинг ответа LLM в структурированный вызов

2. Обновить `PlanningService._decompose_task()` - генерировать Function Calls вместо произвольного текста
3. Обновить `ExecutionService._execute_action_step()` - обрабатывать Function Calls
4. Добавить схемы валидации для разных типов инструментов

**Приоритет:** Высокий

### 1.3. Обновление PlanningService для Function Calling

**Файл:** `backend/app/services/planning_service.py`

**Задачи:**

1. Модифицировать `_decompose_task()` для генерации Function Calls:
   ```python
   {
     "function": "code_execution_tool",
     "parameters": {
       "code": "...",
       "language": "python"
     },
     "step_id": "step_1",
     "description": "..."
   }
   ```

2. Обновить system_prompt для планировщика - требовать Function Calling формат
3. Добавить валидацию Function Calls перед сохранением плана

**Приоритет:** Высокий

## Этап 2: Улучшение Human-in-the-Loop механизмов

### 2.1. Adaptive Approval Service

**Файл:** `backend/app/services/adaptive_approval_service.py`

**Задачи:**

1. Создать класс `AdaptiveApprovalService`:

   - `should_require_approval(plan, agent_trust_score, task_risk_level)` - умное определение необходимости утверждения
   - `calculate_agent_trust_score(agent_id)` - расчет доверия на основе истории
   - `calculate_task_risk_level(task_description, context)` - расчет уровня риска

2. Интегрировать в `PlanningService._create_plan_approval_request()` - использовать адаптивную логику
3. Добавить метрики для отслеживания эффективности адаптивных решений
4. Создать миграцию для хранения trust scores агентов

**Приоритет:** Высокий

### 2.2. Interactive Execution Service

**Файл:** `backend/app/services/interactive_execution_service.py`

**Задачи:**

1. Создать класс `InteractiveExecutionService`:

   - `execute_with_human_oversight(step, human_feedback_callback)` - выполнение с возможностью вмешательства
   - `pause_for_clarification(step, question)` - пауза для уточнения
   - `request_confirmation(step, context)` - запрос подтверждения

2. Интегрировать в `ExecutionService.execute_plan()` - опциональное использование интерактивного режима
3. Добавить API endpoints для интерактивного взаимодействия
4. Создать UI компоненты для интерактивного контроля

**Приоритет:** Средний

## Этап 3: Замкнутый цикл обучения и самоусовершенствования

### 3.1. Meta-Learning Service

**Файл:** `backend/app/services/meta_learning_service.py`

**Задачи:**

1. Создать класс `MetaLearningService`:

   - `analyze_execution_patterns(agent_id)` - анализ паттернов выполнения
   - `improve_planning_strategy(plan_id)` - улучшение стратегии планирования
   - `evolve_prompts(prompt_id)` - эволюция промптов
   - `identify_best_practices()` - выявление лучших практик

2. Создать модели БД для хранения мета-данных обучения:

   - `ExecutionPattern` - паттерны выполнения
   - `StrategyImprovement` - улучшения стратегий
   - `PromptEvolution` - эволюция промптов

3. Создать миграцию для новых таблиц
4. Интегрировать в `DecisionPipeline` - автоматический анализ после выполнения

**Приоритет:** Высокий

### 3.2. Feedback Learning Service

**Файл:** `backend/app/services/feedback_learning_service.py`

**Задачи:**

1. Создать класс `FeedbackLearningService`:

   - `learn_from_approval_feedback(approval, human_feedback)` - обучение на обратной связи
   - `apply_learned_patterns(task_description)` - применение изученных паттернов
   - `extract_improvements_from_feedback(feedback)` - извлечение улучшений из фидбека

2. Интегрировать в `ApprovalService` - автоматическое обучение при утверждении/отклонении
3. Создать модель БД для хранения извлеченных паттернов
4. Добавить метрики эффективности обучения

**Приоритет:** Средний

### 3.3. Planning Metrics Service

**Файл:** `backend/app/services/planning_metrics_service.py`

**Задачи:**

1. Создать класс `PlanningMetricsService`:

   - `calculate_plan_quality_score(plan)` - оценка качества плана
   - `track_plan_execution_success(plan_id, success)` - отслеживание успешности
   - `compare_plan_versions(plan_id)` - сравнение версий планов

2. Интегрировать в `PlanningService` - автоматический расчет метрик
3. Создать API endpoints для получения метрик
4. Добавить визуализацию метрик в UI

**Приоритет:** Средний

## Этап 4: Безопасность и изоляция выполнения

### 4.1. Code Execution Sandbox

**Файл:** `backend/app/services/code_execution_sandbox.py`

**Задачи:**

1. Создать класс `CodeExecutionSandbox`:

   - `execute_code_safely(code, language, constraints)` - безопасное выполнение
   - Настройка ограничений: время, память, файловая система, сеть
   - Логирование всех действий
   - Изоляция окружения выполнения

2. Интегрировать в `PythonTool.execute_python_code()` - использовать sandbox
3. Добавить конфигурацию ограничений в настройки
4. Создать мониторинг использования ресурсов

**Приоритет:** Высокий (критично для безопасности)

## Этап 5: Интеграция и тестирование

### 5.1. Интеграция всех компонентов

**Задачи:**

1. Обновить `DecisionPipeline` для использования новых сервисов
2. Обновить `ExecutionService` для использования Function Calling и Sandbox
3. Обновить `PlanningService` для использования ModelSelector и Function Calling
4. Добавить конфигурацию для всех новых компонентов

**Приоритет:** Высокий

### 5.2. Тестирование

**Задачи:**

1. Создать тесты для `ModelSelector`
2. Создать тесты для `FunctionCallProtocol`
3. Создать тесты для `AdaptiveApprovalService`
4. Создать тесты для `MetaLearningService`
5. Создать интеграционные тесты для полного цикла

**Приоритет:** Высокий

## Порядок реализации

1. **Этап 1.1** - ModelSelector (1-2 дня)

   - После завершения: очистка корня проекта, документация, коммит

2. **Этап 1.2-1.3** - Function Calling Protocol (2-3 дня)

   - После завершения: очистка корня проекта, документация, коммит

3. **Этап 4.1** - Code Execution Sandbox (2-3 дня) - критично для безопасности

   - После завершения: очистка корня проекта, документация, коммит

4. **Этап 2.1** - Adaptive Approval Service (2 дня)

   - После завершения: очистка корня проекта, документация, коммит

5. **Этап 3.1** - Meta-Learning Service (3-4 дня)

   - После завершения: очистка корня проекта, документация, коммит

6. **Этап 3.2** - Feedback Learning Service (2 дня)

   - После завершения: очистка корня проекта, документация, коммит

7. **Этап 3.3** - Planning Metrics Service (1-2 дня)

   - После завершения: очистка корня проекта, документация, коммит

8. **Этап 2.2** - Interactive Execution Service (2-3 дня)

   - После завершения: очистка корня проекта, документация, коммит

9. **Этап 5** - Интеграция и тестирование (2-3 дня)

   - После завершения: финальная очистка, документация, коммит

**Общее время: 17-24 дня**

## Стандартная процедура завершения этапа

**Перед переходом к следующему этапу (обязательно):**

1. **Очистка корня проекта:**

   - Удалить временные тестовые файлы (`test_*.py`, `*_test.py` в корне)
   - Удалить временные скрипты миграций (`apply_*_migration.py`, `verify_*_migration.py`)
   - Удалить временные markdown файлы с результатами тестов
   - Оставить только production код и документацию в `docs/`

2. **Документация:**

   - Создать/обновить документацию в `docs/guides/` для новых компонентов
   - Обновить `README.md` если нужно
   - Добавить примеры использования в документацию

3. **Коммит:**

   - Создать коммит с понятным сообщением: `feat: [Название этапа] - описание`
   - Убедиться, что все изменения закоммичены
   - Не оставлять незакоммиченных изменений перед следующим этапом

**Это правило применяется ко ВСЕМ этапам без исключения.**

## Зависимости

- ModelSelector не зависит от других компонентов
- Function Calling Protocol нужен для PlanningService и ExecutionService
- Sandbox критичен для безопасного выполнения кода
- Adaptive Approval улучшает существующий ApprovalService
- Meta-Learning зависит от наличия данных выполнения
- Feedback Learning зависит от ApprovalService