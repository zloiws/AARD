# AARD Project - Cursor AI System Prompt

You are working on AARD — a personal human‑AI interaction environment.

ARCHITECTURAL RULES (NON-NEGOTIABLE):
1. NO AGI/autonomous intelligence terminology
2. NO "self‑learning" or "intelligence growth" claims
3. Human is the foundation, NOT part of the system
4. LLM is a semantic interpreter, NOT an intelligence core
5. Plans are hypotheses, NOT instructions
6. System prompt REQUIRED ONLY for decision‑making entities
7. NO prompts for infrastructure components (orchestrator, sandbox, registry)
8. Two models: Reasoning (decisions) and Code (execution) — NEVER mix

WORKING PRINCIPLES:
- ALWAYS check Capability & Agent Registry before creating anything new
- ALWAYS require formalized inputs/outputs for any component
- ALWAYS separate interpretation from execution
- ALWAYS require human approval for environment expansion
- NEVER modify behavior without reflection on outcomes

REFER TO NORMATIVE DOCS & PLANS (use exact filenames)
- `docs/context/ARCHITECTURE_BASELINE_v0.md`
- `docs/context/ARCHITECTURE_LAW.md`
- `docs/context/SERVICE_ORCHESTRATION_READINESS_CHECKLIST.md`
- `.cursor/plans/AARD — Prompt-Centric Architecture & Execution Plan_v0.1.md`
- `.cursor/plans/aard_comprehensive_development_plan_v_0.md`
- `.cursor/plans/aard_interaction_scheme_reflection_driven.md`
- `.cursor/plans/contracts-and-entities.plan.md`

Also consult onboarding & operational summaries:
- `docs/context/CHAT_ONBOARDING.md`
- `docs/context/OPERATIONAL_DECISIONS.md`

Before any code generation:
1. Confirm which architectural phase you're in (see `PROJECT_PHASE.md` / plans)
2. Verify component responsibilities (catalog & service docs)
3. Check if Registry already has required capability/agent
4. Create onboarding acknowledgement per `docs/context/CHAT_ONBOARDING.md` before making changes