"""
Execution graph models: ExecutionGraph, ExecutionNode, ExecutionEdge
"""
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from app.core.database import Base
from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class ExecutionGraph(Base):
    """Execution graph for a chat/session"""
    __tablename__ = "execution_graphs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # relationships
    nodes = relationship("ExecutionNode", backref="graph", cascade="all, delete-orphan")
    edges = relationship("ExecutionEdge", backref="graph", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExecutionGraph(id={self.id}, session_id={self.session_id})>"


class ExecutionNode(Base):
    """Node inside execution graph"""
    __tablename__ = "execution_nodes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    graph_id = Column(PGUUID(as_uuid=True), ForeignKey("execution_graphs.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type = Column(String(50), nullable=False)  # agent, tool, user_input, plan, response
    name = Column(String(255), nullable=True)
    data = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # pending, executing, success, error
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    # optional link to chat message or workflow event
    chat_message_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    workflow_event_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "graph_id": str(self.graph_id),
            "node_type": self.node_type,
            "name": self.name,
            "data": self.data,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "chat_message_id": str(self.chat_message_id) if self.chat_message_id else None,
            "workflow_event_id": str(self.workflow_event_id) if self.workflow_event_id else None,
        }

    def __repr__(self):
        return f"<ExecutionNode(id={self.id}, type={self.node_type}, status={self.status})>"


class ExecutionEdge(Base):
    """Edge between execution nodes"""
    __tablename__ = "execution_edges"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    graph_id = Column(PGUUID(as_uuid=True), ForeignKey("execution_graphs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    target_node_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    label = Column(String(255), nullable=True)
    data = Column(JSON, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "graph_id": str(self.graph_id),
            "source_node_id": str(self.source_node_id),
            "target_node_id": str(self.target_node_id),
            "label": self.label,
            "data": self.data,
        }

    def __repr__(self):
        return f"<ExecutionEdge(id={self.id}, source={self.source_node_id}, target={self.target_node_id})>"


