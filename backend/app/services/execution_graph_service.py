"""
ExecutionGraphService: manage execution graphs, nodes and edges.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.execution_graph import (ExecutionEdge, ExecutionGraph,
                                        ExecutionNode)
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class ExecutionGraphService:
    """Service for creating and updating execution graphs"""

    def __init__(self, db: Optional[Session] = None):
        # If db is provided, use it for operations; otherwise create short-lived sessions
        self._db_provided = db is not None
        self._db = db

    def _get_session(self) -> Session:
        return self._db if self._db_provided else SessionLocal()

    def create_or_get_graph(self, session_id: str) -> ExecutionGraph:
        db = self._get_session()
        try:
            graph = db.query(ExecutionGraph).filter(ExecutionGraph.session_id == session_id).first()
            if graph:
                return graph
            graph = ExecutionGraph(session_id=session_id)
            db.add(graph)
            db.commit()
            db.refresh(graph)
            return graph
        finally:
            if not self._db_provided:
                db.close()

    def add_node(self, graph_id, node_type: str, name: Optional[str] = None, data: Optional[Dict[str, Any]] = None,
                 status: str = "pending", chat_message_id: Optional[str] = None) -> ExecutionNode:
        db = self._get_session()
        try:
            node = ExecutionNode(
                graph_id=graph_id,
                node_type=node_type,
                name=name,
                data=data or {},
                status=status,
                chat_message_id=chat_message_id
            )
            db.add(node)
            db.commit()
            db.refresh(node)
            return node
        finally:
            if not self._db_provided:
                db.close()

    def add_edge(self, graph_id, source_node_id, target_node_id, label: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        db = self._get_session()
        try:
            edge = ExecutionEdge(
                graph_id=graph_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                label=label,
                data=data or {}
            )
            db.add(edge)
            db.commit()
            db.refresh(edge)
            return edge
        finally:
            if not self._db_provided:
                db.close()

    def update_node_status(self, node_id, status: str, result_data: Optional[Dict[str, Any]] = None):
        db = self._get_session()
        try:
            node = db.query(ExecutionNode).filter(ExecutionNode.id == node_id).first()
            if not node:
                raise ValueError(f"Node {node_id} not found")
            node.status = status
            now = datetime.now(timezone.utc)
            if status == "executing":
                node.started_at = now
            if status in ("success", "error", "completed"):
                node.completed_at = now
                if result_data and "execution_time_ms" in result_data:
                    node.execution_time_ms = result_data.get("execution_time_ms")
            if result_data:
                # merge result into data
                node.data = {**(node.data or {}), **result_data}
            db.add(node)
            db.commit()
            db.refresh(node)
            return node
        finally:
            if not self._db_provided:
                db.close()


