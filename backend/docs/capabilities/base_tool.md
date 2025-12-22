## base_tool
Type: Capability/Tool
Role: Abstract base for tools exposing execute interface.
Inputs: tool-specific parameters
Outputs: tool execution result (status, result, output)
LLM usage: no
Events emitted: workflow_event (tool_call/tool_result)
Readiness: PASS (reason: core abstraction only; implementations must document interfaces)


