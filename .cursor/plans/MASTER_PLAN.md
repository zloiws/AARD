MASTER PLAN — AARD consolidated roadmap (normative draft)

Purpose
-------
Unified, prioritized master plan consolidating work from `.cursor/plans/*` and aligned with `docs/context/*`. This document is normative: it encodes execution discipline, phase DoD, tracks, and governance rules for Cursor-driven execution and human coordination.

Status
------
Current phase: Stabilization (Phase 0–4 completed).  
Document status: NORMATIVE (see Governance below). Date: YYYY-MM-DD. Owner: Architecture / System Owner.

Top-level tracks (rephrased)
----------------------------
- Track A — Architectural enforcement (runtime guards, explicit annotations, manual verification). NOTE: lint/CI checks are advisory/optional and must not block commits by default.
- Track B — Technical debt & prompt migration (LEGACY_PROMPT_EXEMPT removal, deduplication).
- Track C — Feature evolution (new agents, capabilities, UI).

Phase -1 — Execution discipline (normative)
-------------------------------------------
This section is normative and must be enforced.

Rules (must):
- Cursor must NOT refactor business logic, rename entities, or introduce new abstractions without explicit human request.
- Cursor must work on exactly one Active Block at a time and must not propose switching blocks unless explicitly asked.
- Violation of execution discipline is considered an architectural regression even if tests pass.
- Cursor must not expand block scope while the block is active.

Active Block model (definition)
- Block is declared by a human and has: single objective, explicit exit condition, owner, and list of affected files.
- No block may modify baseline docs (`ARCHITECTURE_BASELINE_v0.md`, `ARCHITECTURE_LAW.md`) unless explicitly declared in the block and approved by owner.

Block Status (required on block completion)
- Block name:
- What is DONE (facts only):
- What is STABLE (can be reused):
- What is TEMPORARY (assumptions / mocks / flags):
- What is NOT TOUCHED next:
- Architectural impact: none / localized / cross-cutting

Phase DoD (minimal examples — required for phase completion)
-----------------------------------------------------------
Phase 0 DoD:
- `backend/docs/entities/catalog.{json,md}` produced, one classification per `backend/app/**.py`.

Phase 1 DoD:
- `WorkflowEvent` persisted with all ExecutionEvent (v0) fields present.
- Canonical stages stored only.
- At least one contract test asserting API serialization shape.

Phase 2 DoD:
- All LLM call paths in scope resolve prompts via PromptAssignment/PromptRuntimeSelector or are explicitly annotated `# LEGACY_PROMPT_EXEMPT` with reason.
- Unit test validating prompt resolution guard exists.

Phase 3 DoD:
- Per-entity docs created under `backend/docs/{services,components,capabilities,agents,registry}` following the template.
- Owners assigned for each entity doc.

Phase 4 DoD:
- `backend/docs/architecture/backend_interactions.md` exists with canonical stage mapping and Mermaid diagram.
- `/api/events/graph` (or equivalent) defined for observability.

Priorities (operational)
------------------------
- PRIORITY 0 — Freeze baseline docs (`ARCHITECTURE_BASELINE_v0.md`, `ARCHITECTURE_LAW.md`, `SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md`).
- PRIORITY 1 — Stabilize entity IO and readiness (one FAIL at a time; no parallel FAIL resolution).
- PRIORITY 2 — Address prompt migration and technical debt (Track B).
- PRIORITY 3 — Grow agents/capabilities and UI after readiness.

Process rules (must-follow)
---------------------------
- Declare Active Block → implement incrementally → run only relevant tests → produce Block Status → STOP.
- Any change that affects an entity's contract must include a service/component doc update and tests in the same commit.
- Any LLM changes must resolve prompts before calling LLM; low-level clients are transport-only.

Deliverables & artifact classification
------------------------------------
Each artifact must be marked with one of:
- normative — required source-of-truth (e.g., `ARCHITECTURE_LAW.md`, `ARCHITECTURE_BASELINE_v0.md`)
- descriptive — informative (e.g., `llm_call_inventory.md`)
- temporary — ephemeral (e.g., TODO lists, ad-hoc notes)

Primary deliverables
- `backend/docs/entities/catalog.{json,md}` (descriptive)
- `backend/docs/architecture/backend_interactions.md` (normative/descriptive — mapping)
- `backend/docs/llm_call_inventory.{md,json}` (descriptive)
- per-entity docs under `backend/docs/{services,components,capabilities,agents,registry}` (normative/descriptive)
- tests validating contracts (normative when enforcing ExecutionEvent/PromptAssignment)

Governance & owners
--------------------
- Each service/entity doc must include `owner` (team/person/email).
- Major architectural changes require review by owner of `ARCHITECTURE_LAW.md` and affected entity owners.
- When document is marked `normative`, changes must be accompanied by a Block and explicit owner approval.

Observability & acceptance
--------------------------
- Every persisted event must follow ExecutionEvent (v0) — see `docs/api/contracts_v0.md`.
- UI visualizations are read-only views of events; UI must not infer logic.

Appendix: plans merged
----------------------
This MASTER_PLAN consolidates:
- `.cursor/plans/contracts-and-entities.plan.md`
- `.cursor/plans/AARD — Prompt-Centric Architecture & Execution Plan_v0.1.md`
- `.cursor/plans/aard_comprehensive_development_plan_v_0.md`
- `.cursor/plans/TODO_1.md` (archived copy)
- `.cursor/plans/AARD Web UI — Architecture & Implementation Plan.md` (UI plan included as sub-section)

Archive & references
--------------------
Detailed legacy notes and TODOs moved to `.cursor/plans/archive/`. Reference them from the relevant phase in this plan.

Change log
----------
Record changes to MASTER_PLAN in `.cursor/plans/CHANGELOG.md`.


