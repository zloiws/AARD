"""
Agent model for AARD platform
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List, Any
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    DRAFT = "draft"
    WAITING_APPROVAL = "waiting_approval"
    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class AgentHealthStatus(str, Enum):
    """Agent health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AgentCapability(str, Enum):
    """Agent capability types"""
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    PLANNING = "planning"
    REASONING = "reasoning"
    DATA_PROCESSING = "data_processing"
    TEXT_GENERATION = "text_generation"
    RESEARCH = "research"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"


class Agent(Base):
    """Agent model - represents an autonomous agent in the system"""
    __tablename__ = "agents"
    
    # Primary identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Identity and versioning
    version = Column(Integer, default=1, nullable=False)
    parent_agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    
    # Status and lifecycle
    status = Column(String(50), nullable=False, default=AgentStatus.DRAFT.value)
    created_by = Column(String(255), nullable=True)  # User who created the agent
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    activated_at = Column(DateTime, nullable=True)  # When agent was activated
    last_used_at = Column(DateTime, nullable=True)  # Last time agent was used
    
    # Heartbeat and health
    endpoint = Column(String(255), nullable=True)  # Agent endpoint URL for A2A communication
    last_heartbeat = Column(DateTime, nullable=True)  # Last heartbeat timestamp
    health_status = Column(String(50), nullable=True, default="unknown")  # healthy, degraded, unhealthy, unknown
    last_health_check = Column(DateTime, nullable=True)  # Last health check timestamp
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    
    # Agent configuration
    system_prompt = Column(Text, nullable=True)  # System prompt for the agent
    capabilities = Column(JSONB, nullable=True)  # List of AgentCapability values
    model_preference = Column(String(255), nullable=True)  # Preferred LLM model
    temperature = Column(String(10), default="0.7", nullable=True)  # Default temperature
    
    # Security and permissions
    identity_id = Column(String(255), nullable=True)  # SPIFFE ID or similar
    security_policies = Column(JSONB, nullable=True)  # Security policies for this agent
    allowed_actions = Column(JSONB, nullable=True)  # List of allowed actions
    forbidden_actions = Column(JSONB, nullable=True)  # List of forbidden actions
    
    # Resource limits
    max_concurrent_tasks = Column(Integer, default=1, nullable=False)
    rate_limit_per_minute = Column(Integer, nullable=True)
    memory_limit_mb = Column(Integer, nullable=True)
    
    # Metrics and performance
    total_tasks_executed = Column(Integer, default=0, nullable=False)
    successful_tasks = Column(Integer, default=0, nullable=False)
    failed_tasks = Column(Integer, default=0, nullable=False)
    average_execution_time = Column(Integer, nullable=True)  # in seconds
    success_rate = Column(String(10), nullable=True)  # Calculated field
    
    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name conflict)
    agent_metadata = Column(JSONB, nullable=True)  # Additional metadata
    tags = Column(JSONB, nullable=True)  # Tags for categorization
    
    # Relationships
    parent_agent = relationship("Agent", remote_side=[id], backref="child_agents")
    
    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, status={self.status}, version={self.version})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parent_agent_id": str(self.parent_agent_id) if self.parent_agent_id else None,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "system_prompt": self.system_prompt,
            "capabilities": self.capabilities,
            "model_preference": self.model_preference,
            "temperature": self.temperature,
            "identity_id": self.identity_id,
            "security_policies": self.security_policies,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "memory_limit_mb": self.memory_limit_mb,
            "total_tasks_executed": self.total_tasks_executed,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "average_execution_time": self.average_execution_time,
            "success_rate": self.success_rate,
            "metadata": self.agent_metadata,  # Map to 'metadata' in API response
            "agent_metadata": self.agent_metadata,
            "tags": self.tags,
        }

