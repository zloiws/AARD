## reflection_service
Type: Component
Role: Analyze execution results and propose updates to prompts, confidence and registry.
Inputs: Execution outputs, event histories, metrics.
Outputs: improvement proposals, confidence updates, registry update requests.
LLM usage: yes (reflection.system required; verify PromptAssignment)
Events emitted: workflow_event (stage=reflection, component_role=reflection)
Readiness: FAIL (reason: ensure reflection.system prompt is assigned and tests cover proposed updates)


