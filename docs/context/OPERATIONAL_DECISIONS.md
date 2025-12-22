OPERATIONAL_DECISIONS

Purpose
-------
Краткое, действующее изложение операционных решений и приоритетов, извлечённых из проектных обсуждений и чатов.
Этот файл — источник правды для процессов и быстрого онбординга (actionable summary). Подробный архив — `del_chat.md`.

Key decisions
-------------
- CI / lint checks are NOT mandatory at this phase. Контроль сохранён, но перенесён в документы и процессы (см. нижe).
- Автоматические PR-гейты / bot-enforced architecture — запрещены на текущем этапе.
- Архитектурные контракты и проверки выполняются вручную через чеклисты и инвентаризации.

Canonical constraints (short)
---------------------------
- Следовать `ARCHITECTURE_BASELINE_v0.md` и `ARCHITECTURE_LAW.md`.
- Ни один backend `app/**` файл не может быть оставлен без категории — см. `backend/docs/entities/catalog.md`.
- Любой LLM-вызов должен резолвиться через PromptAssignment или явно помечен:

  # LEGACY_PROMPT_EXEMPT
  # reason: <one-line reason>
  # phase: Phase 2 inventory freeze

Priorities (operational)
------------------------
- PRIORITY 0 — зафиксировать базу (ARCHITECTURE_BASELINE_v0.md и сопутствующие документы).
- PRIORITY 1 — довести сущности до «оркестрабельных»: входы/выходы, side-effects, события, LLM usage.
- PRIORITY 2 — устранять отдельные FAIL-пункты readiness (по одному).
- PRIORITY 3 — наращивание агентов и capability-каналов (после стабилизации).

Golden rule
-----------
Ни одной новой возможности, пока существующая сущность не готова к оркестрации.

Execution quick reference
-------------------------
- Canonical stages: interpretation, validator_a, routing, planning, validator_b, execution, reflection, registry_update.
- Minimal ExecutionEvent (v0) fields (must be present in emitted/persisted events): event_id, timestamp, workflow_id, session_id, stage, component_role, component_name, decision_source, status, prompt_id (if used), prompt_version (if used), input_summary, output_summary, reason_code, parent_event_id, event_metadata.

Onboarding / immediate checklist for new chat
---------------------------------------------
1. Read (in order): `docs/context/ARCHITECTURE_BASELINE_v0.md`, `docs/context/ARCHITECTURE_LAW.md`, `docs/context/SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md`, `docs/api/contracts_v0.md`, `backend/docs/entities/catalog.md`, `backend/docs/architecture/backend_interactions.md`, `backend/docs/llm_call_inventory.md`, `.cursor/plans/AARD — Prompt-Centric Architecture & Execution Plan_v0.1.md`.
2. Confirm knowledge: canonical stages + ExecutionEvent required fields.
3. If planning edits: run readiness checklist for target entity and document PASS/FAIL before changes.
4. For any LLM change: resolve prompt via PromptAssignment or add `# LEGACY_PROMPT_EXEMPT` annotation with reason.

Tracks (how to categorize follow-up work)
---------------------------------------
- Track A — Architectural enforcement (lint rules, runtime guards, contract validation).
- Track B — Technical debt burn-down (prompt migration, deduplication).
- Track C — Feature evolution (new agents, capabilities).

Process notes
-------------
- Work one phase at a time; stop and report after each phase completion.
- Do not refactor, rename entities, or introduce new abstractions without explicit request/approval.
- Use `backend/docs/*` inventories and `docs/context/*` directives as the single source of truth.

References
----------
- `del_chat.md` — full chat archive (raw).
- `docs/context/ARCHITECTURE_BASELINE_v0.md`
- `docs/context/ARCHITECTURE_LAW.md`
- `docs/context/SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md`
- `backend/docs/entities/catalog.md`
- `backend/docs/llm_call_inventory.md`

Adoption
--------
Adoption date: YYYY-MM-DD  
Owner: Architecture / System Owner


