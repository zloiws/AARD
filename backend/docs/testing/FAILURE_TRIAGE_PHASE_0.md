# FAILURE_TRIAGE_PHASE_0

Date: 2025-12-21
Author: Automated triage (assistant)

Purpose
-------
Document triage (NOT fixes) of failures observed during the non-real-LLM test run. For each failing test we record the observed error, a root‑cause hypothesis and classification (defect / test / architecture / docs). This file is an artifact for human review and prioritization.

Key rule
--------
Triage ≠ Fixing. Do not change code based solely on this document. If fix is allowed now it means the issue is safe to correct (test hygiene, mocks, minor setup); otherwise human review required.

Table of failures
-----------------

| Test | Error (observed) | Root cause (hypothesis) | Category | Fix allowed now? |
| --- | --- | --- | ---: | :---: |
| tests/test_plan_template_extraction.py::TestPlanTemplateExtraction::test_extract_template_on_plan_completion | TypeError: 'Mock' object is not subscriptable (in get_template) | Service expects raw SQL row/tuple returned by `fetchone()`; unit test provides Mock/ORM mock; incompatible I/O contract | Architecture mismatch / Test integration | ❌ |
| tests/test_plan_template_service.py::TestPlanTemplateService::test_extract_template_from_plan_success | TypeError: 'Mock' object is not subscriptable | Same as above — raw SQL vs mocked ORM objects mismatch | Architecture mismatch / Test integration | ❌ |
| tests/test_plan_template_service.py::TestPlanTemplateService::test_get_template | TypeError when indexing row | get_template assumes row is indexable; Mock returned by test isn't; fragility in raw-SQL handling | Test setup / Code robustness | ✅ |
| tests/test_plan_template_service.py::TestPlanTemplateService::test_update_template_usage | Attribute/assertion failures when commit/refresh called on Mock | Service assumes DB objects with attributes; the test's Mock semantics differ | Test setup | ✅ |
| tests/test_plan_tree_service.py::TestPlanTreeService::test_empty_steps | Assertion or parsing error for steps field | Data type mismatch: code expects list or JSON but test fixture supplies different form (string/None) | Test setup / Data contract | ✅ |
| tests/test_planning_with_teams.py::test_plan_with_team* (multiple) | AttributeError / Assertion failures during team selection | Missing or incomplete mocks for Agent/Team services or reliance on network calls; test expects in-memory DB + fixtures | Test hygiene (mocks) | ✅ |
| tests/test_request_orchestrator.py::test_request_orchestrator_initialization | Initialization error (missing context/registry) | Orchestrator requires ServiceRegistry/ExecutionContext; fixture not provided in test | Test setup | ✅ |
| tests/test_service_registry.py::test_service_registry_get_service_with_db / _with_context | Service lookup failures / None responses | ServiceRegistry not initialized with expected providers in test environment | Test setup / Config | ✅ |
| tests/cli/test_migrations_cli.py::test_build_parser_and_call_migrate | CLI parser/migrate invocation error | Test assumes CLI entrypoints or scripts present/available; parser API changed or path issue | Test hygiene / CLI contract | ✅ |
| tests/docs/test_service_docs_present.py::test_service_docs_exist | AssertionError: missing docs/service file(s) | Missing documentation artifacts in `backend/docs/services/` (docs gap) | Documentation | ❌ |
| tests/integration/test_dashboard_api.py::test_dashboard_statistics | Assertion or data mismatch (dashboard stats) | Integration test depends on seeded metrics/data not present in environment | Integration / Environment | ✅ (if seeding ok) |
| tests/integration/test_planning_digital_twin.py::Test4ComplexTask::test_complex_task_planning | Complex failure / exceptions during planning pipeline | Integration-level dependencies (models, prompts, registry) not configured in test DB | Integration / Environment / Architecture | ❌ |
| tests/integration/test_prompt_ab_testing.py::* | Assertion failures for AB testing logic | Prompt assignment/versioning behavior changed or missing seed data; tests expect specific prompt_version data | Architecture / Prompt contracts | ❌ |
| tests/integration/test_prompt_auto_improvement.py::test_analyze_and_improve_prompts_low_success_rate | Failure in analysis/improvement pipeline | Requires prompt metrics and history in DB; missing seed data or mock | Integration / Data | ❌ |
| tests/test_agent_dialog_api.py::* (setup errors) | ModuleNotFoundError / setup errors | Import/path issues or conftest fixtures not visible (sys.path or backend path problems) | Test setup / Environment | ✅ |
| Asyncio warning: "Task was destroyed but it is pending" | Background async tasks created with asyncio.create_task not awaited or test loop torn down | Lifecycle mismatch: background tasks not awaited in test harness; code creates background tasks in production flows | Architecture / Runtime | ❌ |
| Unexpected LLM HTTP requests observed in non-real run | Calls to Ollama endpoints appeared in logs | Some code paths still call LLM clients during non-real tests (insufficient mocking or gating) | Test hygiene / Missing gate | ✅ |

Notes & evidence
----------------
- Multiple "Mock not subscriptable" traces point at `backend/app/services/plan_template_service.py:get_template` (raw SQL path). Unit tests mock `db.query`/ORM‑style but service expects raw SQL rows — mismatch. See log lines with "Error extracting template... 'Mock' object is not subscriptable".
- Asyncio pending task appears from `ExecutionService._analyze_patterns_async` background invocation (create_task). Tests tear down event loop and cause "Task was destroyed but it is pending".
- ModuleNotFound/setup errors in agent dialog API tests indicate test imports rely on `backend` being on sys.path; conftest normally adds it but some tests run in a different import context.
- HTTP calls to `10.39.0.101:11434` appear in logs even when `RUN_REAL_LLM_TESTS` was not set for some runs — indicates either some tests call live LLM or earlier environment had env set; ensure gate/fixture works and no hardcoded server usage exists.

Classification legend
---------------------
- Fix allowed now? ✅ — safe to modify test fixtures, mocks or small code guards to make unit tests deterministic. No architectural contract change.
- Fix allowed now? ❌ — requires human review, architecture/contract change, docs update, or environment provisioning (not safe to auto-fix).

Recommended next steps (triage → prioritization)
------------------------------------------------
1. Human review items marked ❌ (architecture/docs/integration) and decide ownership/prioritization. Attach to Phase gate.  
2. For ✅ items create small focused tasks: fix mocks, improve ORM/raw-SQL fallbacks, ensure conftest sys.path handling. Prefer unit-fix PRs with CHANGELOG entry.  
3. Add a CI runner wrapper that runs non-real tests with `-m "not real_llm"` and `--junitxml` and stores logs under `logs/` to avoid lost output.  
4. Add a test‑hygiene checklist for contributors: always mark heavy tests with `real_llm`/`slow`, seed DB for integration tests, and avoid background create_task in code paths executed by unit tests (or guard them behind `if not in_test_mode`).

Change record
-------------
Filename: `backend/docs/testing/FAILURE_TRIAGE_PHASE_0.md` created by automated triage run.


