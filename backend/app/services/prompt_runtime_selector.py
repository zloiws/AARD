"""
Prompt runtime selector: resolve system prompt for a given component_role/stage
using PromptAssignment resolution order:
  1) experiment (matching experiment_id / workflow_id / session_id)
  2) agent (matching agent_id)
  3) global
Fallback: disk-canonical prompt via PromptService.get_active_prompt(name)
"""
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.prompt_service import PromptService
from app.models.prompt_assignment import PromptAssignment
from app.models.prompt import Prompt
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class PromptRuntimeSelector:
    def __init__(self, db: Session):
        self.db = db
        self.prompt_service = PromptService(db)

    def _query_assignment(
        self,
        component_role: str,
        scope: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        experiment_id: Optional[UUID] = None,
        model_id: Optional[UUID] = None,
        server_id: Optional[UUID] = None,
        task_type: Optional[str] = None,
    ):
        q = self.db.query(PromptAssignment).filter(PromptAssignment.component_role == component_role)
        if scope:
            q = q.filter(PromptAssignment.scope == scope)
        if agent_id:
            q = q.filter(PromptAssignment.agent_id == agent_id)
        if experiment_id:
            q = q.filter(PromptAssignment.experiment_id == experiment_id)
        if model_id:
            q = q.filter(PromptAssignment.model_id == model_id)
        if server_id:
            q = q.filter(PromptAssignment.server_id == server_id)
        if task_type:
            q = q.filter(PromptAssignment.task_type == task_type)
        return q.order_by(PromptAssignment.created_at.desc()).all()

    def resolve(
        self,
        component_role: str,
        context_metadata: Optional[Dict[str, Any]] = None,
        *,
        task_type: Optional[str] = None,
        model_id: Optional[UUID] = None,
        server_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        experiment_id: Optional[UUID] = None,
    ) -> Dict[str, Optional[Any]]:
        """
        Resolve the system prompt to use for a given component_role using assignment resolution order.

        Returns dict:
          {
            "prompt_text": str | None,
            "prompt_id": UUID | None,
            "prompt_version": int | None,
            "source": "experiment|agent|global|disk"
          }
        """
        # Try experiment scope
        if not experiment_id and context_metadata:
            # common keys in metadata: experiment_id, workflow_id, session_id
            exp = context_metadata.get("experiment_id") or context_metadata.get("workflow_id") or context_metadata.get("session_id")
            try:
                experiment_id = UUID(exp) if exp else None
            except Exception:
                experiment_id = None

        # 1) experiment scope
        if experiment_id:
            assigns = self._query_assignment(component_role, scope="experiment", experiment_id=experiment_id, model_id=model_id, server_id=server_id, task_type=task_type)
            if assigns:
                a = assigns[0]
                p = self.prompt_service.get_prompt(a.prompt_id)
                if p:
                    logger.debug(f"Resolved prompt for {component_role} from experiment assignment {a.id}")
                    return {"prompt_text": p.prompt_text, "prompt_id": a.prompt_id, "prompt_version": getattr(p, "version", None), "source": "experiment"}

        # 2) agent scope
        if agent_id:
            assigns = self._query_assignment(component_role, scope="agent", agent_id=agent_id, model_id=model_id, server_id=server_id, task_type=task_type)
            if assigns:
                a = assigns[0]
                p = self.prompt_service.get_prompt(a.prompt_id)
                if p:
                    logger.debug(f"Resolved prompt for {component_role} from agent assignment {a.id}")
                    return {"prompt_text": p.prompt_text, "prompt_id": a.prompt_id, "prompt_version": getattr(p, "version", None), "source": "agent"}

        # 3) global scope
        assigns = self._query_assignment(component_role, scope="global", model_id=model_id, server_id=server_id, task_type=task_type)
        if assigns:
            a = assigns[0]
            p = self.prompt_service.get_prompt(a.prompt_id)
            if p:
                logger.debug(f"Resolved prompt for {component_role} from global assignment {a.id}")
                return {"prompt_text": p.prompt_text, "prompt_id": a.prompt_id, "prompt_version": getattr(p, "version", None), "source": "global"}

        # 4) fallback: disk canonical via PromptService.get_active_prompt using STAGE_NAME mapping or component_role
        try:
            # Try using prompt name == component_role
            active = self.prompt_service.get_active_prompt(name=component_role)
            if active:
                logger.debug(f"Resolved prompt for {component_role} from disk-canonical active prompt {active.id}")
                return {"prompt_text": active.prompt_text, "prompt_id": active.id, "prompt_version": getattr(active, "version", None), "source": "disk"}
        except Exception:
            pass

        logger.debug(f"No prompt resolved for {component_role}; returning None")
        return {"prompt_text": None, "prompt_id": None, "prompt_version": None, "source": None}


