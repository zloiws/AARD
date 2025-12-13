\"\"\"Execution API routes (minimal stubs)\"\"\"
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix=\"/api/execution\", tags=[\"execution\"])


@router.get(\"/session/{session_id}/graph\")
def get_execution_graph(session_id: str, db: Session = Depends(get_db)):
    \"\"\"Return execution graph for a session (stub)\"\"\"
    # TODO: implement query to build graph from execution_graphs/nodes/edges
    return JSONResponse({\"session_id\": session_id, \"graph\": []})


@router.get(\"/session/{session_id}/node/{node_id}\")
def get_node(session_id: str, node_id: str, db: Session = Depends(get_db)):
    \"\"\"Return a single execution node (stub)\"\"\"
    return JSONResponse({\"node_id\": node_id, \"payload\": {}})


