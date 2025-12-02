"""
Web pages for artifacts
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.core.database import get_db
from app.models.artifact import Artifact, ArtifactType, ArtifactStatus

router = APIRouter(tags=["artifacts_pages"])


@router.get("/artifacts", response_class=HTMLResponse)
async def artifacts_list(
    request: Request,
    artifact_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Artifacts list page"""
    query = db.query(Artifact)
    
    if artifact_type:
        query = query.filter(Artifact.type == artifact_type.lower())
    if status_filter:
        query = query.filter(Artifact.status == status_filter.lower())
    
    artifacts = query.order_by(Artifact.created_at.desc()).limit(100).all()
    
    return templates.TemplateResponse(
        "artifacts/list.html",
        {
            "request": request,
            "artifacts": artifacts
        }
    )


@router.get("/artifacts/create", response_class=HTMLResponse)
async def artifacts_create_page(request: Request):
    """Create artifact page"""
    return templates.TemplateResponse(
        "artifacts/create.html",
        {
            "request": request
        }
    )


@router.get("/artifacts/{artifact_id}", response_class=HTMLResponse)
async def artifact_detail(
    request: Request,
    artifact_id: UUID,
    db: Session = Depends(get_db)
):
    """Artifact detail page"""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )
    
    return templates.TemplateResponse(
        "artifacts/detail.html",
        {
            "request": request,
            "artifact": artifact
        }
    )

