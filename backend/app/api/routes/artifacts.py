"""
API routes for artifacts (agents and tools)
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.models.user import User

from uuid import UUID

from app.core.auth import get_current_user_optional
from app.core.database import get_db
from app.core.ollama_client import OllamaClient, get_ollama_client
from app.models.artifact import Artifact, ArtifactStatus, ArtifactType
from app.services.artifact_generator import ArtifactGenerator
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class ArtifactResponse(BaseModel):
    """Artifact response model"""
    id: UUID
    type: str
    name: str
    description: Optional[str] = None
    version: int
    status: str
    security_rating: Optional[float] = None
    created_at: datetime  # FastAPI автоматически сериализует datetime в ISO формат
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class ArtifactDetailResponse(ArtifactResponse):
    """Detailed artifact response with code/prompt"""
    code: Optional[str] = None
    prompt: Optional[str] = None
    test_results: Optional[dict] = None


class CreateArtifactRequest(BaseModel):
    """Request model for creating artifact"""
    description: str = Field(..., description="Description of what artifact should do")
    artifact_type: ArtifactType = Field(..., description="Type of artifact (agent or tool)")
    context: Optional[dict] = Field(default_factory=dict, description="Additional context")


@router.get("/", response_model=List[ArtifactResponse])
async def list_artifacts(
    artifact_type: Optional[ArtifactType] = None,
    status: Optional[ArtifactStatus] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List artifacts"""
    query = db.query(Artifact)
    
    if artifact_type:
        query = query.filter(Artifact.type == artifact_type)
    if status:
        query = query.filter(Artifact.status == status)
    
    artifacts = query.order_by(Artifact.created_at.desc()).limit(limit).all()
    return artifacts


@router.get("/{artifact_id}", response_model=ArtifactDetailResponse)
async def get_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db)
):
    """Get artifact by ID"""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )
    
    return artifact


@router.post("/", response_model=ArtifactDetailResponse)
async def create_artifact(
    request: CreateArtifactRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    ollama_client: OllamaClient = Depends(get_ollama_client),
    current_user: Optional["User"] = Depends(get_current_user_optional)
):
    """Create a new artifact (agent or tool)"""
    generator = ArtifactGenerator(db, ollama_client)
    
    try:
        artifact = await generator.generate_artifact(
            description=request.description,
            artifact_type=request.artifact_type,
            context=request.context,
            created_by=current_user.username if current_user else "system"
        )
        return artifact
    except Exception as e:
        import traceback
        error_detail = f"Failed to generate artifact: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete an artifact"""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )
    
    db.delete(artifact)
    db.commit()
    
    return {"status": "deleted", "artifact_id": str(artifact_id)}

