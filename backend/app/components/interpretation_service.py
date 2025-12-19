"""
InterpretationService (component wrapper).

Role: Convert raw user input into a StructuredIntent.
Model role: Reasoning (semantic interpretation only).

Implementation note:
This wrapper delegates to existing `app.services.interpretation_service.InterpretationService`
to avoid breaking current behavior, while providing a stable typed contract.
"""

from __future__ import annotations

import json
from typing import Optional

from app.components.contracts import StructuredIntent
from app.components.prompt_repository import ComponentPromptRepository
from app.core.config import get_settings
from app.core.execution_context import ExecutionContext
from app.core.ollama_client import OllamaClient, TaskType
from app.services.interpretation_service import \
    InterpretationService as LegacyInterpretationService
from sqlalchemy.orm import Session


class InterpretationService:
    component_name = "interpretation"

    def __init__(
        self,
        db: Session,
        prompt_repo: Optional[ComponentPromptRepository] = None,
    ):
        self.db = db
        self.prompt_repo = prompt_repo or ComponentPromptRepository()
        self._legacy = LegacyInterpretationService(db)

    async def interpret(self, raw_input: str, context: ExecutionContext) -> StructuredIntent:
        # Explicit prompt artifact exists (not yet enforced in legacy service).
        _ = self.prompt_repo.get_system_prompt(self.component_name)

        interpretation = await self._legacy.interpret(raw_input, context)
        # By default legacy interpretation remains authoritative.
        # Optionally, if configured, refine/produce structured intent via LLM using the component system prompt.
        settings = get_settings()
        if getattr(settings, "interpretation_use_llm", False):
            try:
                system_prompt = self.prompt_repo.get_system_prompt(self.component_name)
                ollama = OllamaClient()
                # Build simple chat-style messages with explicit system role
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_input},
                ]
                # Use REASONING task type for interpretation
                resp = await ollama.generate(prompt=raw_input, task_type=TaskType.REASONING, system_prompt=system_prompt)
                # Attempt to parse JSON intent from response if present
                resp_text = getattr(resp, "response", None) or str(resp)
                parsed_intent = None
                try:
                    parsed = json.loads(resp_text)
                    # accept keys 'intent' or 'interpretation'
                    parsed_intent = parsed.get("intent") or parsed.get("interpretation")
                except Exception:
                    # fallback: use entire text as intent
                    parsed_intent = resp_text.strip()
                if parsed_intent:
                    interpretation["intent"] = parsed_intent
                # record that LLM was invoked and what system prompt used
                interpretation.setdefault("metadata", {})["llm_interpretation_used"] = True
                interpretation["metadata"]["llm_system_prompt_snippet"] = (system_prompt or "")[:300]
            except Exception:
                # non-fatal - preserve legacy interpretation
                interpretation.setdefault("metadata", {})["llm_interpretation_error"] = True
        return StructuredIntent(
            raw_input=raw_input,
            intent=interpretation.get("intent"),
            requires_clarification=bool(interpretation.get("requires_clarification")),
            clarification_questions=list(interpretation.get("clarification_questions") or []),
            can_proceed=bool(interpretation.get("can_proceed", True)),
            metadata={"legacy": interpretation},
        )


