## base_agent
Type: Agent
Role: Base class providing agent lifecycle, prompt handling, and execution helpers.
Inputs: agent configuration, prompts, task requests
Outputs: agent messages, plan steps, actions
LLM usage: yes (agents must have system_prompt; agent.system_prompt sourced from registry)
Events emitted: workflow_event (stage=execution, component_role=agent_{name})
Readiness: FAIL (reason: verify all agents registered in Registry and have prompt_id/version)


