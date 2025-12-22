<!-- Migrated from legacy UI_ARCHITECTURE.md; canonical location for UI architecture -->
# UI Architecture — AARD

This document describes the UI responsibilities within the AARD system: observability, HITL controls, and configuration surfaces. The UI is a consumer of architecture; it must not implement architecture rules.

## Purpose
- Present ExecutionEvents, plan lifecycles, and introspection graphs.
- Provide human controls for HITL operations: plan approval, agent creation approvals, prompt assignment UX.

## Responsibilities
- Render facts from backend (do not infer or transform decision logic).
- Allow administrators to assign prompts (`component_role`, `stage`, `scope`) via Settings → Prompts.
- Provide timeline/graph views for workflows and plans.

## Contract with Backend
- UI consumes the following APIs/events:
  - `/api/events?workflow_id=...` (historical)
  - WebSocket `/api/ws/ws/execution/{workflow_id}` for live updates
  - `/api/prompts`, `/api/prompts/{id}/assign` for prompt management
  - `/api/plans?session_id=...` for listing plans

UI must display `component_role`, `prompt_id`, `prompt_version`, `decision_source`, `reason_code` for each event.


