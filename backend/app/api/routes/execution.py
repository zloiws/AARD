"""Execution API routes (minimal stubs)"""
from datetime import datetime

from app.core.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/execution", tags=["execution"])


@router.get("/session/{session_id}/graph")
def get_execution_graph(session_id: str, db: Session = Depends(get_db)):
    """Return execution graph for a session (stub)"""
    # TODO: implement query to build graph from execution_graphs/nodes/edges
    return JSONResponse({"session_id": session_id, "graph": []})


@router.get("/session/{session_id}/node/{node_id}")
def get_node(session_id: str, node_id: str, db: Session = Depends(get_db)):
    """Return a single execution node (stub)"""
    return JSONResponse({"node_id": node_id, "payload": {}})
