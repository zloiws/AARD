"""
Events API for UI observability
Provides:
- GET /api/events/recent
- GET /api/events/graph
"""
from typing import Any, Dict, Optional

from app.core.database import get_db
from app.models.execution_graph import ExecutionGraph
from app.services.workflow_event_service import WorkflowEventService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/recent")
async def get_recent_events(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow id"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    svc = WorkflowEventService(db)
    events = svc.get_recent_events(limit=limit, workflow_id=workflow_id)
    return {"events": [e.to_dict() for e in events], "total": len(events)}


@router.get("/graph")
async def get_graph(
    session_id: Optional[str] = Query(None, description="Session id to fetch execution graph for"),
    db: Session = Depends(get_db),
):
    """
    Return execution graph nodes/edges for UI visualization.
    Prefers ExecutionGraph rows if available; otherwise returns empty graph.
    """
    if session_id:
        graph = db.query(ExecutionGraph).filter(ExecutionGraph.session_id == session_id).order_by(ExecutionGraph.created_at.desc()).first()
    else:
        graph = db.query(ExecutionGraph).order_by(ExecutionGraph.created_at.desc()).first()

    if not graph:
        return {"nodes": [], "edges": []}

    nodes = [n.to_dict() for n in graph.nodes]
    edges = [e.to_dict() for e in graph.edges]
    return {"nodes": nodes, "edges": edges, "graph_id": str(graph.id)}


