"""Execution Graph API routes"""
from datetime import datetime

from app.core.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/execution", tags=["execution_graph"])


@router.get("/session/{session_id}/graph_full")
def get_execution_graph_full(session_id: str, db: Session = Depends(get_db)):
    """Return execution graph for a session (full implementation)"""
    try:
        graph_row = db.execute(
            sa_text("SELECT id, session_id, metadata, created_at FROM execution_graphs WHERE session_id = :sid"),
            {"sid": session_id}
        ).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not graph_row:
        raise HTTPException(status_code=404, detail="Execution graph not found")

    graph_id = str(graph_row[0])
    metadata = graph_row[2] or {}
    created_at = graph_row[3].isoformat() if isinstance(graph_row[3], datetime) else str(graph_row[3]) if graph_row[3] else None

    # Nodes
    nodes = []
    try:
        node_rows = db.execute(
            sa_text("SELECT id, node_type, payload, status, created_at FROM execution_nodes WHERE graph_id = :gid ORDER BY created_at ASC"),
            {"gid": graph_id}
        ).fetchall()
        for nr in node_rows:
            nodes.append({
                "id": str(nr[0]),
                "node_type": nr[1],
                "payload": nr[2] or {},
                "status": nr[3],
                "created_at": nr[4].isoformat() if isinstance(nr[4], datetime) else str(nr[4]) if nr[4] else None
            })
    except Exception:
        nodes = []

    # Edges
    edges = []
    try:
        edge_rows = db.execute(
            sa_text("SELECT id, from_node, to_node, metadata, created_at FROM execution_edges WHERE graph_id = :gid"),
            {"gid": graph_id}
        ).fetchall()
        for er in edge_rows:
            edges.append({
                "id": str(er[0]),
                "from_node": str(er[1]),
                "to_node": str(er[2]),
                "metadata": er[3] or {},
                "created_at": er[4].isoformat() if isinstance(er[4], datetime) else str(er[4]) if er[4] else None
            })
    except Exception:
        edges = []

    return JSONResponse({
        "session_id": session_id,
        "graph": {
            "id": graph_id,
            "metadata": metadata,
            "created_at": created_at,
            "nodes": nodes,
            "edges": edges
        }
    })
