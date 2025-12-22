# TESTING_STABILIZATION_PLAN.md — Stabilization plan and BLOCK_STATUS

This document is the single source of truth for the current TESTING stabilization block.
It records the scope, actions taken, change records and the current BLOCK_STATUS.

Block: Test hygiene & deterministic unit stabilization
Started: 2025-12-21
Scope: Test inventory, marker normalization, centralized guards, non‑real test runs, collection of failures, triage, and safe test‑only fixes to enable triage. No production/business‑logic fixes will be applied without explicit approval and a Change Record.

Actions performed (chronological)
- Generated `backend/tests/TEST_MATRIX.md` (inventory of test files and suggested markers).
- Generated suggestions for markers (added `SuggestedMarkers` column).
- Ensured `RUN_REAL_LLM_TESTS` default is `"0"` in `backend/tests/conftest.py`.
- Ran non‑real test suite: `python -m pytest -m "not real_llm" -q --junitxml=reports/non_real.xml`.
- Generated aggregated reports: `reports/test_failures_summary.csv` / `.json`.
- Ran observational real‑LLM marker run: `python -m pytest -m "real_llm" -q --junitxml=reports/real_llm.xml`.
- Ran full test suite with `RUN_REAL_LLM_TESTS=1` and collected `reports/full_with_real_enabled.xml`.
- Extracted failed files list: `reports/failed_test_files.txt`.
- Per‑file reruns for failed files: `reports/failed_rerun_perfile/*` and `reports/failed_rerun.log`.
- Generated rerun summary: `reports/failed_rerun_summary.csv` / `.json`.
- Registered additional pytest marks in `backend/pytest.ini` (integration, slow, timeout, cli, docs, scripts).
- Added non‑invasive test‑only stub fixtures in `backend/tests/conftest.py` to aid triage:
  - `plan_id`, `execution_context`, `workflow_engine` (safe stubs/mocks).
- Appended Change Records to `backend/tests/TESTING_CHANGELOG.md` documenting inventory, reports and test‑stubs.
- Performed targeted reruns after adding stubs; collected `reports/targeted_after_stubs.xml` and updated perfile rerun artifacts.

BLOCK_STATUS
- TEST_MATRIX: completed
- MARKERS_NORMALIZED: completed (suggestions only)
- REAL_LLM_GUARD: completed
- NON_REAL_RUN: completed
- FAILURES_COLLECTED: completed
- TRIAGE_FIXTURE_ISSUES: completed (identified and stubbed core missing fixtures; report: `reports/fixtures_issues.*`)
- TRIAGE_ENVIRONMENT_ISSUES: completed (identified network/DB/Ollama blockers; report: `reports/environment_issues.*`)
- FIXES_APPLIED: partial (test‑only stubs added; no production logic fixes applied)

Change Records
- 2025-12-21: Created test inventory `backend/tests/TEST_MATRIX.md`. (author: automated runner)
- 2025-12-21: Added `SuggestedMarkers` column with recommendations. (author: automated runner)
- 2025-12-21: Set explicit default `RUN_REAL_LLM_TESTS=0` in `backend/tests/conftest.py`. (author: automated runner)
- 2025-12-21: Ran `not real_llm` test suite and saved JUnit XML to `reports/non_real.xml`. (author: automated runner)
- 2025-12-21: Generated `reports/test_failures_summary.csv` and `.json`. (author: automated runner)
- 2025-12-21: Ran observational `real_llm` selection and `full` run with `RUN_REAL_LLM_TESTS=1`. Saved `reports/real_llm.xml` and `reports/full_with_real_enabled.xml`. (author: automated runner)
- 2025-12-21: Collected failing test file list and performed per-file reruns. Generated `reports/failed_rerun_summary.csv`. (author: automated runner)
- 2025-12-22: Registered pytest marks in `backend/pytest.ini` and added test‑only stub fixtures in `backend/tests/conftest.py`. (author: automated runner)
- 2025-12-22: Appended Change Records and performed targeted reruns; generated `reports/targeted_after_stubs.xml` and updated rerun artifacts. (author: automated runner)

Summary statistics (artifacts produced)
- non_real parsed testcases: 781 (reports/non_real.xml)
- full run: tests=1104, failures=13, errors=658 (reports/full_with_real_enabled.xml)
- rerun summary: failures=17, errors=11 (reports/failed_rerun_summary.csv)

Next steps (priority)
1. Commit current stabilization artifacts and documentation (this commit was created to preserve pre‑fix state).
2. Perform full triage of logic/service failures and classify each as: implementation defect, test defect, or architectural/documentation debt.
3. For test‑defects or environment‑gaps, apply safe test‑only fixes/mocks and rerun targeted tests to isolate logic failures.
4. For implementation defects, prepare minimal, well‑scoped patches with accompanying Change Records; do not merge without review.
5. Iterate: targeted rerun → update reports → mark Change Record → proceed to next item.

Notes
- All actions above are documented and reversible. Only test‑oriented, non‑invasive changes have been applied so far (pytest.ini marks and stub fixtures).
- For each subsequent code fix, a Change Record entry must be added to the changelog.
- This file is the authoritative status; update it each time a block status changes.


