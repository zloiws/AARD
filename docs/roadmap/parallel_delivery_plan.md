---
title: Parallel Backend+UI Delivery Plan (Observability-first)
type: delivery_plan
refs:
  - .cursor/plans/AARD — Prompt-Centric Architecture & Execution Plan_v0.1.md
  - .cursor/plans/AARD Web UI — Architecture & Implementation Plan.md
---

This is a delivery plan (execution roadmap), not an architecture document.
Architecture documents remain authoritative and are referenced above. This file captures the implementation delivery steps and canonical runtime contracts for parallel backend and UI work.

## North-star (from architecture)
- Backend behavior is defined by prompts; every LLM call must have an explicit `component_role` → prompt assignment.
- UI is observability & HITL control only; it does not perform interpretation or routing logic.

## Canonical Stage ↔ Component ↔ Prompt mapping (non-negotiable)

| stage | component_role | component_name | prompt_key |
|------|----------------|----------------|------------|
| interpretation | interpretation | InterpretationService | interpretation.system |
| validator_a | semantic_validator | SemanticValidator | semantic_validator.system |
| routing | routing | DecisionRoutingCenter | routing.system |
| planning | planning | PlanningService | planning.system |
| validator_b | execution_validator | ExecutionValidator | execution_validator.system |
| execution | execution | AgentOrTool (agent_{name}) | agent_{name}.system |
| reflection | reflection | ReflectionService | reflection.system |

Rules:
- Enforce `component_role` on all ExecutionEvent emissions.
- Do not share prompts between routing and planning.
- Execution uses agent prompts scoped to specific agents/tools.

## Phases (summary)
- Phase 0 — Freeze contracts (docs/api/contracts_v0.md)
- Phase 1 — Observability MVP: emit stage events, WS, Timeline + Graph UI
- Phase 2 — Prompt runtime enforcement: seed disk → DB, prompt selector
- Phase 3 — Settings/Prompts minimal UI: list, assign, version
- Phase 4 — Execution safety: CapabilityBoundary + Sandbox

## Immediate next actions
1. Finalize `docs/api/contracts_v0.md` (ExecutionEvent, PromptAssignment) — done (this file defines required fields).
2. Backend: implement event emitter emitting `component_role`, `prompt_id`, `prompt_version`, `decision_source`.
3. UI: implement TimelineView + Graph consuming WS events; show decision_source and prompt metadata.
4. Prompt selector: implement runtime lookup by (experiment/agent/global) resolution order.

## Acceptance criteria (MVP)
- A chat request produces ExecutionEvents for stages: interpretation → validator_a → routing → planning → validator_b → execution → reflection.
- Each event includes `stage`, `component_role`, `prompt_id`/`version`, and `decision_source`.
- UI Timeline/Graph displays the sequence with clickable events and shows prompt metadata.

## Notes about placement and process
- Keep architecture documents separate and authoritative under `.cursor/plans/`.
- This delivery plan should live in `docs/roadmap/parallel_delivery_plan.md` and will be used by implementers for branches/PRs.


