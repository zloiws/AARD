"""
Agent test and benchmark models
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.core.database import Base
from sqlalchemy import (JSON, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class TestStatus(str, Enum):
    """Test status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


class TestType(str, Enum):
    """Test type enumeration"""
    FUNCTIONAL = "functional"  # Functional correctness test
    PERFORMANCE = "performance"  # Performance benchmark
    STRESS = "stress"  # Stress test
    SECURITY = "security"  # Security test
    INTEGRATION = "integration"  # Integration test
    REGRESSION = "regression"  # Regression test


class AgentTest(Base):
    """Agent test definition"""
    __tablename__ = "agent_tests"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Test configuration
    test_type = Column(String(50), nullable=False)  # TestType enum
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    # Test input/output
    input_data = Column(JSONB, nullable=True)  # Test input (task, context, etc.)
    expected_output = Column(JSONB, nullable=True)  # Expected result
    validation_rules = Column(JSONB, nullable=True)  # Validation rules (regex, schema, etc.)
    
    # Test execution settings
    timeout_seconds = Column(Integer, default=60, nullable=False)
    max_retries = Column(Integer, default=0, nullable=False)
    required_tools = Column(JSONB, nullable=True)  # List of required tool names
    
    # Metadata
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    tags = Column(JSONB, nullable=True)  # Tags for categorization
    
    # Relationships
    agent = relationship("Agent", backref="tests")
    test_runs = relationship("AgentTestRun", back_populates="test", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentTest(id={self.id}, name={self.name}, type={self.test_type}, agent_id={self.agent_id})>"


class AgentTestRun(Base):
    """Agent test execution result"""
    __tablename__ = "agent_test_runs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    test_id = Column(PGUUID(as_uuid=True), ForeignKey("agent_tests.id"), nullable=False)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    agent_version = Column(Integer, nullable=True)  # Agent version at time of test
    
    # Execution status
    status = Column(String(50), nullable=False)  # TestStatus enum
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Execution duration in milliseconds
    
    # Test results
    input_data = Column(JSONB, nullable=True)  # Actual input used
    output_data = Column(JSONB, nullable=True)  # Actual output from agent
    expected_output = Column(JSONB, nullable=True)  # Expected output
    
    # Validation results
    validation_passed = Column(String(10), nullable=True)  # "true", "false", "partial"
    validation_details = Column(JSONB, nullable=True)  # Detailed validation results
    
    # Performance metrics
    tokens_used = Column(Integer, nullable=True)
    llm_calls = Column(Integer, nullable=True)
    tool_calls = Column(Integer, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)
    
    # Error information
    error_message = Column(Text, nullable=True)
    error_type = Column(String(255), nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Metadata
    run_by = Column(String(255), nullable=True)  # User or system that ran the test
    notes = Column(Text, nullable=True)
    
    # Relationships
    test = relationship("AgentTest", back_populates="test_runs")
    agent = relationship("Agent")
    
    def __repr__(self):
        return f"<AgentTestRun(id={self.id}, test_id={self.test_id}, status={self.status}, duration_ms={self.duration_ms})>"


class AgentBenchmark(Base):
    """Agent benchmark definition"""
    __tablename__ = "agent_benchmarks"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Benchmark configuration
    benchmark_type = Column(String(50), nullable=False)  # TestType enum
    agent_ids = Column(JSONB, nullable=False)  # List of agent IDs to compare
    
    # Benchmark tasks
    tasks = Column(JSONB, nullable=False)  # List of tasks to execute
    
    # Benchmark settings
    iterations = Column(Integer, default=1, nullable=False)  # Number of iterations per agent
    timeout_seconds = Column(Integer, default=300, nullable=False)
    parallel_execution = Column(String(10), default="false", nullable=False)  # "true" or "false"
    
    # Metrics to collect
    metrics = Column(JSONB, nullable=True)  # List of metrics to collect (latency, accuracy, etc.)
    
    # Metadata
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    tags = Column(JSONB, nullable=True)
    
    # Relationships
    benchmark_runs = relationship("AgentBenchmarkRun", back_populates="benchmark", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentBenchmark(id={self.id}, name={self.name}, type={self.benchmark_type})>"


class AgentBenchmarkRun(Base):
    """Agent benchmark execution result"""
    __tablename__ = "agent_benchmark_runs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    benchmark_id = Column(PGUUID(as_uuid=True), ForeignKey("agent_benchmarks.id"), nullable=False)
    
    # Execution status
    status = Column(String(50), nullable=False)  # TestStatus enum
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Results per agent
    agent_results = Column(JSONB, nullable=False)  # {agent_id: {metrics, results, status}}
    
    # Summary statistics
    summary = Column(JSONB, nullable=True)  # Overall statistics (best agent, avg metrics, etc.)
    
    # Error information
    error_message = Column(Text, nullable=True)
    error_type = Column(String(255), nullable=True)
    
    # Metadata
    run_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    benchmark = relationship("AgentBenchmark", back_populates="benchmark_runs")
    
    def __repr__(self):
        return f"<AgentBenchmarkRun(id={self.id}, benchmark_id={self.benchmark_id}, status={self.status})>"

