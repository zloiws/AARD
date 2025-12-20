CHAT_ONBOARDING — what a new chat must read before starting work

Purpose
-------
Minimum orientation checklist and immediate actions for any new chat/agent entering the repository.

Required reading (minimal, in order)
1. `docs/context/ARCHITECTURE_BASELINE_v0.md` — canonical baseline: execution stages, ExecutionEvent (v0) contract, prompt-centric rules, and accepted invariants.
2. `docs/context/ARCHITECTURE_LAW.md` — hard architectural prohibitions and mandatory constraints.
3. `docs/context/SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md` — what makes a service orchestration-ready; use this to validate changes.
4. `docs/api/contracts_v0.md` — API contracts, including `ExecutionEvent (v0)` and `PromptAssignment (v0)`.
5. `backend/docs/entities/catalog.md` — inventory and classification of backend elements (each backend `app/**` file must have one classification).
6. `backend/docs/architecture/backend_interactions.md` — interaction spec mapping stages to components and event emission points.
7. `backend/docs/llm_call_inventory.md` — inventory of LLM call sites, exemptions, and inventory status.
8. `.cursor/plans/AARD — Prompt-Centric Architecture & Execution Plan_v0.1.md` — plan and phase rules.
9. `docs/context/OPERATIONAL_DECISIONS.md` — actionable operational rules and priorities (summary of del_chat.md).
10. `del_chat.md` — raw archive of chat discussion and rationale.

Quick checks (before any edit)
- Can you list canonical stages? (`interpretation`, `validator_a`, `routing`, `planning`, `validator_b`, `execution`, `reflection`, `registry_update`)
- Can you list ExecutionEvent (v0) required fields? (`event_id`, `timestamp`, `workflow_id`, `session_id`, `stage`, `component_role`, `component_name`, `decision_source`, `status`, `prompt_id`/`prompt_version` (if used), `input_summary`, `output_summary`, `reason_code`, `parent_event_id`, `event_metadata`)
- Is the entity you will change classified in `backend/docs/entities/catalog.md`?
- Does any file you will change contain literal prompts? (see `backend/docs/llm_call_inventory.md`)

Immediate checklist (first run)
1. Create onboarding ack: `docs/context/onboarding_ack/<chat-id>.md` using `TEMPLATE_ACK.md` and commit it.
2. If you plan to touch an entity, run the `SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md` for that entity and publish the PASS/FAIL result in `backend/docs/services/<service>.md` (per `ARCHITECTURE_LAW.md`).
3. For any LLM-related change: ensure prompt resolution via PromptAssignment or add `# LEGACY_PROMPT_EXEMPT` annotation with reason.
4. If any conflict with `ARCHITECTURE_LAW.md` or baseline arises — stop and request human decision.

Operational rules (summary)
- No refactors/renames/new abstractions without explicit approval.
- Work one phase at a time; stop and produce `BLOCK STATUS` after phase completion (see `CURSOR_WORKING_CONTRACT.md`).
- Use `backend/docs/*` inventories and `docs/context/*` directives as the single source of truth.

Where to record status
- `docs/context/PROJECT_PHASE.md` — current project phase.
- `docs/context/onboarding_ack/<chat-id>.md` — per-chat acknowledgement.
- Per-entity service docs under `backend/docs/services/` — readiness results and owner.
Operational notes:
- Do not perform refactors, renames, or new abstractions unless explicitly requested.
- Follow phase discipline: work on one phase at a time and stop after completing each phase.
- Any action that touches LLM prompts must follow the prompt-centric rules; literal prompts must be annotated if exempt.

Checklist for the first run:
- Confirm you have read items 1–4 and can cite the canonical stage list and the ExecutionEvent required fields.
- Confirm you understand the golden rule: do not add features until entities reach orchestration-ready state.
- If any of the above files are unclear, escalate for human clarification before making changes.


