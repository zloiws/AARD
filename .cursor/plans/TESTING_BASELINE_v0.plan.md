# TESTING_BASELINE_v0 — Backend тестирование (AARD)

## Non-goals (обязательные предохранители)

- Tests must **not** drive architectural changes.
- Failing tests indicate either:
- a) a defect in implementation, or
- b) an outdated / incorrect test.
- In case of ambiguity, architecture documents take precedence over tests.
- If a test requires changing `docs/context/ARCHITECTURE_BASELINE_v0.md` or `docs/context/ARCHITECTURE_LAW.md`, the test is considered **invalid until reviewed by a human**.

## Цель

- Получить **полностью работающий backend** через управляемый прогон тестов: модульно → сервисно → интеграционно → workflow/end‑to‑end, с отдельным треком **Live Environment Validation** (реальные LLM вызовы на remote Ollama).

## Термины и нормализация уровней тестов

| Было | Норма (используем дальше) || --- | --- || Smoke / Sanity | **Boot & Liveness** || Unit tests | **Pure Unit** || Contract tests | **Architectural Contracts** || Service tests | **Service Integration (LLM-mocked)** || Integration tests | **System Integration** || End-to-End | **Workflow Scenarios** || Real‑LLM tests | **Live Environment Validation** |

## Протокол документирования изменений (ОБЯЗАТЕЛЬНО)

### Принцип

Любое изменение в ходе тестирования должно быть **наблюдаемым, атрибутируемым и обратимым**.

### Что считается “изменением”

- изменения тестов (маркеры, фикстуры, ожидания, таймауты);
- изменения кода backend, сделанные ради прохождения тестов;
- изменения конфигурации/переменных окружения/seed‑процедур, влияющие на прогон.

### Обязательные артефакты на каждое изменение

- **Change Record**: краткая запись “что/почему/чем проверено/как откатить”.
- формат: один блок в `backend/tests/TESTING_CHANGELOG.md` (будет создан) или отдельный файл `docs/reports/testing_runs/YYYY-MM-DD_change_<id>.md`.
- **Обновление TEST_MATRIX**: если изменение влияет на категорию/зависимости/время выполнения.
- файл: `backend/tests/TEST_MATRIX.md` (будет создан).
- **Граница изменения**: в записи явно указать, что изменялось:
- test-only / fixture-only / code-bugfix / env-change.

### Дополнительное требование по сервисам (контрактный закон)

Если изменяется поведение сервиса (не просто “фикс бага”), требуется обновить соответствующий `docs/services/<service>.md` (если такой документ существует/должен существовать по `ARCHITECTURE_LAW.md`).

## Категории и подкатегории тестов (что именно тестируем)

### A. Boot & Liveness (самые быстрые проверки)

- **Import & config**: импорт `backend/app/**`, загрузка env через `backend/app/core/config.py`.
- **DB connectivity**: создание engine/session в `backend/app/core/database.py`, базовая транзакция.
- **API liveness**: старт FastAPI приложения и базовый endpoint через `TestClient`.

### B. Pure Unit (без сети и без реальной БД)

- **Core**: `app/core/*` (selectors, prompt runtime selector, small logic).
- **Models**: `app/models/*` (валидации/enum/serialization).
- **Utilities**: helper‑функции без внешних зависимостей.

### C. Architectural Contracts (контракты и инварианты)

- **Docs/service presence**: `backend/tests/docs/test_service_docs_present.py`.
- **API consistency**: `backend/tests/test_contracts_api.py`, `backend/tests/integration/test_phase6_api_consistency.py`.
- **Events contracts**: `backend/tests/test_workflow_event_contract.py`, `backend/tests/scripts/test_workflow_events*.py`.

### D. DB & Migrations

- **Alembic миграции**: `backend/tests/integration/test_migration.py` и связанные скрипты.
- **pgvector/extension**: `backend/tests/integration/test_vector_search*.py` (и graceful‑fallback при недоступности).

