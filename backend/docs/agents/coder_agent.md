## coder_agent
Type: Agent
Role: Code-generation agent — generates code from function-call prompts and validates execution.
Inputs: FunctionCall prompts, context, agent/system prompt
Outputs: generated code, execution results
LLM usage: yes (agent.system_prompt required; currently uses literal prompts in code — annotated)
Events emitted: workflow_event (stage=execution, component_role=agent_coder)
Readiness: FAIL (reason: literal prompts present; ensure agent is registered and prompt assigned)


