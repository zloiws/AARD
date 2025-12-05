"""
Plan Template model for storing reusable plan patterns
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class TemplateStatus(str, Enum):
    """Template status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PlanTemplate(Base):
    """Plan Template model for storing reusable plan patterns"""
    __tablename__ = "plan_templates"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Template identification
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # e.g., "code_generation", "data_processing", "api_development"
    tags = Column(ARRAY(String), nullable=True)  # Array of tags for categorization
    
    # Template structure (abstracted from successful plans)
    goal_pattern = Column(Text, nullable=False)  # Abstracted goal pattern
    strategy_template = Column(JSONB, nullable=True)  # Template for strategy (approach, assumptions, constraints)
    steps_template = Column(JSONB, nullable=False)  # Template for steps structure
    alternatives_template = Column(JSONB, nullable=True)  # Template for alternatives
    
    # Metadata
    status = Column(String(20), nullable=False, default=TemplateStatus.DRAFT.value)
    version = Column(Integer, nullable=False, default=1)
    
    # Quality metrics (from source plans)
    success_rate = Column(Float, nullable=True)  # Average success rate of plans using this template
    avg_execution_time = Column(Integer, nullable=True)  # Average execution time in seconds
    usage_count = Column(Integer, nullable=False, default=0)  # How many times this template was used
    
    # Source information
    source_plan_ids = Column(ARRAY(PGUUID(as_uuid=True)), nullable=True)  # IDs of plans this template was extracted from
    source_task_descriptions = Column(ARRAY(Text), nullable=True)  # Descriptions of source tasks
    
    # Embedding for semantic search (if vector search is available)
    embedding = Column(ARRAY(Float), nullable=True)  # Vector embedding for semantic search
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    # Note: We don't have a direct foreign key to plans, but we store plan IDs in source_plan_ids
    
    def __repr__(self):
        return f"<PlanTemplate(id={self.id}, name={self.name}, category={self.category}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags or [],
            "goal_pattern": self.goal_pattern,
            "strategy_template": self.strategy_template,
            "steps_template": self.steps_template,
            "alternatives_template": self.alternatives_template,
            "status": self.status,
            "version": self.version,
            "success_rate": self.success_rate,
            "avg_execution_time": self.avg_execution_time,
            "usage_count": self.usage_count,
            "source_plan_ids": [str(pid) for pid in (self.source_plan_ids or [])],
            "source_task_descriptions": self.source_task_descriptions or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

