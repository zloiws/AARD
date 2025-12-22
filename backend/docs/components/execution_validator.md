## execution_validator
Type: Component
Role: Validate plan hypotheses for safe execution (mechanical safety).
Inputs: PlanHypothesis, capability registry, execution constraints.
Outputs: approved | rejected with reasons.
LLM usage: yes (component must have system prompt; VERIFY assignment)
Events emitted: workflow_event (stage=validator_b, component_role=execution_validator)
Readiness: FAIL (reason: ensure system_prompt present and validation tests exist)


