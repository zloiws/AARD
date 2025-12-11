"""
Execution API routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.execution_graph import ExecutionGraph, ExecutionNode, ExecutionEdge
from app.models import Artifact  # noqa: F401

logger = LoggingConfig.get_logger(__name__)
router = APIRouter(prefix="/api/execution", tags=["execution"])


@router.get("/{session_id}/graph")
async def get_execution_graph(session_id: str, db: Session = Depends(get_db)):
    """Return execution graph (nodes + edges) for a session"""
    graph = db.query(ExecutionGraph).filter(ExecutionGraph.session_id == session_id).first()
    if not graph:
        return {"id": None, "session_id": session_id, "nodes": [], "edges": []}

    nodes = [n.to_dict() for n in graph.nodes]
    edges = [e.to_dict() for e in graph.edges]
    return {"id": str(graph.id), "session_id": graph.session_id, "nodes": nodes, "edges": edges}


@router.get("/{session_id}/node/{node_id}")
async def get_node_details(session_id: str, node_id: str, db: Session = Depends(get_db)):
    """Get details for a specific node"""
    node = db.query(ExecutionNode).filter(ExecutionNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node.to_dict()


@router.post("/{session_id}/replay/{node_id}")
async def replay_node(session_id: str, node_id: str):
    """
    Replay a node execution. Currently a placeholder that enqueues replay (not implemented).
    """
    # TODO: integrate with execution engine / task queue to actually replay
    return {"status": "accepted", "message": "Replay requested (not implemented)", "node_id": node_id}


