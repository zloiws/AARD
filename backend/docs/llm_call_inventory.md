# LLM Call Inventory (Phase 2 — option A)

This document inventories code locations that call the LLM layer (OllamaClient) and classifies whether they resolve system prompts via the runtime prompt resolution stack or use local literals / no prompt.

Rules applied:
- "Resolved" means the file uses `PromptService`, `PromptManager`, `PromptRuntimeSelector` or component prompt repository to obtain a `system_prompt` before invoking the LLM.
- "Literal" means a hard-coded string is passed as `system_prompt` at the call site.
- "None" means no `system_prompt` argument is passed.
- Per plan Phase 2 rules, each uncovered LLM call must be routed via `prompt_runtime_selector` or explicitly annotated as legacy/exempt.

Summary (high level)
- Total LLM call sites discovered: 24 (see JSON)
- Resolved via prompt manager/service: request_orchestrator.py, interpretation_service.py, reflection_service.py, planning_service.py, benchmark_service.py, model_benchmark_service.py, execution_service.py, agent base/evolution — generally compliant.
- Hard-coded literals found: artifact_generator.py, agent_approval_agent.py, uncertainty_learning_service.py, some agent files — **require annotation or migration**.
- Callers with no explicit prompt: self_audit_service.py, planning_service_dialog_integration.py, planning_hypothesis_service.py, critic_service.py, decision_framework.py — **require review**.

Recommendations (next actions)
1. For each "literal" call site, add a short code comment annotation `# LEGACY_PROMPT_EXEMPT: reason` or migrate to `PromptAssignment` + `PromptManager`.
2. For "no prompt" call sites, decide whether no prompt is required (e.g., embedding generation) or route via `PromptRuntimeSelector` before calling.
3. Add a lint/check that warns when `OllamaClient.generate` is invoked without an explicit `system_prompt` parameter or a preceding prompt resolution call (configurable to allow explicit exemptions).

Detailed inventory is in `backend/docs/llm_call_inventory.json`.

Status: annotated

BLOCK STATUS = DONE


