"""Meta API routes (minimal stubs)"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/evolution-timeline")
def get_evolution_timeline(limit: int = 50, db: Session = Depends(get_db)):
    """Return evolution timeline (stub)"""
    return JSONResponse({"timeline": [], "limit": limit})


@router.get("/components")
def list_components(db: Session = Depends(get_db)):
    """Return list of components (stub)"""
    return JSONResponse({"components": []})
