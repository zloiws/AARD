"""
Prompt assignment model: maps prompts to models/servers/task types.
"""
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class PromptAssignment(Base):
    __tablename__ = "prompt_assignments"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    prompt_id = Column(PGUUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(PGUUID(as_uuid=True), ForeignKey("ollama_models.id", ondelete="SET NULL"), nullable=True, index=True)
    server_id = Column(PGUUID(as_uuid=True), ForeignKey("ollama_servers.id", ondelete="SET NULL"), nullable=True, index=True)
    task_type = Column(String(100), nullable=True)  # e.g., planning, reasoning, code_generation
    component_role = Column(String(100), nullable=False, index=True)  # e.g., interpretation, planning, routing
    stage = Column(String(100), nullable=False, index=True)  # duplicate of component_role for audit/compat
    scope = Column(String(50), nullable=False, default="global")  # global | agent | experiment
    agent_id = Column(PGUUID(as_uuid=True), nullable=True)
    experiment_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(255), nullable=True)

    prompt = relationship("Prompt", backref="assignments")
    model = relationship("OllamaModel", backref="prompt_assignments")
    server = relationship("OllamaServer", backref="prompt_assignments")

    def to_dict(self):
        return {
            "id": str(self.id),
            "prompt_id": str(self.prompt_id) if self.prompt_id else None,
            "model_id": str(self.model_id) if self.model_id else None,
            "server_id": str(self.server_id) if self.server_id else None,
            "task_type": self.task_type,
            "component_role": self.component_role,
            "stage": self.stage,
            "scope": self.scope,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "experiment_id": str(self.experiment_id) if self.experiment_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }


