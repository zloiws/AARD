NEW_CHAT_START_HERE

Purpose: quick orientation for a new chat/agent entering the repo.

Required reading (in order):
1. `docs/context/ARCHITECTURE_BASELINE_v0.md`
2. `docs/context/ARCHITECTURE_LAW.md`
3. `docs/context/SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md`
4. `docs/api/contracts_v0.md`
5. `backend/docs/entities/catalog.md`
6. `backend/docs/architecture/backend_interactions.md`
7. `backend/docs/llm_call_inventory.md`
8. `.cursor/plans/AARD — Prompt-Centric Architecture & Execution Plan_v0.1.md`
9. `del_chat.md` (archive; see `docs/context/OPERATIONAL_DECISIONS.md` for actionable summary)
10. `docs/context/CHAT_ONBOARDING.md`

Quick checks:
- Can you list canonical stages?
- Can you list ExecutionEvent (v0) required fields?
- Are the entities you will touch classified in `backend/docs/entities/catalog.md`?
- Does any file you will change contain literal prompts? (see `backend/docs/llm_call_inventory.md`)

Operational rules summary:
- No refactors/renames/new abstractions without explicit request.
- One phase at a time; stop and report after the phase.
- LLM calls must follow PromptAssignment order or be explicitly exempted.

If you plan to start work, create an acknowledgement file in `docs/context/onboarding_ack/<chat-id>.md` using the TEMPLATE_ACK.


