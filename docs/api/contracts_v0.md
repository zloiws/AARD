### ExecutionEvent (v0)

Required fields:
- event_id: string (UUID)
- timestamp: string (ISO 8601)
- session_id: string
- workflow_id: string
- stage: string  # one of: interpretation, validator_a, routing, planning, validator_b, execution, reflection
- component_role: string  # canonical role name (see Stage <-> Component mapping)
- component_name: string  # actual component/agent id
- prompt_id: string | null
- prompt_version: string | null
- input_summary: string | object
- output_summary: string | object
- reason_code: string | object
- status: string  # e.g., started, completed, failed

Critical additional field:
- decision_source: string  # one of: component | registry | human
  - component: decision produced by a component role (interpretation/validator/routing/planning/reflection)
  - registry: decision is derived from registry lookup (capabilities/agents/tools)
  - human: decision confirmed/initiated by a human (HITL)

Optional fields (recommended):
- related_plan_id: string | null
- parent_event_id: string | null
- metadata: object

---

### PromptAssignment (v0)

Purpose: map canonical prompts to runtime targets (model/server/task_type/component/stage) with scoping for experiments or per-agent overrides.

Fields:
- prompt_id: string
- model_id: string | null
- server_id: string | null
- task_type: string | null
- component_role: string  # ties assignment to canonical mapping (required)
- stage: string           # mirrors stage (required)
- scope: string           # one of: global | agent | experiment
  - global: default runtime assignment for stage/component_role
  - agent: overrides for a specific agent prompt context
  - experiment: overrides only inside an experiment/session, never global by default
- agent_id: string | null  # required when scope == agent
- experiment_id: string | null  # required when scope == experiment
- created_at: string (ISO 8601)
- created_by: string | null

Resolution order (highest priority first):
1) experiment scope (matching experiment_id / workflow_id / session_id)
2) agent scope (matching agent_id)
3) global scope
Fallback: disk-canonical prompt for component_role

Notes:
- `component_role` is the primary key to ensure prompts are applied per logical stage/component.
- `stage` is kept for redundancy and auditing but should match the `component_role` canonical mapping.

---

### Stage ↔ Component ↔ Prompt (canonical mapping)

This mapping is authoritative and must be enforced by `contracts_v0` consumers (backend emitters, runtime prompt selectors, and UI).

| stage | component_role | component_name | canonical_prompt_key |
|-------|----------------|----------------|----------------------|
| interpretation | interpretation | InterpretationService | interpretation.system |
| validator_a | semantic_validator | SemanticValidator | semantic_validator.system |
| routing | routing | DecisionRoutingCenter | routing.system |
| planning | planning | PlanningService | planning.system |
| validator_b | execution_validator | ExecutionValidator | execution_validator.system |
| execution | execution | AgentOrTool (agent_{name}) | agent_{name}.system |
| reflection | reflection | ReflectionService | reflection.system |

Rules:
- Every LLM call MUST be associated with a `component_role` and resolved through PromptAssignment lookup before invoking the model.
- Never reuse routing prompts for planning; routing and planning are distinct component_roles.
- Execution stage uses agent/tool prompts (`agent_{name}.system`) not component prompts.
- UI should display `stage`, `component_role`, `prompt_id`, `prompt_version`, and `decision_source` for each ExecutionEvent.


