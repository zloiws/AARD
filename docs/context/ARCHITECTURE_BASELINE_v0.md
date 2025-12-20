# ARCHITECTURE_BASELINE_v0

**Project:** AARD  
**Scope:** backend/app (core runtime, agents, services, components)  
**Status:** FIXED / BASELINE  
**Version:** v0  
**Date:** YYYY-MM-DD  
**Owner:** Architecture / System Owner

---

## 1. Purpose of this document

This document fixes the **architectural baseline** of the AARD backend after
completion of the initial architecture alignment cycle (Phase 0–4).

Its purpose is to:

- declare the **authoritative architectural model** of the system;
- define **non-negotiable invariants** for further development;
- establish a **stable reference point** for refactoring, enforcement, and evolution;
- prevent architectural drift caused by ad-hoc changes or agent over-execution.

From this point forward, **all changes MUST be evaluated against this baseline**.

---

## 2. Baseline scope

### In scope

- `backend/app/**`
- Architectural contracts, prompts, events, orchestration, agent/component boundaries
- Runtime behavior of LLM calls and observability

### Explicitly out of scope

- Tests (`backend/tests/**`)
- Migrations (`backend/alembic/**`)
- Scripts (`backend/scripts/**`)
- SQL helpers
- CI/CD configuration (unless enforcing architectural rules)

---

## 3. Normative references (authoritative)

The following documents are **normative**.  
If code or future docs contradict them — **the code is wrong**.

1. `docs/api/contracts_v0.md`
2. `docs/context/ARCHITECTURE_LAW.md`
3. `docs/context/SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md`
4. `.cursor/plans/AARD — Prompt-Centric Architecture & Execution Plan_v0.1.md`

Derived / descriptive artifacts:

- `backend/docs/entities/catalog.md`
- `backend/docs/llm_call_inventory.md`
- `backend/docs/architecture/backend_interactions.md`

---

## 4. Architectural model (fixed)

### 4.1 Canonical execution stages

The system operates on a **canonical, ordered execution pipeline**:

1. `interpretation`
2. `validator_a`
3. `routing`
4. `planning`
5. `validator_b`
6. `execution`
7. `reflection`
8. `registry_update`

No other stages may be persisted in events.

Internal helper states MAY exist, but **must be mapped** before persistence.

---

### 4.2 ExecutionEvent (v0) — mandatory

The system’s single source of truth for observability is:

**ExecutionEvent (v0)**  
implemented concretely as `WorkflowEvent`.

Each persisted / emitted event MUST include:

- `event_id`
- `timestamp`
- `workflow_id`
- `session_id`
- `stage` (canonical)
- `component_role`
- `component_name`
- `decision_source`
- `status`
- `prompt_id` (if LLM used)
- `prompt_version` (if LLM used)
- `input_summary`
- `output_summary`
- `reason_code`
- `parent_event_id`
- `event_metadata`

Any component that cannot emit a compliant event
**is not orchestration-ready**.

---

## 5. Prompt-centric execution (non-negotiable)

### 5.1 Rule

> **If a component calls an LLM, it MUST resolve a prompt explicitly.**

No implicit prompts.  
No hidden defaults.  
No silent fallbacks.

---

### 5.2 Prompt resolution order (fixed)

Prompt resolution follows **PromptAssignment (v0)** order:

1. Explicit assignment (component + stage)
2. Agent-level assignment
3. Component default
4. System fallback (only if documented)

Resolution MUST occur **before** invoking `OllamaClient.generate`.

---

### 5.3 Low-level client rule

`app/core/ollama_client.py` is a **transport only**.

It:
- does NOT resolve prompts;
- does NOT enforce architecture;
- expects a fully-resolved `system_prompt`.

This is **by design**.

---

## 6. LLM call inventory status (as of baseline)

All LLM invocation points have been scanned and classified.

Artifacts:

- `backend/docs/llm_call_inventory.json`
- `backend/docs/llm_call_inventory.md`

Current state:

- ✅ Calls with proper prompt resolution exist
- ⚠️ Calls with literal / implicit prompts are identified
- ⚠️ Calls without explicit prompts are identified and classified

No migration is performed in this baseline.
All deviations are **known, localized, and documented**.

---

## 7. Entity taxonomy (fixed vocabulary)

Every backend element MUST belong to exactly one category:

- **Service** — domain logic
- **Module** — internal grouping
- **Component** — LLM “thinking” unit
- **Capability / Tool** — execution surface
- **Agent** — orchestrated decision entity
- **Sandbox** — isolated execution
- **Registry** — persistence / memory / index

Reference catalog:

- `backend/docs/entities/catalog.md`

Entities without classification **do not exist architecturally**.

---

## 8. Interaction model (authoritative)

The authoritative interaction flow is defined in:

- `backend/docs/architecture/backend_interactions.md`

It specifies:

- stage → component/service mapping
- prompt resolution points
- event emission points
- dependency directionality

This document is the **single source of truth** for:
- UI visualization
- observability pipelines
- agent execution tracing

---

## 9. What this baseline explicitly does NOT do

This baseline:

- ❌ does NOT refactor code
- ❌ does NOT migrate legacy prompts
- ❌ does NOT “clean up” services
- ❌ does NOT optimize performance
- ❌ does NOT add features

It **only defines the ground rules**.

---

## 10. Post-baseline work rules

All future work MUST belong to exactly one track:

### Track A — Architectural enforcement
Examples:
- lint rules
- runtime guards
- contract validation

### Track B — Technical debt burn-down
Examples:
- LEGACY_PROMPT_EXEMPT removal
- prompt migration
- module deduplication

### Track C — Feature evolution
Examples:
- new agents
- new capabilities
- new flows

Tracks MUST NOT be mixed in a single PR.

---

## 11. Cursor / agent operating constraints

For automated agents (Cursor, etc.):

- No PR unless explicitly authorized
- No CI unless explicitly authorized
- No cross-track work
- One block at a time
- Stop after block completion and wait

Violation of these rules is considered a **process error**, not a productivity gain.

---

## 12. Acceptance statement

By committing this document, the project declares:

> “The architecture is now defined, observable, and enforceable.  
> All further changes are intentional deviations, not accidental drift.”

This document marks the **end of the architecture definition phase**  
and the **start of controlled system evolution**.

---

### Where to place this file (recommended)

Recommended path:

```
docs/context/ARCHITECTURE_BASELINE_v0.md
```

Why:

- next to `ARCHITECTURE_LAW.md`;
- logically above interaction-spec and inventories;
- clearly normative.

---

## Next steps (no pressure)

After baseline fixation you may:

1. prepare PR **only with documentation**
2. enable Track A (enforcement)
3. enable Track B (debt reduction)
4. do nothing — the architecture is fixed and preserved

If you want I can:

- draft a Cursor system-prompt referencing this baseline;
- or break Track A/B into subplans.

ARCHITECTURE BASELINE v0 — FIXED


