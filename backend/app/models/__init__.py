"""
SQLAlchemy models
"""
from app.core.database import Base

# Import all models here so Alembic can detect them
from app.models.task import Task, TaskStatus  # noqa: F401
from app.models.artifact import Artifact, ArtifactDependency, ArtifactType, ArtifactStatus  # noqa: F401
from app.models.artifact_version import ArtifactVersion  # noqa: F401
from app.models.ollama_server import OllamaServer  # noqa: F401
from app.models.ollama_model import OllamaModel  # noqa: F401
from app.models.prompt import Prompt, PromptType, PromptStatus  # noqa: F401
from app.models.system_setting import SystemSetting, SettingValueType, SettingCategory
from app.models.tool import Tool, ToolStatus, ToolCategory  # noqa: F401  # noqa: F401
from app.models.approval import ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus  # noqa: F401
from app.models.evolution import EvolutionHistory, Feedback, EntityType, ChangeType, TriggerType, FeedbackType  # noqa: F401
from app.models.plan import Plan, PlanStatus  # noqa: F401
from app.models.plan_template import PlanTemplate, TemplateStatus  # noqa: F401
from app.models.trace import ExecutionTrace  # noqa: F401
from app.models.request_log import RequestLog, RequestConsequence  # noqa: F401
from app.models.task_queue import TaskQueue, QueueTask  # noqa: F401
from app.models.checkpoint import Checkpoint  # noqa: F401
from app.models.agent import Agent, AgentStatus, AgentHealthStatus, AgentCapability
from app.models.agent_team import AgentTeam, CoordinationStrategy, TeamStatus, agent_team_association  # noqa: F401
from app.models.agent_conversation import AgentConversation, ConversationStatus, MessageRole  # noqa: F401
from app.models.agent_experiment import AgentExperiment, ExperimentResult  # noqa: F401
from app.models.agent_test import (  # noqa: F401
    AgentTest, AgentTestRun, AgentBenchmark, AgentBenchmarkRun,
    TestStatus, TestType
)
from app.models.agent_memory import (  # noqa: F401
    AgentMemory, MemoryEntry, MemoryAssociation,
    MemoryType, AssociationType
)
from app.models.user import User, Session, UserRole  # noqa: F401
from app.models.learning_pattern import LearningPattern, PatternType  # noqa: F401
from app.models.chat_session import ChatSession, ChatMessage  # noqa: F401
from app.models.workflow_event import (  # noqa: F401
    WorkflowEvent, EventSource, EventType, EventStatus, WorkflowStage
)
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType  # noqa: F401
from app.models.benchmark_result import BenchmarkResult  # noqa: F401
from app.models.project_metric import ProjectMetric, MetricType, MetricPeriod  # noqa: F401
from app.models.audit_report import AuditReport, AuditType, AuditStatus  # noqa: F401
from app.models.uncertainty_parameters import UncertaintyParameter, ParameterType  # noqa: F401
from app.models.uncertainty_types import UncertaintyLevel, UncertaintyType  # noqa: F401
from app.models.system_parameter import SystemParameter, ParameterCategory, SystemParameterType  # noqa: F401

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
    "ArtifactVersion",
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
    # Plan Templates
    "PlanTemplate",
    "TemplateStatus",
    # Traces
    "ExecutionTrace",
    # Request Logs
    "RequestLog",
    "RequestConsequence",
    # Task Queues
    "TaskQueue",
    "QueueTask",
    # Checkpoints
    "Checkpoint",
    # Agents
    "Agent",
    "AgentStatus",
    "AgentHealthStatus",
    "AgentCapability",
    # Agent Teams
    "AgentTeam",
    "CoordinationStrategy",
    "TeamStatus",
    "agent_team_association",
    # Agent Conversations
    "AgentConversation",
    "ConversationStatus",
    "MessageRole",
    # Agent Experiments
    "AgentExperiment",
    "ExperimentResult",
    # Agent Tests
    "AgentTest",
    "AgentTestRun",
    "AgentBenchmark",
    "AgentBenchmarkRun",
    "TestStatus",
    "TestType",
    # Agent Memory
    "AgentMemory",
    "MemoryEntry",
    "MemoryAssociation",
    "MemoryType",
    "AssociationType",
    # Authentication
    "User",
    "Session",
    "UserRole",
    # Learning Patterns
    "LearningPattern",
    "PatternType",
    # Chat Sessions
    "ChatSession",
    "ChatMessage",
    # Workflow Events
    "WorkflowEvent",
    "EventSource",
    "EventType",
    "EventStatus",
    "WorkflowStage",
    # Benchmark
    "BenchmarkTask",
    "BenchmarkTaskType",
    "BenchmarkResult",
    # Project Metrics
    "ProjectMetric",
    "MetricType",
    "MetricPeriod",
    # Audit Reports
    "AuditReport",
    "AuditType",
    "AuditStatus",
    # Uncertainty Parameters
    "UncertaintyParameter",
    "ParameterType",
    # Uncertainty Types
    "UncertaintyLevel",
    "UncertaintyType",
    # System Parameters
    "SystemParameter",
    "ParameterCategory",
    "SystemParameterType",
]

