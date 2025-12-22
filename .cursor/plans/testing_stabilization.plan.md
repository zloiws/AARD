# FAILURE_TRIAGE_PHASE_0 — Stabilization plan (v0)

Краткая цель

- Формализовать triage (артефакт `backend/docs/testing/FAILURE_TRIAGE_PHASE_0.md`) как план работ в `.cursor/plans/` и определить последовательность Active Block для поочерёдного выполнения фиксов.

Контекст и входные артефакты

- Исходный триаж: `backend/docs/testing/FAILURE_TRIAGE_PHASE_0.md`
- Своды прогонов и rerun: `reports/test_failures_summary.csv`, `reports/failed_rerun_summary.csv`, `reports/failed_rerun_perfile/*`
- Текущий Active Block: `Test hygiene & deterministic unit stabilization` (см. `backend/docs/testing/TESTING_STABILIZATION_PLAN.md`)

Конечный результат

- Новый план‑файл в `.cursor/plans/FAILURE_TRIAGE_PHASE_0.plan.md` с:
- декларацией последовательности Active Block,
- простым набором задач/туду на каждый блок,
- ссылками на ключевые артефакты и критерием Done для каждого блока.

Порядок блоков (очередность, приоритет и короткая логика)

1. Test hygiene & deterministic unit stabilization — (DONE/PARTIAL)

- очистка маркеров, central real_llm guard, базовый инвентарь тестов, тест‑stubs.
- DoD: `pytest -m "not real_llm"` без новых падений.

2. Environment & Services readiness

- seed scripts, local mock endpoints, DB extension readiness, no connection refused.
- DoD: интеграционные тесты не падают из‑за недоступности сервисов (или отмечены skip).

3. Test harness & fixtures stabilization

- реализовать/восстановить ожиданные фикстуры (`plan_id`, `execution_context`, `real_model_and_server` и т.д.) и унифицировать conftest.
- DoD: нет "fixture not found" в целевых тестах.

4. CI / Runner hardening

- сделать chunked runs, сохранить логи, junit xml, зарегистрировать marks.
- DoD: CI прогон chunked non‑real стабилен.

5. Entity I/O & Contract stabilization

- устранить raw‑SQL vs ORM mismatch, добавить defensive guards, doc contracts per entity.
- DoD: unit tests по контрактам проходят.

6. Logic / Service fixes (minimal, reviewed)

- исправления Production-кода только после human review + Change Record.
- DoD: targeted failing tests green.

7. Prompt / Model migration & observational validation

- prompt inventory, annotations, run observational real_llm track (non‑blocking).

8. Docs / Per‑entity documentation completion
9. Observability & acceptance
10. Final verification & close block

Ключевые файлы для проверки/изменения

- `backend/docs/testing/FAILURE_TRIAGE_PHASE_0.md` (исходник)
- `backend/docs/testing/TESTING_STABILIZATION_PLAN.md` (статус и BLOCK_STATUS)
- `backend/tests/TEST_MATRIX.md` (инвентарь)
- `backend/tests/TESTING_CHANGELOG.md` (Change Records)
- `backend/tests/conftest.py`, `backend/pytest.ini` (test harness)
- `reports/` — все агрегированные артефакты

Минимальные туду‑элементы (для планирования и трекинга)

- testing-blocks-01: Создать план‑файл `.cursor/plans/FAILURE_TRIAGE_PHASE_0.plan.md` на основе триажа и очереди блоков
- pre-fix-commit: Зафиксировать текущие артефакты (reports, docs, conftest stubs) — snapshot (если не сделан)
- triage-logic: Собрать полный список logic‑failures (из `reports/failed_rerun_perfile/*`) и классифицировать: impl|test|arch|docs
- env-readiness: Сформировать checklist для Environment (OLLAMA, local APIs, DB extensions) и задачи по seed/mocks
- fixtures-stabilize: Реализовать/утвердить отсутствующие фикстуры и унифицировать conftest pour triage runs
- runner-hardening: Создать runner scripts для chunked non‑real runs и CI config notes
- contract-audit: По результатам triage провести audit I/O контрактов и подготовить дефенсивные патчи (или спецификации)
- logic-fixes-queue: Подготовить список minimal patches для сервисов с приоритетами и owners
- prompt-migration: Подготовить prompt inventory и observational run plan
- docs-complete: Список недостающих service docs (из FAILURE_TRIAGE_PHASE_0) и план их создания
- final-verification: Выполнить финальные прогоны и оформить BLOCK STATUS

Зависимости и критерии перехода

- Каждый блок начинается только после DoD предыдущего блока.
- Любые изменения production‑кода требуют human review и запись в `backend/tests/TESTING_CHANGELOG.md`.