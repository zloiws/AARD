"""
Benchmark Task model for storing test tasks
"""
from datetime import datetime
from enum import Enum
from uuid import uuid4
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class BenchmarkTaskType(str, Enum):
    """Benchmark task type enumeration"""
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    REASONING = "reasoning"
    PLANNING = "planning"
    GENERAL_CHAT = "general_chat"


class BenchmarkTask(Base):
    """Benchmark Task model for storing test tasks"""
    __tablename__ = "benchmark_tasks"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Task identification
    task_type = Column(SQLEnum(BenchmarkTaskType), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)  # e.g., "python", "javascript", "math"
    name = Column(String(255), nullable=False, unique=True)  # Unique task name
    
    # Task content
    task_description = Column(Text, nullable=False)  # The actual task/prompt
    expected_output = Column(Text, nullable=True)  # Expected output (can be partial or example)
    evaluation_criteria = Column(JSONB, nullable=True)  # Criteria for evaluation as JSON
    
    # Additional metadata
    difficulty = Column(String(20), nullable=True)  # "easy", "medium", "hard"
    tags = Column(JSONB, nullable=True)  # Array of tags for filtering
    task_metadata = Column(JSONB, nullable=True)  # Additional metadata (renamed from metadata to avoid SQLAlchemy conflict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships (will be added after BenchmarkResult model is created)
    # results = relationship("BenchmarkResult", back_populates="task", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BenchmarkTask(id={self.id}, name='{self.name}', type='{self.task_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "task_type": self.task_type.value if isinstance(self.task_type, Enum) else self.task_type,
            "category": self.category,
            "name": self.name,
            "task_description": self.task_description,
            "expected_output": self.expected_output,
            "evaluation_criteria": self.evaluation_criteria,
            "difficulty": self.difficulty,
            "tags": self.tags,
            "task_metadata": self.task_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

