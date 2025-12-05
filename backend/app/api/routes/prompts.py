"""
API routes for prompts
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.core.auth import get_current_user_optional
from app.models.prompt import Prompt, PromptType, PromptStatus
from app.services.prompt_service import PromptService

router = APIRouter(prefix="/api/prompts", tags=["prompts"])
logger = LoggingConfig.get_logger(__name__)


class PromptResponse(BaseModel):
    """Prompt response model"""
    id: UUID
    name: str
    prompt_text: str
    prompt_type: str
    level: int
    version: int
    status: str
    success_rate: Optional[float] = None
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CreatePromptRequest(BaseModel):
    """Request model for creating prompt"""
    name: str = Field(..., description="Prompt name")
    prompt_text: str = Field(..., description="Prompt text")
    prompt_type: PromptType = Field(..., description="Prompt type")
    level: int = Field(default=0, ge=0, le=4, description="Prompt level (0-4)")


class UpdatePromptRequest(BaseModel):
    """Request model for updating prompt"""
    prompt_text: Optional[str] = None
    name: Optional[str] = None
    status: Optional[PromptStatus] = None


class PromptVersionRequest(BaseModel):
    """Request model for creating prompt version"""
    prompt_text: str = Field(..., description="New prompt text for the version")


@router.get("/", response_model=List[PromptResponse])
async def list_prompts(
    prompt_type: Optional[PromptType] = None,
    status: Optional[PromptStatus] = None,
    level: Optional[int] = None,
    name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List prompts with filtering"""
    prompt_service = PromptService(db)
    prompts = prompt_service.list_prompts(
        prompt_type=prompt_type,
        status=status,
        level=level,
        name_search=name,
        limit=limit,
        offset=offset
    )
    return prompts


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: UUID,
    db: Session = Depends(get_db)
):
    """Get prompt by ID"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    return prompt


@router.post("/", response_model=PromptResponse)
async def create_prompt(
    request: CreatePromptRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: Optional["User"] = Depends(get_current_user_optional)
):
    """Create a new prompt"""
    try:
        prompt_service = PromptService(db)
        created_by = current_user.username if current_user else "system"
        
        prompt = prompt_service.create_prompt(
            name=request.name,
            prompt_text=request.prompt_text,
            prompt_type=request.prompt_type,
            level=request.level,
            created_by=created_by
        )
        
        return prompt
    except Exception as e:
        import traceback
        error_detail = f"Error creating prompt: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Error creating prompt: {error_detail}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: UUID,
    request: UpdatePromptRequest,
    db: Session = Depends(get_db)
):
    """Update a prompt"""
    prompt_service = PromptService(db)
    
    prompt = prompt_service.update_prompt(
        prompt_id=prompt_id,
        prompt_text=request.prompt_text,
        name=request.name,
        level=None  # Level update not supported in UpdatePromptRequest
    )
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    # Update status separately if provided
    if request.status is not None:
        if request.status == PromptStatus.DEPRECATED:
            prompt = prompt_service.deprecate_prompt(prompt_id)
        else:
            prompt.status = request.status.value.lower() if hasattr(request.status, 'value') else str(request.status).lower()
            db.commit()
            db.refresh(prompt)
    
    return prompt


@router.post("/{prompt_id}/version", response_model=PromptResponse)
async def create_prompt_version(
    prompt_id: UUID,
    request: PromptVersionRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: Optional["User"] = Depends(get_current_user_optional)
):
    """Create a new version of a prompt"""
    prompt_service = PromptService(db)
    created_by = current_user.username if current_user else "system"
    
    new_version = prompt_service.create_version(
        parent_prompt_id=prompt_id,
        prompt_text=request.prompt_text,
        created_by=created_by
    )
    
    if not new_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent prompt {prompt_id} not found"
        )
    
    return new_version


@router.post("/{prompt_id}/deprecate", response_model=PromptResponse)
async def deprecate_prompt(
    prompt_id: UUID,
    db: Session = Depends(get_db)
):
    """Deprecate (disable) a prompt"""
    prompt_service = PromptService(db)
    
    deprecated = prompt_service.deprecate_prompt(prompt_id)
    
    if not deprecated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    return deprecated


@router.get("/{prompt_id}/versions", response_model=List[PromptResponse])
async def get_prompt_versions(
    prompt_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all versions of a prompt"""
    prompt_service = PromptService(db)
    
    versions = prompt_service.get_prompt_versions(prompt_id)
    
    if not versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    return versions


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a prompt"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    db.delete(prompt)
    db.commit()
    
    return {"status": "deleted", "prompt_id": str(prompt_id)}

