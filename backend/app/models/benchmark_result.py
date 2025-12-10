"""
Benchmark Result model for storing execution results
"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class BenchmarkResult(Base):
    """Benchmark Result model for storing execution results"""
    __tablename__ = "benchmark_results"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    benchmark_task_id = Column(PGUUID(as_uuid=True), ForeignKey("benchmark_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(PGUUID(as_uuid=True), ForeignKey("ollama_models.id", ondelete="SET NULL"), nullable=True, index=True)
    server_id = Column(PGUUID(as_uuid=True), ForeignKey("ollama_servers.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Execution data
    execution_time = Column(Float, nullable=True)  # Time in seconds
    output = Column(Text, nullable=True)  # Model output
    score = Column(Float, nullable=True)  # Overall score (0.0-1.0)
    metrics = Column(JSONB, nullable=True)  # Detailed metrics as JSON
    passed = Column(Boolean, nullable=False, default=False)  # Whether the test passed
    
    # Additional metadata
    error_message = Column(Text, nullable=True)  # Error message if failed
    execution_metadata = Column(JSONB, nullable=True)  # Additional execution metadata
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Relationships
    task = relationship("BenchmarkTask", back_populates="results")
    model = relationship("OllamaModel", backref="benchmark_results")
    server = relationship("OllamaServer", backref="benchmark_results")
    
    def __repr__(self):
        return f"<BenchmarkResult(id={self.id}, task_id={self.benchmark_task_id}, passed={self.passed}, score={self.score})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "benchmark_task_id": str(self.benchmark_task_id),
            "model_id": str(self.model_id) if self.model_id else None,
            "server_id": str(self.server_id) if self.server_id else None,
            "execution_time": self.execution_time,
            "output": self.output,
            "score": self.score,
            "metrics": self.metrics,
            "passed": self.passed,
            "error_message": self.error_message,
            "execution_metadata": self.execution_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

