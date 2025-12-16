"""
Validator A (Semantic Validator) — component.

Role: Validate that the StructuredIntent is semantically usable; request clarification if needed.
Model role: Reasoning (may ask the human questions).

At this stage: deterministic validation (no LLM). This is a boundary placeholder.
"""

from __future__ import annotations

from app.components.contracts import StructuredIntent, ValidationResult
from app.components.prompt_repository import ComponentPromptRepository


class SemanticValidator:
    component_name = "semantic_validator"

    def __init__(self, prompt_repo: ComponentPromptRepository | None = None):
        self.prompt_repo = prompt_repo or ComponentPromptRepository()

    async def validate_intent(self, intent: StructuredIntent) -> ValidationResult:
        _ = self.prompt_repo.get_system_prompt(self.component_name)

        if intent.requires_clarification or not intent.can_proceed:
            return ValidationResult(
                status="clarification_required",
                reason="requires_clarification",
                clarification_questions=intent.clarification_questions,
                metadata={"source": "intent"},
            )
        if not intent.intent:
            return ValidationResult(
                status="clarification_required",
                reason="missing_intent",
                clarification_questions=["Пожалуйста, уточните цель запроса."],
            )
        return ValidationResult(status="approved")


