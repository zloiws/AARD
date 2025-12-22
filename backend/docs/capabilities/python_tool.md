## python_tool
Type: Capability/Tool
Role: Execute Python code in sandboxed environment; used by CoderAgent and services.
Inputs: code string, timeout, input_data
Outputs: execution result (status, result, output, error)
LLM usage: no
Events emitted: workflow_event (tool_call/tool_result)
Readiness: PASS (reason: implemented as service/tool; verify sandbox isolation tests)


