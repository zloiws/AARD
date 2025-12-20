BLOCK A — Backend core stabilized (90% DONE)

Фактически закрыто:

planning integration

agent dialogs

memory/vector

real LLM dialogs

Оставшееся здесь:

triage_import_errors → fix_import_errors

run_full_backend_tests_after_fixes

👉 Это один логический подблок, а не 5–6 задач.

🧪 BLOCK B — Test hygiene & scope alignment

Сюда относятся:

run_full_backend_incremental

остаточные unit/integration несостыковки

флаги RUN_API_INTEGRATION_TESTS, real LLM и т.д.

Это не про фиксы, а про:

какие тесты обязательны,

какие опциональны,

какие manual-only.

🖥 BLOCK C — UI validation (отдельный домен)

UI сейчас:

не блокирует backend

не влияет на архитектурную корректность

Поэтому:

run_ui_tests

run_full_tests

create_changelog

👉 Это отдельный этап, не смешивать с backend.

BLOCK A: Backend Core Stabilization
- Fix remaining import/module errors
- Run full backend tests once
STATUS: COMPLETED

BLOCK D: Import hygiene + final backend run
- Triage import/module errors and fix (unit by unit)
- Re-run backend tests incrementally; split into blocks if >3 failures
- Final full backend run with real LLMs (ENABLE_TRACING=0)
STATUS: IN_PROGRESS

BLOCK E: Planning + dialog loop
- Fix planning ↔ agent dialog integration and conversation lifecycle
- Ensure PlannerAgent compatibility and stubbing for tests
- Run integration tests `test_planning_with_dialogs.py`
STATUS: COMPLETED

BLOCK F: Agent integration / planning integration
- Run `test_agent_planning.py` and `test_planning_api.py`
- Stabilize agent selection and auto-selection in planning
STATUS: COMPLETED

BLOCK G: Memory / Vector / Embeddings
- Ensure `AgentMemory.embedding` present and migrations idempotent
- Embedding generation fallback for empty/error cases
- `search_memories_vector` fallbacks when pgvector unavailable
STATUS: COMPLETED

NOTE:
- Current state: We intentionally support both `vector` (pgvector) and `float8[]` storage for `agent_memories.embedding`.
- Rationale: many developer/test environments do not have `pgvector` available; code now writes to whichever form exists and falls back safely.
- Action item (optional): prepare an Alembic migration to convert `embedding` to `vector` in environments where pgvector is available. This is NOT required for correctness and is deferred to final DB migration planning.

BLOCK H: Ollama integration & model selection
- Health checks and discovery of configured servers
- Improve model selection heuristics and fallback behavior
- Ensure tests can run with remote Ollama instances if localhost absent
STATUS: IN_PROGRESS

BLOCK I: Execution & Tracing stability
- Allow disabling DB span export during tests (ENABLE_TRACING)
- Prevent tracing errors when execution_traces table missing
- Normalize datetimes for duration calculations
STATUS: COMPLETED

BLOCK J: Meta-learning service
- Add sync wrapper and async variant for analyze_execution_patterns
- Update callers to avoid unawaited coroutine warnings
STATUS: COMPLETED

BLOCK K: Testing infra & fixtures
- Stabilize `tests/conftest.py`, create tables reliably (no DROP SCHEMA)
- Add fixtures for scripts tests and system settings
- Ensure tests run on Windows (encoding fixes)
STATUS: COMPLETED

BLOCK L: UI Validation (Vitest)
- Install UI dev dependencies
- Run UI test suite and fix failures
STATUS: NOT_STARTED

BLOCK M: Changelog & final commit summary
- Create `docs/CHANGELOG_FEATURE_UI_ARCHITECTURE_ALIGN.md`
- Produce final commit summary for merge into `main`
STATUS: NOT_STARTED

BLOCK B: Test Scope Definition
- Define mandatory vs optional tests
- Document env flags and expectations
STATUS: NOT_STARTED

BLOCK C: UI Validation
- Run UI tests
- Final changelog
STATUS: NOT_STARTED


