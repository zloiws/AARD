## planner_agent
Type: Agent
Role: Planning-focused agent (produces plans, decompositions, function-call prompts).
Inputs: task descriptions, context, prompts (agent/system)
Outputs: plans, structured steps, function_call prompts
LLM usage: yes (uses agent.system_prompt; verify registry prompt assignment)
Events emitted: workflow_event (stage=planning/execution, component_role=agent_planner)
Readiness: FAIL (reason: confirm agent registration and associated prompt_id/version)


