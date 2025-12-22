## planning_service
Type: Component
Role: Build PlanHypothesis from routing decisions and context; produce versioned plan proposals.
Inputs: RoutingDecision, memory/context, capabilities.
Outputs: PlanHypothesis (versioned), required_capabilities, creation_requests.
LLM usage: yes (planning.system required; verify PromptAssignment)
Events emitted: workflow_event (stage=planning, component_role=planning)
Readiness: FAIL (reason: confirm planning.system prompt is assigned and prompt unit tests exist)


