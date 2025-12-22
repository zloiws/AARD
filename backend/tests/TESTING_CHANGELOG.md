# TESTING_CHANGELOG

Each entry documents a single change performed during testing runs.

Required fields:
- date: YYYY-MM-DD
- author: Name <email>
- change_id: short-id
- scope: test-only | fixture-only | code-bugfix | env-change
- summary: short description
- rationale: why change was needed
- verification: how change was verified (commands, pytest invocations)
- rollback: how to rollback

Example:

---
date: 2025-12-21
author: Tehno <tehno@example.com>
change_id: add_real_llm_gate_001
scope: test-only
summary: Skip real_llm tests unless RUN_REAL_LLM_TESTS=1
rationale: Prevent accidental execution of heavy/live tests in CI/local runs
verification: `env RUN_REAL_LLM_TESTS=0 pytest -q -m real_llm` should skip tests
rollback: remove entry and revert conftest change
---


---
date: 2025-12-21
author: automated-runner <ci@example.com>
change_id: testing_inventory_001
scope: test-only
summary: Generate test inventory and suggested markers (TEST_MATRIX.md)
rationale: Create a central inventory to plan non-real and real-LLM test runs
verification: `python tools/generate_test_matrix.py` produced `backend/tests/TEST_MATRIX.md`
rollback: remove TEST_MATRIX.md and revert any downstream usage
---

---
date: 2025-12-21
author: automated-runner <ci@example.com>
change_id: testing_reports_001
scope: test-only
summary: Collected test run reports and rerun summaries
rationale: Aggregate failures and errors for triage
verification: reports generated: `reports/non_real.xml`, `reports/full_with_real_enabled.xml`, `reports/failed_rerun_summary.csv`
rollback: remove reports/ files if needed
---

---
date: 2025-12-22
author: automated-runner <ci@example.com>
change_id: testing_marks_and_stubs_001
scope: test-only
summary: Register pytest custom marks and add test-only stub fixtures
rationale: Suppress UnknownMark warnings and provide safe test stubs to surface logic defects during triage
verification: `pytest -q -m "not real_llm"` runs; `reports/failed_rerun_perfile/*` created for reruns
rollback: remove added fixtures and pytest.ini entries, update TESTING_CHANGELOG
---

