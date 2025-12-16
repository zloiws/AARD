"""
Validator B (Execution Validator) — component.

Role: Check whether a PlanHypothesis is safe/allowed to execute.
Model role: Reasoning (no user interaction).

At this stage: deterministic stub approving everything. Real checks will be wired to
CapabilityBoundary / sandbox policy in later phases.
"""

from __future__ import annotations

from typing import Optional

from app.components.contracts import PlanHypothesis, ExecutionValidationResult
from app.components.prompt_repository import ComponentPromptRepository


class ExecutionValidator:
    component_name = "execution_validator"

    def __init__(self, prompt_repo: Optional[ComponentPromptRepository] = None):
        self.prompt_repo = prompt_repo or ComponentPromptRepository()

    async def validate_plan(self, plan: PlanHypothesis) -> ExecutionValidationResult:
        _ = self.prompt_repo.get_system_prompt(self.component_name)
        return ExecutionValidationResult(status="approved", metadata={"note": "stub"})


