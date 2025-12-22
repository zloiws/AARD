## interpretation_service
Type: Component
Role: Convert raw user input into StructuredIntent.
Inputs: raw user input, user/session context.
Outputs: StructuredIntent (intent_type, goal, constraints, ambiguity_flags).
LLM usage: yes (uses Reasoning model; must have system_prompt via PromptAssignment or ComponentPromptRepository)
Events emitted: workflow_event (stage=interpretation, component_role=interpretation)
Readiness: FAIL (reason: verify prompt assignment and unit tests for structured output)


