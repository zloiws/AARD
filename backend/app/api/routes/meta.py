"""
Meta API routes
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.artifact import Artifact
from app.models.artifact_version import ArtifactVersion
from app.core.meta_tracker import MetaTracker

logger = LoggingConfig.get_logger(__name__)
router = APIRouter(prefix="/api/meta", tags=["meta"])

# Simple singleton meta tracker for API usage
_meta_tracker = MetaTracker()


@router.get("/components")
async def get_all_components(db: Session = Depends(get_db)):
    """Return components (artifacts) with basic version info"""
    artifacts = db.query(Artifact).all()
    result = {}
    for art in artifacts:
        versions = []
        avs = db.query(ArtifactVersion).filter(ArtifactVersion.artifact_id == art.id).order_by(ArtifactVersion.created_at.asc()).all()
        for av in avs:
            versions.append({
                "version": av.version,
                "created_at": av.created_at.isoformat() if av.created_at else None,
                "created_by": av.created_by,
                "file_path": av.file_path if hasattr(av, "file_path") else None,
                "test_results": av.test_results if hasattr(av, "test_results") else {},
                "performance_metrics": av.performance_metrics if hasattr(av, "performance_metrics") else {},
            })
        result[art.name] = {
            "id": str(art.id),
            "type": art.type,
            "current_version": art.version,
            "versions": versions,
            "usage_count": getattr(art, "usage_count", 0),
            "last_used": getattr(art, "last_used", None),
        }
    return {"components": result}


@router.get("/evolution-timeline")
async def get_evolution_timeline():
    """Return evolution timeline from MetaTracker"""
    timeline = await _meta_tracker.get_evolution_graph()
    return timeline


@router.get("/components/{component_id}/diff/{version_a}/{version_b}")
async def get_component_diff(component_id: str, version_a: str, version_b: str):
    """Return diff between two versions (placeholder)"""
    # TODO: implement diffing between versions
    raise HTTPException(status_code=501, detail="Diff endpoint not implemented")


@router.post("/components/{component_id}/rollback/{version}")
async def rollback_component(component_id: str, version: str):
    """Rollback component to specified version (placeholder)"""
    # TODO: implement RBAC and rollback logic
    return {"status": "accepted", "message": "Rollback requested (not implemented)", "component_id": component_id, "version": version}


