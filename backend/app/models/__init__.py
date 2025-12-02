"""
SQLAlchemy models
"""
from app.core.database import Base

# Import all models here so Alembic can detect them
from app.models.task import Task, TaskStatus  # noqa: F401
from app.models.artifact import Artifact, ArtifactDependency, ArtifactType, ArtifactStatus  # noqa: F401
from app.models.ollama_server import OllamaServer  # noqa: F401
from app.models.ollama_model import OllamaModel  # noqa: F401
from app.models.prompt import Prompt, PromptType, PromptStatus  # noqa: F401
from app.models.approval import ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus  # noqa: F401
from app.models.evolution import EvolutionHistory, Feedback, EntityType, ChangeType, TriggerType, FeedbackType  # noqa: F401
from app.models.plan import Plan, PlanStatus  # noqa: F401

__all__ = [
    "Base",
    # Tasks
    "Task",
    "TaskStatus",
    # Artifacts
    "Artifact",
    "ArtifactDependency",
    "ArtifactType",
    "ArtifactStatus",
    # Ollama
    "OllamaServer",
    "OllamaModel",
    # Prompts
    "Prompt",
    "PromptType",
    "PromptStatus",
    # Approvals
    "ApprovalRequest",
    "ApprovalRequestType",
    "ApprovalRequestStatus",
    # Evolution
    "EvolutionHistory",
    "Feedback",
    "EntityType",
    "ChangeType",
    "TriggerType",
    "FeedbackType",
    # Plans
    "Plan",
    "PlanStatus",
]

