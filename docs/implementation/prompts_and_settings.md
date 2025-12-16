# Prompts & Settings — Implementation Notes (continuation)

This document describes the recent work implementing prompt management and Settings UI. It continues and complements the canonical AARD plan and implementation notes already present in the repository (see `docs/implementation/plan_lifecycle.md`).

Date: 2025-12-16

## High-level summary — what was implemented

- Backend
  - Added persistent prompt model and versioning (`backend/app/models/prompt.py` existed; records created from disk).
  - Added prompt assignments mapping prompts → model/server/task_type (`backend/app/models/prompt_assignment.py`).
  - Extended `PromptService` with:
    - create/read/update/versioning functions (existing),
    - assignment functions `assign_prompt_to_model_or_server()` and `list_assignments()` (`backend/app/services/prompt_service.py`).
  - Extended API:
    - Prompt management routes already existed in `backend/app/api/routes/prompts.py`; new endpoints added:
      - `POST /api/prompts/{prompt_id}/assign` — assign prompt to model/server/task_type.
      - `GET /api/prompts/{prompt_id}/assignments` and `GET /api/prompts/assignments` — list assignments.
  - Seed script to import on-disk system prompts into DB:
    - `backend/scripts/seed_prompts_from_disk.py` — idempotent import of `prompts/components/*.system` as prompt records (creates versions when text changes).
  - Interpretation behavior:
    - `InterpretationService` now passes the component system prompt to the LLM (`OllamaClient.generate(..., system_prompt=...)`) and uses the LLM output to enrich StructuredIntent. The platform default flag `interpretation_use_llm` is enabled (`backend/app/core/config.py`).

- Frontend (UI)
  - Settings UI refactor:
    - `ModelSettings` became a modal dialog (Settings) instead of a side panel; can be opened/closed from the header (`ui/src/App.tsx`).
    - Settings modal shows `ModelSettings` plus a `PromptsPanel` for prompt management.
  - Prompts panel:
    - `ui/src/components/PromptsPanel.tsx` lists prompts and their versions, allows creating assignments (server/model/task_type).
  - Chat UI improvements:
    - `ui/src/components/ChatPanel.tsx`:
      - Clarification flow: shows clarification questions and allows answering directly from the suggested question.
      - Debug toggle `DebugAdmin` to force admin role for testing Approve.
      - Polling/WebSocket hooks to reflect plan/execution updates in real time.
  - Realtime events:
    - `ui/src/components/RealtimeEventsPanel.tsx` increased width by 20%, defaults collapsed, color-coded event types and expand/collapse control.

## Why these choices

- The system must treat prompts as first-class, versioned artifacts. Having them in DB enables:
  - querying by model/task_type,
  - version history and metrics,
  - controlled evolution and human approval workflows.
- The modal Settings layout groups Servers/Models and Prompts logically for admin workflows.
- LLM usage for interpretation is enabled by default to obey the "prompt-centric" principle: prompts directly control behavior.

## Files added/changed (high-signal)
- New:
  - `backend/app/models/prompt_assignment.py`
  - `backend/scripts/seed_prompts_from_disk.py`
  - `ui/src/components/PromptsPanel.tsx`
- Changed / extended:
  - `backend/app/services/prompt_service.py` (assignments)
  - `backend/app/api/routes/prompts.py` (assignment endpoints)
  - `backend/app/components/interpretation_service.py` (passes system_prompt to Ollama)
  - `backend/app/core/config.py` (interpretation_use_llm default=true)
  - `ui/src/App.tsx` (Settings modal)
  - `ui/src/components/ChatPanel.tsx`, `RealtimeEventsPanel.tsx` (UI improvements)

## Next recommended steps
1. Add UI in `PromptsPanel` to select model or server from the current list before assignment (improve UX).  
2. Add server-side logging for `/api/prompts` and prompt assignment endpoints to capture errors and metrics.  
3. Add integration tests (Playwright) for:
   - Creating/Versioning prompts in UI → persisted in DB.
   - Assigning prompt → model/server/task_type via UI and verifying runtime lookup.
4. Wire runtime prompt selection: when making LLM calls, select the active prompt by model/server/task_type via a central `PromptManager` (already present) and pass it as `system_prompt` to `OllamaClient.generate`.

## How to run the seed script
From the repository root:
```
python -c "import sys, pathlib; sys.path.insert(0, str(pathlib.Path('backend').resolve())); from scripts.seed_prompts_from_disk import main as m; m()"
```

## Commit
This documentation file was added as part of the implementation changes committed together with the code edits.


