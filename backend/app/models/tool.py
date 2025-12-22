"""
Tool model for AARD platform
Tools are executable functions that agents can use to perform actions
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.core.database import Base
from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class ToolStatus(str, Enum):
    """Tool status enumeration"""
    DRAFT = "draft"
    WAITING_APPROVAL = "waiting_approval"
    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class ToolCategory(str, Enum):
    """Tool category types"""
    FILE_OPERATIONS = "file_operations"
    NETWORK = "network"
    DATABASE = "database"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    DATA_PROCESSING = "data_processing"
    SEARCH = "search"
    API = "api"
    SYSTEM = "system"
    CUSTOM = "custom"


class Tool(Base):
    """Tool model - represents an executable tool/function"""
    __tablename__ = "tools"
    
    # Primary identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # ToolCategory value
    
    # Versioning
    version = Column(Integer, default=1, nullable=False)
    parent_tool_id = Column(PGUUID(as_uuid=True), ForeignKey("tools.id"), nullable=True)
    
    # Status and lifecycle
    status = Column(String(50), nullable=False, default=ToolStatus.DRAFT.value)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    activated_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Tool implementation
    code = Column(Text, nullable=True)  # Python code for the tool
    entry_point = Column(String(255), nullable=True)  # Function name to call (default: "execute")
    language = Column(String(50), default="python", nullable=False)  # python, javascript, etc.
    
    # Tool schema (input/output parameters)
    input_schema = Column(JSONB, nullable=True)  # JSON Schema for input parameters
    output_schema = Column(JSONB, nullable=True)  # JSON Schema for output
    parameters = Column(JSONB, nullable=True)  # Simplified parameter definitions
    
    # Dependencies and requirements
    dependencies = Column(JSONB, nullable=True)  # List of required packages/modules
    requirements = Column(Text, nullable=True)  # requirements.txt content
    
    # Security and permissions
    security_policies = Column(JSONB, nullable=True)  # Security policies
    allowed_agents = Column(JSONB, nullable=True)  # List of agent IDs allowed to use this tool
    forbidden_agents = Column(JSONB, nullable=True)  # List of agent IDs forbidden to use
    requires_approval = Column(Boolean, default=False, nullable=False)  # Require approval before execution
    
    # Resource limits
    timeout_seconds = Column(Integer, nullable=True)  # Execution timeout
    max_memory_mb = Column(Integer, nullable=True)  # Memory limit
    rate_limit_per_minute = Column(Integer, nullable=True)  # Rate limiting
    
    # Metrics and performance
    total_executions = Column(Integer, default=0, nullable=False)
    successful_executions = Column(Integer, default=0, nullable=False)
    failed_executions = Column(Integer, default=0, nullable=False)
    average_execution_time = Column(Integer, nullable=True)  # in milliseconds
    success_rate = Column(String(10), nullable=True)  # Calculated field
    
    # Metadata
    tool_metadata = Column(JSONB, nullable=True)  # Additional metadata (renamed from metadata)
    tags = Column(JSONB, nullable=True)  # Tags for categorization
    examples = Column(JSONB, nullable=True)  # Example usage
    
    # Relationships
    parent_tool = relationship("Tool", remote_side=[id], backref="child_tools")
    
    def __repr__(self):
        return f"<Tool(id={self.id}, name={self.name}, status={self.status}, version={self.version})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "parent_tool_id": str(self.parent_tool_id) if self.parent_tool_id else None,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "code": self.code,
            "entry_point": self.entry_point,
            "language": self.language,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "requirements": self.requirements,
            "security_policies": self.security_policies,
            "allowed_agents": self.allowed_agents,
            "forbidden_agents": self.forbidden_agents,
            "requires_approval": self.requires_approval,
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "average_execution_time": self.average_execution_time,
            "success_rate": self.success_rate,
            "metadata": self.tool_metadata,  # Map to 'metadata' in API response
            "tool_metadata": self.tool_metadata,
            "tags": self.tags,
            "examples": self.examples,
        }

