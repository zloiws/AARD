"""
Uncertainty Parameters model for storing learnable parameters
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class ParameterType(str, Enum):
    """Types of uncertainty parameters"""
    WEIGHT = "weight"  # Weight for uncertainty type (0.0-1.0)
    THRESHOLD = "threshold"  # Threshold for uncertainty level (0.0-1.0)
    KEYWORD_LIST = "keyword_list"  # List of keywords for detection
    COUNT_THRESHOLD = "count_threshold"  # Numeric threshold for counts
    SIMILARITY_THRESHOLD = "similarity_threshold"  # Threshold for similarity checks


class UncertaintyParameter(Base):
    """Model for storing learnable uncertainty assessment parameters"""
    __tablename__ = "uncertainty_parameters"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    parameter_name = Column(String(255), unique=True, nullable=False, index=True)
    parameter_type = Column(SQLEnum(ParameterType), nullable=False)
    
    # Value storage - depends on type
    numeric_value = Column(Float, nullable=True)  # For weights, thresholds
    text_value = Column(Text, nullable=True)  # For keyword lists (JSON string)
    json_value = Column(JSONB, nullable=True)  # For complex structures
    
    # Versioning and learning
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Learning metadata
    learning_history = Column(JSONB, nullable=True)  # History of changes: [{"version": 1, "value": ..., "reason": ..., "timestamp": ...}]
    performance_metrics = Column(JSONB, nullable=True)  # Metrics: {"accuracy": 0.95, "precision": 0.92, "recall": 0.88}
    last_improved_at = Column(DateTime, nullable=True)  # When parameter was last improved
    improvement_count = Column(Integer, default=0, nullable=False)  # Number of times improved
    
    # Metadata
    description = Column(Text, nullable=True)  # Human-readable description
    extra_metadata = Column(JSONB, nullable=True)  # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    
    def get_value(self) -> Any:
        """Get parameter value based on type"""
        if self.parameter_type == ParameterType.WEIGHT.value or self.parameter_type == ParameterType.THRESHOLD.value:
            return self.numeric_value
        elif self.parameter_type == ParameterType.KEYWORD_LIST.value:
            if self.json_value:
                return self.json_value
            elif self.text_value:
                import json
                try:
                    return json.loads(self.text_value)
                except:
                    return []
            return []
        elif self.parameter_type == ParameterType.COUNT_THRESHOLD.value:
            return int(self.numeric_value) if self.numeric_value else None
        elif self.parameter_type == ParameterType.SIMILARITY_THRESHOLD.value:
            return self.numeric_value
        return None
    
    def set_value(self, value: Any) -> None:
        """Set parameter value based on type"""
        if self.parameter_type == ParameterType.WEIGHT.value or self.parameter_type == ParameterType.THRESHOLD.value:
            self.numeric_value = float(value)
        elif self.parameter_type == ParameterType.KEYWORD_LIST.value:
            if isinstance(value, list):
                self.json_value = value
                import json
                self.text_value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, str):
                self.text_value = value
                import json
                try:
                    self.json_value = json.loads(value)
                except:
                    self.json_value = []
        elif self.parameter_type == ParameterType.COUNT_THRESHOLD.value:
            self.numeric_value = float(int(value))
        elif self.parameter_type == ParameterType.SIMILARITY_THRESHOLD.value:
            self.numeric_value = float(value)
    
    def add_to_history(self, value: Any, reason: str, metrics: Optional[Dict[str, Any]] = None) -> None:
        """Add entry to learning history"""
        if self.learning_history is None:
            self.learning_history = []
        
        history_entry = {
            "version": self.version,
            "value": value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics or {}
        }
        
        self.learning_history.append(history_entry)
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
    
    def update_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update performance metrics"""
        if self.performance_metrics is None:
            self.performance_metrics = {}
        
        self.performance_metrics.update(metrics)
        self.last_improved_at = datetime.now(timezone.utc)
        self.improvement_count += 1
    
    def __repr__(self):
        return f"<UncertaintyParameter(name={self.parameter_name}, type={self.parameter_type}, value={self.get_value()})>"

