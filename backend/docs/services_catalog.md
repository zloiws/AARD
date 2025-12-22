# Сервисная карта backend (AARD) — каталог сервисов и модулей

Документ подготовлен в соответствии с `docs/context/ARCHITECTURE_LAW.md` и `docs/context/SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md`.
Задача: для каждого сервиса — роль, перечисление модулей с краткой ролью, входы/выходы и статус готовности (поля, требующие ручной проверки, помечены как "VERIFY").

---

## 1. Application Core
Роль: инфраструктурный фундамент — загрузка конфигурации, DB, оркестрация запросов, tracing/metrics, регистрация сервисов.

Ключевые модули:
- `app.core.config` — загрузка `Settings` (env/.env). Входы: env; Выходы: Settings. Готовность: registered config usage — OK.
- `app.core.database` — engine/SessionLocal, регистрация моделей. Входы: DB URL; Выходы: Session, engine. Готовность: OK.
- `app.core.auth` — аутентификация/утилиты для маршрутов. Входы: credentials/context; Выходы: user/principal. VERIFY: покрытие тестами.
- `app.core.service_registry` — runtime registry/lookup API. Входы: регистрация при старте; Выходы: lookup. Готовность: важный контракт.
- `app.core.request_orchestrator` — единая точка оркестрации входящих запросов, выбор маршрута. Входы: request context; Выходы: orchestration result.
- `app.core.request_router` — роутинг типов запросов (RequestType). Роль: lightweight router.
- `app.core.workflow_engine`, `workflow_tracker` — управление lifecycle планов/выполнений. Ключевой для контроля стадий (DRAFT→APPROVED→EXECUTING…).
- `app.core.model_selector` — выбор модели/инстанса для LLM-вызовов. VERIFY: system prompt assignment path.
- `app.core.ollama_client`, `ollama_db_client`, `ollama_manager` — адаптеры к Ollama (см. Tools).
- `app.core.metrics`, `tracing`, `trace_exporter`, `logging_config` — observability.

Inputs: env/settings, HTTP/worker requests, DB. Outputs: Sessions, registered services, traces, metrics.

Readiness notes:
- Contract: core предоставляет общие API; все сервисы обязаны использовать его контракты.
- VERIFY: наличие unit tests на auth/model_selector; prompt assignment must be checked against PromptSelector (per ARCHITECTURE_LAW).

---

## 2. HTTP API Layer
Роль: внешняя граница — FastAPI handlers, валидация входов и делегирование в бизнес-слой.

Ключевые модули:
- `app.main` — FastAPI приложение, lifespan, инициализация middleware/metrics.
- `app.api.routes.*` — коллекция маршрутов (см. список файлов в `app/api/routes/`), каждый маршрут:
  - роль: перевод HTTP → вызовы сервисов; валидация входа через Pydantic; авторизация.
  - входы: HTTP requests; выходы: JSON responses / status codes.

Readiness notes:
- Обязателен OpenAPI (FastAPI генерирует). Для каждой конечной точки нужен контракт (Input DTO / Output DTO) и тесты (VERIFY наличие контрактов в `docs/`).

---

## 3. Data / ORM Layer
Роль: доменные сущности и миграции.

Ключевые модули:
- `app.models.*` — SQLAlchemy модели (см. `app/models/` список): Plan, Task, Agent, Prompt, ChatSession, ExecutionGraph, Artifact, Approval и т.д.
- `app.core.database` — metadata registration.
- `alembic/*`, `backend/sql/*` — миграции и SQL-скрипты.

Inputs: DB connections, service calls. Outputs: persisted entities, schema migrations.

Readiness notes:
- Миграции — ряд скриптов дублируют функционал (см. раздел "Unused / To Consolidate"). Все миграции должны быть идемпотентны (SERVICE checklist).

---

## 4. Business Services
Роль: основная доменная логика (планирование, выполнение, очереди, метрики, артефакты).

Ключевые модули (выборочно, ключевые):
- `app.services.planning_service` — создание/управление планами. Inputs: requests; Outputs: Plan entities. VERIFY: system prompt usage (if component uses LLM).
- `app.services.execution_service` — исполнение шагов плана, StepExecutor. Критично для lifecycle transitions.
- `app.services.agent_service`, `agent_registry` — управление агентами, lifecycle.
- `app.services.agent_dialog_service` — диалоговые сценарии агентов.
- `app.services.ollama_service` — высокоуровневый сервис работы с моделями (взаимодействует с core.ollama_*).
- `app.services.agent_gym_service`, `agent_experiment_service` — экспериментальная/bench сервисы.
- `app.services.prompt_service`, `prompt_runtime_selector` — работа с prompts; важно для CONTRACT law.
- `app.services.audit_scheduler`, `project_metrics_service`, `plan_evaluation_service` — observability/quality.