### E. Service Integration (LLM-mocked)

- Planning/Reflection/Memory/Orchestrator тестируются с моками LLM, проверяя контракты вход/выход и статусы.

### F. System Integration (реальная БД, реальные сервисы, LLM не обязателен)

- Тесты с `@pytest.mark.integration` и `backend/tests/integration/*`, где LLM либо мокается, либо тест корректно `skip` при отсутствии.

### G. Workflow Scenarios (E2E по фазам)

- Phase 3/4/5/6 сценарии нарастающей сложности:
- `backend/tests/integration/test_phase3_full_integration.py`
- `backend/tests/integration/test_workflow_engine.py`
- `backend/tests/integration/test_phase4_integration.py`
- `backend/tests/integration/test_phase5_e2e_workflows.py`
- `backend/tests/integration/test_phase6_consistency.py`

### H. Live Environment Validation (real LLM, remote Ollama) — отдельный трек

#### Жёсткие правила

- Rule: `real_llm` tests are **observational, not blocking**.
- Their failure never blocks backend readiness.
- Their purpose is environment validation, not correctness proof.
- Any retry/timeout tuning in `real_llm` tests must **not** leak into non-real tests.

#### Примеры live‑LLM файлов

- `backend/tests/integration/test_agent_dialogs_real_llm.py`
- `backend/tests/integration/test_real_llm_full_workflow.py`
- `backend/tests/integration/test_agent_teams_real_llm.py`
- (долго) `backend/tests/integration/test_model_benchmark_real.py`

## Подготовка окружения под ваши условия (existing Postgres + remote Ollama)

### DB (existing Postgres)

- Используем `POSTGRES_HOST/PORT/DB/USER/PASSWORD` (см. `backend/app/core/config.py`).
- Требование: пользователь должен иметь права на миграции/DDL, включая `CREATE EXTENSION` (если требуется `vector`).

### LLM (remote Ollama)

- Используем `OLLAMA_URL_1`, `OLLAMA_MODEL_1` (+ опционально `*_2`).
- Требование: remote Ollama доступен по сети; модели загружены/доступны.

## Порядок прогонки (фазы) + STOP/GO gates

### Phase 0 — Инвентаризация и разметка

- Сбор тестов → раскладка по категориям → заполнение `TEST_MATRIX`.
- Нормализация маркеров, особенно `real_llm`.

**Gate after Phase 0 (STOP and report)**:

- `TEST_MATRIX` создан и отражает текущую реальность
- есть протокол Change Record (куда писать и как)

### Phase 1 — Boot & Liveness + Architectural Contracts

- Запуск быстрых тестов и контрактов (без live LLM).
- Фиксация и устранение критических проблем (без архитектурных изменений).

**Gate after Phase 1 (STOP and report)**:

- All Boot & Liveness + Architectural Contracts green
- No architectural violations introduced

### Phase 2 — DB & Migrations + System Integration (без live LLM)

- Прогон миграций против existing Postgres.
- Интеграционные тесты без `real_llm`.

**Gate after Phase 2 (STOP and report)**:

- DB/migrations + System Integration green (или чёткий список блокеров среды)
- Все изменения оформлены Change Records

### Phase 3 — Workflow Scenarios (Phase 3/4/5/6)

- Прогон фазовых сценариев, стабилизация workflow.

**Gate after Phase 3 (STOP and report)**:

- Workflow Scenarios green (или чёткий список блокеров с reproduction)
- Нет “оптимизаций ради теста” вне области дефекта

### Phase 4 — Live Environment Validation (remote Ollama)

- Диагностика соединения и доступности моделей.
- Запуск `real_llm` трека только при явном флаге (например `RUN_REAL_LLM_TESTS=1`).
- Отчёт по среде: latency, timeouts, ошибки/коды, стабильность.

**Gate after Phase 4 (STOP and report)**:

- Сформирован отчёт по live‑среде; backend readiness не блокируется падениями live‑LLM

## “Cursor instruction” (норматив для исполнения плана)

