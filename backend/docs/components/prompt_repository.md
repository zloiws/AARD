## prompt_repository
Type: Component
Role: Provide canonical prompt text for components (disk-canonical fallback).
Inputs: component_role or stage
Outputs: system_prompt text, prompt_id/version (if available)
LLM usage: no (provides prompts, does not call LLM)
Events emitted: none
Readiness: PASS (reason: component reads prompts from disk; verify PromptAssignment integration)


