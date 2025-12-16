"""
Decision Routing Center — component.

Role: Choose processing route based on StructuredIntent + Registry knowledge.
Model role: Reasoning (no execution).

At this stage: minimal deterministic stub (no LLM), to establish boundary + contract.
"""

from __future__ import annotations

from typing import Any, Optional

from app.components.contracts import StructuredIntent, RoutingDecision
from app.components.prompt_repository import ComponentPromptRepository


class DecisionRoutingCenter:
    component_name = "routing"

    def __init__(self, prompt_repo: Optional[ComponentPromptRepository] = None):
        self.prompt_repo = prompt_repo or ComponentPromptRepository()

    async def route(self, intent: StructuredIntent, registry: Optional[Any] = None) -> RoutingDecision:
        _ = self.prompt_repo.get_system_prompt(self.component_name)

        # Heuristic placeholder: route to planning if it looks like a multi-step request.
        text = (intent.intent or intent.raw_input or "").strip()
        if len(text) >= 120 or "\n" in text:
            return RoutingDecision(route="planning", reason="heuristic:long_or_multiline")
        return RoutingDecision(route="simple_chat", reason="heuristic:default")