You are executing `TESTING_BASELINE_v0`.You may only:

- work within the currently declared phase;
- modify test markers, fixtures, or code strictly required to make tests pass;
- record every change (Change Record) and update TEST_MATRIX when needed;
- stop after completing the phase and report.

You may not:

- refactor unrelated code;
- introduce new abstractions;
- change architecture documents.

## Testing Stabilization Plan (v0) — actionable anchor

Status:

- TEST_MATRIX: in_progress
- MARKERS_NORMALIZED: in_progress
- REAL_LLM_GUARD: done
- NON_REAL_RUN: in_progress

Rules:

- No code fixes that change service I/O or architecture until Phase gates are passed.
- Allowed during stabilization: test metadata, markers/skips, small defensive guards, conftest improvements, runner scripts.

STEP 0 — Anchor (one-time)

- Create `backend/docs/testing/TESTING_STABILIZATION_PLAN.md` as single source of truth for stabilization steps and BLOCK_STATUS.
- This file documents Active Block scope, allowed changes, and BLOCK_STATUS after each batch.

STEP 1 — TEST_MATRIX (static, file-by-file)

- Create or update `backend/tests/TEST_MATRIX.md`. Work folder-by-folder; for each test file add one line:
- File | Category | Markers | DB | LLM | Notes
- Do not run tests while building the matrix. This is static inventory only.

STEP 2 — Normalize markers (no runs)

- For each test file (one file at a time):
- If it touches DB → add `@pytest.mark.integration`
- If it performs LLM/HTTP → add `@pytest.mark.real_llm` and ensure skip gating
- If long → add `@pytest.mark.slow`
- Replace hardcoded endpoints with env/config usage (`OLLAMA_URL_*`)
- Add `pytest.skip()` guarded by env flag when appropriate
- Do not change assertions or business logic in this step.

STEP 3 — Safe-guard live-LLM (central)

- Ensure `backend/tests/conftest.py` includes centralized guard: skip `real_llm` unless `RUN_REAL_LLM_TESTS=1`.
- Ensure `RUN_REAL_LLM_TESTS` default is `"0"` in CI/local runs.

STEP 4 — Controlled non-real runs (chunked)

- Never run the entire suite at once. Run by small groups:
- `python -m pytest tests/docs -q --junitxml=reports/docs.xml`
- `python -m pytest tests/test_* -q --junitxml=reports/unit.xml`
- `python -m pytest tests/integration -m "not real_llm" -q --junitxml=reports/integration.xml`
- Redirect stdout/stderr to per-run log files under `logs/`.

STEP 5 — Iterative fixes (only ✅ items per triage)

- Follow strict priority order:
- Priority 1: Test hygiene & deterministic environment (LLM gating, sys.path/conftest, runner robustness)
- Priority 2: Mocks & fixtures (ServiceRegistry, orchestrator, team mocks, CLI parser expectations)
- Priority 3: Defensive guards (non-invasive: guard against Mock in get_template, no-op commit in test context)
- Forbidden: changing service I/O formats, merging ORM/raw-SQL semantics, suppressing async lifecycle issues.

BLOCK_STATUS template (add to `backend/docs/testing/TESTING_STABILIZATION_PLAN.md` after completing work)---BLOCK: Test hygiene & deterministic unit stabilizationStarted: 2025-12-21Scope: only ✅ items from FAILURE_TRIAGE_PHASE_0Completed:

- real_llm guard added to conftest (`backend/tests/conftest.py`)
- TEST_MATRIX created (`backend/tests/TEST_MATRIX.md`) — in_progress

Not touched (intentional):

- prompt/versioning contract issues (❌)
- async lifecycle redesign (❌)
- docs completeness (❌)

Remaining ❌ items:

- integration prompts seeding and architectural prompt contracts

Verification:

- Run: `python -m pytest -m "not real_llm" --junitxml=reports/non_real.xml`
- Expected: no new failures in non-real track

---Definition of Done (Active Block)