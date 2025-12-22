## semantic_validator
Type: Component
Role: Validate semantic correctness of StructuredIntent (Validator A).
Inputs: StructuredIntent
Outputs: approved | clarification_required (with questions)
LLM usage: yes (semantic_validator.system required; verify PromptAssignment)
Events emitted: workflow_event (stage=validator_a, component_role=semantic_validator)
Readiness: FAIL (reason: confirm prompt assignment and existence of clarification flows)


