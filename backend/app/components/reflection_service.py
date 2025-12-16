"""
ReflectionService — component wrapper.

Role: Analyze execution outcomes and produce ReflectionRecord.
Model role: Reasoning (analysis only).

Implementation note:
This wrapper delegates to existing `app.services.reflection_service.ReflectionService`
to avoid breaking current behavior, while providing a stable typed contract.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.components.contracts import ReflectionRecord
from app.components.prompt_repository import ComponentPromptRepository
from app.services.reflection_service import ReflectionService as LegacyReflectionService


class ReflectionService:
    component_name = "reflection"

    def __init__(self, db: Session, prompt_repo: Optional[ComponentPromptRepository] = None):
        self.db = db
        self.prompt_repo = prompt_repo or ComponentPromptRepository()
        self._legacy = LegacyReflectionService(db)

    async def reflect(
        self,
        plan: Dict[str, Any],
        execution_result: Dict[str, Any],
        human_feedback: Optional[Dict[str, Any]] = None,
    ) -> ReflectionRecord:
        _ = self.prompt_repo.get_system_prompt(self.component_name)

        # Minimal mapping: treat failures as execution_failure.
        ok = bool(execution_result.get("success", execution_result.get("ok", False)))
        category = "success" if ok else "execution_failure"
        summary = execution_result.get("summary") or execution_result.get("error") or None

        # We do not auto-apply any rule updates here; just return a record.
        return ReflectionRecord(
            category=category, summary=summary, metadata={"plan": plan, "result": execution_result, "feedback": human_feedback}
        )


