## simple_agent
Type: Agent
Role: Lightweight agent for simple tasks and direct responses.
Inputs: user messages, agent system prompt
Outputs: direct responses, actions
LLM usage: yes (agent.system_prompt required)
Events emitted: workflow_event (stage=execution, component_role=agent_simple)
Readiness: FAIL (reason: verify prompt assignment and test coverage)


