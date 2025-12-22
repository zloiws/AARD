# docs/context — AARD architecture & process hub

Purpose
-------
This folder contains the normative architecture rules, operational decisions, readiness checklists and onboarding templates for the AARD backend. It is the starting point for any new chat/agent or human contributor who will work on `backend/app/**`.

Start here (required reading, in order)
--------------------------------------
1. `ARCHITECTURE_BASELINE_v0.md` — canonical execution stages, ExecutionEvent (v0), baseline invariants.
2. `ARCHITECTURE_LAW.md` — normative architecture laws (authoritative).
3. `SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md` — mandatory checklist before orchestration.
4. `docs/api/contracts_v0.md` — API contracts (ExecutionEvent, PromptAssignment).
5. `backend/docs/entities/catalog.md` — backend inventory & classification.
6. `backend/docs/architecture/backend_interactions.md` — pipeline mapping and event emission points.
7. `backend/docs/llm_call_inventory.md` — LLM call inventory and exemptions.
8. `OPERATIONAL_DECISIONS.md` — actionable operational rules and priorities.
9. `CHAT_ONBOARDING.md` — onboarding checklist and quick checks.
10. `onboarding_ack/TEMPLATE_ACK.md` — acknowledgement template: create `docs/context/onboarding_ack/<chat-id>.md` after reading.

Quick checks (before any edit)
------------------------------
- Can you list canonical stages? (`interpretation`, `validator_a`, `routing`, `planning`, `validator_b`, `execution`, `reflection`, `registry_update`)
- Can you list ExecutionEvent (v0) required fields (component_role, component_name, input_summary, output_summary, reason_code, etc.)?
- Is the entity you will change classified in `backend/docs/entities/catalog.md`?
- Does your change touch LLM prompts? If yes — follow PromptAssignment rules or annotate literal prompts with `# LEGACY_PROMPT_EXEMPT`.

Onboarding & approvals
----------------------
- Create `docs/context/onboarding_ack/<chat-id>.md` using `TEMPLATE_ACK.md` to signal readiness to start work.
- If an entity is being prepared for orchestration, run the readiness checklist and record PASS/FAIL in `backend/docs/services/<service>.md` per `ARCHITECTURE_LAW.md` requirements.

Process constraints (must-follow)
-------------------------------
- No refactors/renames/new abstractions without explicit approval.
- Work one phase at a time; stop and produce `BLOCK STATUS` after each phase (see `CURSOR_WORKING_CONTRACT.md`).
- Any LLM call must resolve prompt via PromptAssignment or be explicitly annotated as exempt.

Contacts & owners
-----------------
- Owner for context docs: `Architecture / System Owner` (add specific owner contact to each service doc).
- For questions: open an issue or contact the document owner listed in each service doc.

Files in this folder
--------------------
- `ARCHITECTURE_BASELINE_v0.md` — baseline (canonical)
- `ARCHITECTURE_LAW.md` — normative law
- `SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md` — readiness checklist
- `WORKING_CONTRACT.md`, `CURSOR_WORKING_CONTRACT.md` — working contract(s)
- `OPERATIONAL_DECISIONS.md` — operational decisions and priorities
- `CHAT_ONBOARDING.md`, `onboarding_ack/` — onboarding and ack templates
- `PROJECT_PHASE.md` — current phase record
- `architecture_rules.md`, `decision_model.md`, `dialog_rules.md`, `error_taxonomy.md`, `ui_architecture.md` — supporting directives
 - `DOCS_TESTS_POLICY.md` — documentation & tests policy


## Chat snapshot — testing stabilization (quick start)

To continue testing stabilization in a new chat, read this section and the linked artifacts — no further onboarding required.

Summary of actions performed in this chat:
- Declared Active Block: "Test hygiene & deterministic unit stabilization" (scope: only ✅ items from failure triage).
- Added centralized real‑LLM guard in `backend/tests/conftest.py` (skip `real_llm` unless `RUN_REAL_LLM_TESTS=1`).
- Created test inventory: `backend/tests/TEST_MATRIX.md`.
- Created test change log: `backend/tests/TESTING_CHANGELOG.md`.
- Created failure triage: `backend/docs/testing/FAILURE_TRIAGE_PHASE_0.md`.
- Finalized stabilization plan: `.cursor/plans/TESTING_BASELINE_v0.plan.md`.
- Applied safe, non‑architectural fixes to stabilize unit tests:
  - defensive fallbacks in `backend/app/services/plan_template_service.py`
  - execution error handling guard in `backend/app/services/execution_service.py`
  - ServiceRegistry backward compatibility in `backend/app/core/service_registry.py`
  - conftest improvements for sys.path and env gating `backend/tests/conftest.py`

Primary files to review first in a new chat:
- `.cursor/plans/TESTING_BASELINE_v0.plan.md`
- `backend/tests/TEST_MATRIX.md`
- `backend/docs/testing/FAILURE_TRIAGE_PHASE_0.md`
- `backend/tests/TESTING_CHANGELOG.md`

Next steps options (pick one in the next chat):
- Continue Priority‑1 fixes (test hygiene, runner scripts) — safe under Active Block.
- Or freeze changes and review ❌ items (architecture / prompts / async lifecycle) with stakeholders.

BLOCK_STATUS: an editable template is available in `.cursor/plans/TESTING_BASELINE_v0.plan.md` (use it to record progress and final verification).
