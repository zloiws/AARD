## decision_routing
Type: Component
Role: Choose routing strategy for requests (which component/agent/tool to use).
Inputs: StructuredIntent, registry data, context metadata.
Outputs: RoutingDecision (response_type, justification, required_capabilities).
LLM usage: yes (component must have system prompt; VERIFY assignment)
Events emitted: workflow_event (stage=routing, component_role=routing)
Readiness: FAIL (reason: confirm system_prompt assigned via PromptAssignment and tests)


