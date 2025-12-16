"""
PlanningService — component wrapper.

Role: Produce a PlanHypothesis from a RoutingDecision.
Model role: Reasoning (plan generation only).

At this stage: minimal stub to establish contract boundaries without impacting existing services.
"""

from __future__ import annotations

from typing import Optional

from app.components.contracts import RoutingDecision, PlanHypothesis
from app.components.prompt_repository import ComponentPromptRepository


class PlanningService:
    component_name = "planning"

    def __init__(self, prompt_repo: Optional[ComponentPromptRepository] = None):
        self.prompt_repo = prompt_repo or ComponentPromptRepository()

    async def plan(self, routing_decision: RoutingDecision) -> PlanHypothesis:
        _ = self.prompt_repo.get_system_prompt(self.component_name)

        # Placeholder: existing repo has a large `app.services.planning_service.PlanningService`.
        # Integration will happen in a later phase (via Orchestrator).
        return PlanHypothesis(
            name="stub_plan",
            steps=[],
            confidence=0.1,
            metadata={"note": "stub - not yet integrated", "routing": routing_decision.model_dump()},
        )