Inputs: API calls, DB models, tool results. Outputs: domain changes, events, metrics.

Readiness notes:
- Каждый сервис должен иметь documented Input/Output DTO; проверить наличие `docs/services/<service>.md` для приоритета. Многие сервисы уже покрыты тестами (check `backend/tests/`), но VERIFY per-service.

---

## 5. Agents & Planning
Роль: реализация агентов (Component + Capabilities) и lifecycle планирования.

Ключевые модули:
- `app.agents.base_agent` — базовый класс агента; роль: контракт для агентов (system prompt handling should be here). VERIFY: system prompt prop.
- `app.agents.planner_agent` — агент для планирования.
- `app.agents.coder_agent` — агент для генерации/выполнения кода; взаимодействует с `app.tools.code_execution_sandbox` / `code_execution_sandbox`.
- `app.agents.simple_agent` — легковесный агент для простых задач.
- `app.planning.lifecycle` — управление стадиями плана, интеграция с WorkflowEngine.

Inputs: tasks/prompts, memory/context, tool outputs. Outputs: plans, actions, messages.

Readiness notes:
- Agents are Components per ARCHITECTURE_LAW and must have system prompts and be registered in Registry. VERIFY registration and prompt_id/prompt_version.

---

## 6. Decision / Interpretation Components
Роль: компоненты мышления (компоненты, использующие LLM) — интерпретация, валидация, маршрутизация, рефлексия.

Ключевые модули:
- `app.components.interpretation_service` — перевод запросов в structured intents.
- `app.components.planning_service` — вспомогательный компонент для планирования (component-level).
- `app.components.decision_routing` — маршрутизация решений.
- `app.components.execution_validator`, `semantic_validator` — валидация ожидаемого выполнения.
- `app.components.reflection_service` — сбор и анализ результатов (рефлексия).
- `app.services.reflection_service` — service-layer wrapper (обрабатывает результаты рефлексии).

Inputs: intermediate outputs, prompts, request context. Outputs: validated decisions, prompts, routing decisions.

Readiness notes:
- По закону Component — обязателен system prompt, контракт вход/выход; если отсутствует — FAIL для оркестрации. Для каждого модуля: VERIFY system_prompt presence and PromptAssignment entries.

---

## 7. Tools / External Integrations
Роль: реализация возможностей исполнения (Capabilities) — Ollama, web search, python sandbox.

Ключевые модули:
- `app.tools.base_tool`, `python_tool`, `web_search_tool` — стандартный интерфейс инструментов.
- `app.core.ollama_client`, `ollama_db_client`, `ollama_manager` — уровни интеграции с Ollama (HTTP client, DB-backed client, orchestration/manager).
- `app.services.code_execution_sandbox` — изолированное исполнение кода.

Inputs: tool requests, prompts (если нужен LLM). Outputs: tool results, artifacts, errors.

Readiness notes:
- Tools — Capability per ARCHITECTURE_LAW (system prompt not required). VERIFY sandbox isolation tests and permission boundaries.

---

## 8. Registry / Service Discovery
Роль: единый реестр (Registry) — единственный источник правды для агентов, capabilities и версий.

Ключевые модули:
- `app.registry.service`, `app.core.service_registry` — API регистрации/lookup.

Readiness notes:
- По закону Registry обязателен; все компоненты/агенты/capabilities должны быть зарегистрированы. Проверить отсутствие дубликатов при регистрации (VERIFY).

---

## 9. Security / Auth / Permissions
Роль: аутентификация/авторизация и проверка прав.

Ключевые модули:
- `app.security.*` (пустой пакет/модули) и `app.core.auth`, `app.core.permissions`.

Readiness notes:
- Все external endpoints должны использовать auth middlewares; VERIFY coverage for admin/ops scripts.

---

## 10. Memory / Conversation Storage
Роль: хранение диалогов/памяти агентов.

