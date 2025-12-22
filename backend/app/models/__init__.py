"""
SQLAlchemy models
"""
from app.core.database import Base
from app.models.agent import (Agent, AgentCapability, AgentHealthStatus,
                              AgentStatus)
from app.models.agent_conversation import (AgentConversation,  # noqa: F401
                                           ConversationStatus, MessageRole)
from app.models.agent_experiment import (AgentExperiment,  # noqa: F401
                                         ExperimentResult)
from app.models.agent_memory import (AgentMemory,  # noqa: F401
                                     AssociationType, MemoryAssociation,
                                     MemoryEntry, MemoryType)
from app.models.agent_team import (AgentTeam,  # noqa: F401
                                   CoordinationStrategy, TeamStatus,
                                   agent_team_association)
from app.models.agent_test import (AgentBenchmark,  # noqa: F401
                                   AgentBenchmarkRun, AgentTest, AgentTestRun,
                                   TestStatus, TestType)
from app.models.approval import (ApprovalRequest,  # noqa: F401
                                 ApprovalRequestStatus, ApprovalRequestType)
from app.models.artifact import (Artifact, ArtifactDependency,  # noqa: F401
                                 ArtifactStatus, ArtifactType)
from app.models.artifact_version import ArtifactVersion  # noqa: F401
from app.models.audit_report import (AuditReport, AuditStatus,  # noqa: F401
                                     AuditType)
from app.models.benchmark_result import BenchmarkResult  # noqa: F401
from app.models.benchmark_task import (BenchmarkTask,  # noqa: F401
                                       BenchmarkTaskType)
from app.models.chat_session import ChatMessage, ChatSession  # noqa: F401
from app.models.checkpoint import Checkpoint  # noqa: F401
from app.models.evolution import (ChangeType, EntityType,  # noqa: F401
                                  EvolutionHistory, Feedback, FeedbackType,
                                  TriggerType)
from app.models.execution_graph import (ExecutionEdge,  # noqa: F401
                                        ExecutionGraph, ExecutionNode)
from app.models.learning_pattern import (LearningPattern,  # noqa: F401
                                         PatternType)
from app.models.ollama_model import OllamaModel  # noqa: F401
from app.models.ollama_server import OllamaServer  # noqa: F401
from app.models.plan import Plan, PlanStatus  # noqa: F401
from app.models.plan_template import PlanTemplate, TemplateStatus  # noqa: F401
from app.models.project_metric import (MetricPeriod, MetricType,  # noqa: F401
                                       ProjectMetric)
from app.models.prompt import Prompt, PromptStatus, PromptType  # noqa: F401
from app.models.prompt_assignment import PromptAssignment  # noqa: F401
from app.models.request_log import RequestConsequence, RequestLog  # noqa: F401
from app.models.system_parameter import (ParameterCategory,  # noqa: F401
                                         SystemParameter, SystemParameterType)
from app.models.system_setting import (SettingCategory, SettingValueType,
                                       SystemSetting)
# Import all models here so Alembic can detect them
from app.models.task import Task, TaskStatus  # noqa: F401
from app.models.task_queue import QueueTask, TaskQueue  # noqa: F401
from app.models.test_table import TestTable  # noqa: F401
from app.models.tool import (Tool, ToolCategory,  # noqa: F401  # noqa: F401
                             ToolStatus)
from app.models.trace import ExecutionTrace  # noqa: F401
from app.models.uncertainty_parameters import (ParameterType,  # noqa: F401
                                               UncertaintyParameter)
from app.models.uncertainty_types import (UncertaintyLevel,  # noqa: F401
                                          UncertaintyType)
from app.models.user import Session, User, UserRole  # noqa: F401
from app.models.workflow_event import (EventSource, EventStatus,  # noqa: F401
                                       EventType, WorkflowEvent, WorkflowStage)

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
    "PromptAssignment",
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
    # Execution graph
    "ExecutionGraph",
    "ExecutionNode",
    "ExecutionEdge",
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
    # Test tables
    "TestTable",
]

