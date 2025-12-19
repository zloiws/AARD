"""
Interpretation Service

Purpose:
- Provide a single, explicit interpretation layer for incoming user requests.
- Wraps ambiguity detection (UncertaintyService) and exposes a simple `interpret`
  API that returns a structured interpretation object suitable for storage in
  `ExecutionContext.metadata` and for making clarification decisions.

Why:
- Separate interpretation from planning/execution so the system can record
  "why" a request was understood a certain way, request clarifications early,
  and later persist InterpretationRule artifacts derived by MetaLearning.

This is intentionally small and non-invasive: it reuses `UncertaintyService`
to assess ambiguity and produce clarification questions. Next steps will
formalize InterpretationRule storage and richer intent extraction.
"""
from typing import Any, Dict, Optional
from uuid import uuid4

from app.models.interpretation import DecisionNode, DecisionTimeline
from app.services.uncertainty_service import UncertaintyService
from sqlalchemy.exc import SQLAlchemyError


class InterpretationService:
    """Simple interpretation layer that returns structured interpretation."""

    def __init__(self, db, uncertainty_service: Optional[UncertaintyService] = None):
        self.db = db
        self.uncertainty_service = uncertainty_service or UncertaintyService(db)

    async def interpret(self, message: str, context) -> Dict[str, Any]:
        """
        Interpret a user message.

        Returns a dict with:
        - assessment: raw uncertainty assessment
        - requires_clarification: bool
        - clarification_questions: list[str]
        - intent: best-effort placeholder (can be enhanced later)
        """
        # Use UncertaintyService to assess ambiguity and generate questions
        assessment = await self.uncertainty_service.assess_uncertainty(message, getattr(context, "metadata", None))
        handling = await self.uncertainty_service.handle_uncertainty(assessment)

        interpretation = {
            "intent": None,  # placeholder — later: intent extraction
            "assessment": assessment,
            "requires_clarification": handling.get("action") in ("request_clarification", "escalate"),
            "clarification_questions": handling.get("clarification_questions", []),
            "can_proceed": handling.get("action") in ("proceed", "proceed_with_assumptions")
        }

        # Best-effort intent: keep original message for now
        if interpretation["can_proceed"]:
            interpretation["intent"] = message
        # Persist interpretation as a DecisionNode in DecisionTimeline (best-effort, non-fatal)
        try:
            session_id = None
            if hasattr(context, "workflow_id") and context.workflow_id:
                session_id = str(context.workflow_id)
            elif getattr(context, "metadata", None) and context.metadata.get("workflow_id"):
                session_id = str(context.metadata.get("workflow_id"))
            else:
                # fallback: use generated id (won't be linked to workflow)
                session_id = str(uuid4())

            # Try to find existing timeline
            timeline = self.db.query(DecisionTimeline).filter(DecisionTimeline.session_id == session_id).first()
            if not timeline:
                timeline = DecisionTimeline(session_id=session_id, timeline_metadata={"created_by": "interpretation_service"})
                self.db.add(timeline)
                self.db.commit()
                self.db.refresh(timeline)

            node = DecisionNode(
                timeline_id=timeline.id,
                node_type="interpretation",
                payload=interpretation,
                status="created"
            )
            self.db.add(node)
            self.db.commit()
        except SQLAlchemyError as e:
            # Don't fail interpretation if DB write breaks; log to stdout for now
            try:
                # If LoggingConfig not available here, use print as fallback
                from app.core.logging_config import LoggingConfig
                logger = LoggingConfig.get_logger(__name__)
                logger.warning(f"Failed to persist interpretation node: {e}")
            except Exception:
                print(f"Failed to persist interpretation node: {e}")
        except Exception as e:
            # Generic catch - do not block processing
            try:
                from app.core.logging_config import LoggingConfig
                logger = LoggingConfig.get_logger(__name__)
                logger.debug(f"Interpretation persistence non-fatal error: {e}")
            except Exception:
                pass

        return interpretation