Ключевые модули:
- `app.memory.*` (helper инфраструктура).
- `app.models.agent_memory`, `agent_conversation`, `chat_session`.

Readiness notes:
- Memory должен предоставлять API для prompt selection и retrieval; VERIFY data retention & PII redaction policies.

---

## 11. Ops / Maintenance / Migrations
Роль: CLI/скрипты для миграций, seed, проверки состояния БД и админ-утилиты.

Ключевые файлы:
- `apply_migrations.py`, `apply_single_migration.py`, `run_migration.py`, `run_migration_fixed.py`, `update_alembic_version.py`, `scripts/*` миграции/seed.

Issues:
- Множество скриптов дублируют логику (см. `backend/docs/duplicate_modules.json`). Рекомендация: консолидация в CLI.

Readiness notes:
- Scripts must run idempotently; verify runbook and add to `docs/roadmap/migration_runbook.md`.

---

## 12. Utilities / Observability
Роль: metrics, tracing, logging, templates, utils.

Ключевые модули:
- `app.core.metrics`, `tracing`, `trace_exporter`, `logging_config`, `app.core.meta_tracker`.

Readiness notes:
- Observability events must include `component`, `prompt_id` (if LLM used), `decision_source`, `input_summary`, `output_summary`.

---

## Unused / To archive / Needs consolidation (current status)
Ниже — список модулей/скриптов, которые на текущем этапе требуют действий (архив/консолидация/проверка). Статусы даны рекомендационно.

1) Миграции / DB scripts — статус: NEEDS_CONSOLIDATION
   - `apply_migrations.py`, `apply_single_migration.py`, `apply_timezone_migration.py`, `run_migration.py`, `run_migration_fixed.py`, `update_alembic_version.py`, `scripts/autogen_and_apply_migration.py`, `scripts/patch_migrations_idempotent.py`, `migrate_now.py`
   - Роль: применение/анализ миграций. Рекомендация: объединить в `backend/cli/migrations.py` с subcommands.

2) Server runners / wrappers — статус: REDUNDANT (keep minimal)
   - `run.py`, `run_alembic_upgrade.py`, `start_server_with_venv.ps1`, `start_server.bat`, `start_all.bat`
   - Роль: облегчение локального запуска; оставить 1 cross-platform runner + platform helpers.

3) Health / check scripts — статус: TO_BE_UNIFIED
   - `check_tables.py`, `check_missing_tables.py`, `check_db_state.py`, `check_artifacts_integration.py`, plus many `scripts/check_*`
   - Роль: проверки состояния; объединить в `tools/checks.py`.

4) Temp / one-off scripts — статус: ARCHIVE or MIGRATE_TO_CLI
   - `tmp_add_embedding.py`, `tmp_drop_all_tables.py`, `tmp_fix_trace_index.py`, `tmp_list_indexes.py`, `tmp_rename_agents.py`, other `scripts/tmp_*`
   - Роль: одноразовые админ-утилиты; либо архив, либо интегрировать в namespaced CLI.

5) Ollama-related modules — status: REVIEW_REQUIRED
   - `app/core/ollama_client.py`, `app/core/ollama_db_client.py`, `app/core/ollama_manager.py`, `app/services/ollama_service.py`
   - Роль: интеграция с LLM-инстансом; нужно сверить ответственность (client vs db adapter vs orchestrator) и удалить дубли.

---

## Предложения по следующему шагу (конкретно)
1. Провести ревизию и создать `backend/cli` с командами: `migrate`, `check`, `seed`, `render-prompts`, `archive-tmp`. (PR: move + tests).
2. Для каждого компонента (модуля из `app.components.*` и `app.services.*`) заполнить `docs/services/<service>.md` с контрактами: Input DTO, Output DTO, Errors, LLM usage (system_prompt id/version), owner. (Я могу сгенерировать шаблоны и начать автозаполнение).
3. Провести аудит `app/core/ollama_*` и `app/services/ollama_service.py` — собрать повторы функций/API и предложить refactor.

---

Если задача понятна — начну:
- Шаг A: создать шаблоны `docs/services/<service>.md` и автозаполнить для `Application Core`, `Business Services`, `Agents`, `Tools`.
- Шаг B: собрать список владельцев (owner) — VERIFY (нужна информация от команды).

Сообщите, начинаю ли автозаполнение шаблонов (A) сейчас. Спасибо. সামনে.  ✨
{"generated_by":"assistant"}


