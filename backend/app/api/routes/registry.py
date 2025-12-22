"""
API routes for Capability & Agent Registry.

This is a non-LLM interface: it only exposes registry reads/writes.
Writes are gated to ADMIN role (human approval layer can be implemented on top).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from app.core.auth import get_current_user, security
from app.core.database import get_db
from app.models.user import UserRole
from app.registry.service import CapabilityRecord, RegistryService
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.user import User


router = APIRouter(prefix="/api/registry", tags=["registry"])


async def require_admin_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials=Depends(security),
):
    user = await get_current_user(request=request, credentials=credentials, db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


class CapabilityResponse(BaseModel):
    name: str
    source: str
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RegistryArtifactCreate(BaseModel):
    artifact_type: str = Field(..., description="artifact type: agent|tool")
    name: str
    description: Optional[str] = None
    code: Optional[str] = None
    prompt: Optional[str] = None
    status: str = Field(default="draft")
    version: int = Field(default=1, ge=1)
    security_rating: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    test_results: Optional[dict] = None


class RegistryArtifactResponse(BaseModel):
    id: str
    artifact_type: str
    name: str
    description: Optional[str] = None
    version: int
    status: str


class LifecycleUpdateRequest(BaseModel):
    status: str = Field(..., description="New lifecycle/status value (e.g. draft, waiting_approval, active, deprecated)")


@router.get("/capabilities", response_model=List[CapabilityResponse])
async def list_capabilities(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    svc = RegistryService(db)
    caps = svc.list_capabilities(include_inactive=include_inactive)
    return [CapabilityResponse(**c.__dict__) for c in caps]


@router.get("/lookup")
async def lookup_by_capability(
    capability: str,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    svc = RegistryService(db)
    return svc.lookup_by_capability(capability, include_inactive=include_inactive)


@router.get("/artifacts", response_model=List[RegistryArtifactResponse])
async def list_registry_artifacts(
    artifact_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    svc = RegistryService(db)
    artifacts = svc.list_artifacts(artifact_type=artifact_type, status=status, limit=limit, offset=offset)
    return [
        RegistryArtifactResponse(
            id=str(a.id),
            artifact_type=str(a.type),
            name=a.name,
            description=a.description,
            version=a.version,
            status=a.status,
        )
        for a in artifacts
    ]


@router.post("/artifacts", response_model=RegistryArtifactResponse)
async def register_registry_artifact(
    payload: RegistryArtifactCreate,
    db: Session = Depends(get_db),
    current_user: "User" = Depends(require_admin_user),
):
    svc = RegistryService(db)
    artifact = svc.register_artifact(
        artifact_type=payload.artifact_type,
        name=payload.name,
        description=payload.description,
        code=payload.code,
        prompt=payload.prompt,
        status=payload.status,
        version=payload.version,
        security_rating=payload.security_rating,
        test_results=payload.test_results,
        created_by=current_user.username,
    )
    return RegistryArtifactResponse(
        id=str(artifact.id),
        artifact_type=str(artifact.type),
        name=artifact.name,
        description=artifact.description,
        version=artifact.version,
        status=artifact.status,
    )


@router.post("/artifacts/{artifact_id}/lifecycle", response_model=RegistryArtifactResponse)
async def update_registry_artifact_lifecycle(
    artifact_id: UUID,
    payload: LifecycleUpdateRequest,
    db: Session = Depends(get_db),
    _current_user: "User" = Depends(require_admin_user),
):
    svc = RegistryService(db)
    artifact = svc.update_lifecycle(artifact_id, payload.status)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return RegistryArtifactResponse(
        id=str(artifact.id),
        artifact_type=str(artifact.type),
        name=artifact.name,
        description=artifact.description,
        version=artifact.version,
        status=artifact.status,
    )


