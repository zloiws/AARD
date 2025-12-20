CHAT_ONBOARDING — what a new chat must read before starting work

Before any new chat/agent begins operational work on the repository, it MUST read and understand the following files (minimal set), in this order:

1. `docs/context/ARCHITECTURE_BASELINE_v0.md` — canonical baseline: execution stages, ExecutionEvent (v0) contract, prompt-centric rules, and accepted invariants.
2. `docs/context/ARCHITECTURE_LAW.md` — hard architectural prohibitions and mandatory constraints.
3. `docs/context/SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md` — what makes a service orchestration-ready; use this to validate changes.
4. `docs/api/contracts_v0.md` — API contracts, including `ExecutionEvent (v0)` and `PromptAssignment (v0)`.
5. `backend/docs/entities/catalog.md` — inventory and classification of backend elements (each backend `app/**` file has one classification).
6. `backend/docs/architecture/backend_interactions.md` — interaction spec mapping stages to components and event emission points.
7. `backend/docs/llm_call_inventory.md` — inventory of LLM call sites, exemptions, and inventory status.
8. `.cursor/plans/AARD — Prompt-Centric Architecture & Execution Plan_v0.1.md` — plan and phase rules.
9. `del_chat.md` — design rationale and operational decisions about CI and priorities.
10. `docs/context/WORKING_CONTRACT.md` (or `CURSOR_WORKING_CONTRACT.md` if present) — operational rules for Cursor/agents.

Operational notes:
- Do not perform refactors, renames, or new abstractions unless explicitly requested.
- Follow phase discipline: work on one phase at a time and stop after completing each phase.
- Any action that touches LLM prompts must follow the prompt-centric rules; literal prompts must be annotated if exempt.

Checklist for the first run:
- Confirm you have read items 1–4 and can cite the canonical stage list and the ExecutionEvent required fields.
- Confirm you understand the golden rule: do not add features until entities reach orchestration-ready state.
- If any of the above files are unclear, escalate for human clarification before making changes.


