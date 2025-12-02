"""
API routes for prompts
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.prompt import Prompt, PromptType, PromptStatus

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


@router.get("/", response_model=List[PromptResponse])
async def list_prompts(
    prompt_type: Optional[PromptType] = None,
    status: Optional[PromptStatus] = None,
    level: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List prompts"""
    query = db.query(Prompt)
    
    if prompt_type:
        query = query.filter(Prompt.prompt_type == prompt_type)
    if status:
        query = query.filter(Prompt.status == status)
    if level is not None:
        query = query.filter(Prompt.level == level)
    
    prompts = query.order_by(Prompt.created_at.desc()).limit(limit).all()
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
    db: Session = Depends(get_db)
):
    """Create a new prompt"""
    try:
        # Ensure lowercase values for DB constraints
        prompt_type_str = request.prompt_type.value.lower() if hasattr(request.prompt_type, 'value') else str(request.prompt_type).lower()
        status_str = "active"  # Always lowercase
        
        logger.debug(
            "Creating prompt",
            extra={
                "prompt_type": prompt_type_str,
                "status": status_str,
                "name": request.name,
                "level": request.level,
            }
        )
        
        prompt = Prompt(
            name=request.name,
            prompt_text=request.prompt_text,
            prompt_type=prompt_type_str,
            level=request.level,
            status=status_str,
            created_by="user"  # TODO: Get from auth
        )
        
        # Verify values are lowercase before commit
        if prompt.status != "active":
            prompt.status = "active"
        if hasattr(prompt.prompt_type, 'upper') and prompt.prompt_type.upper() == prompt.prompt_type:
            prompt.prompt_type = prompt.prompt_type.lower()
        
        logger.debug(
            "Prompt object created",
            extra={
                "prompt_id": str(prompt.id) if hasattr(prompt, 'id') and prompt.id else None,
                "prompt_type": prompt.prompt_type,
                "status": prompt.status,
            }
        )
        
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        
        return prompt
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = f"Error creating prompt: {str(e)}\n{traceback.format_exc()}"
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
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    if request.prompt_text is not None:
        prompt.prompt_text = request.prompt_text
    if request.name is not None:
        prompt.name = request.name
    if request.status is not None:
        prompt.status = request.status
    
    prompt.version += 1
    
    db.commit()
    db.refresh(prompt)
    
    return prompt


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

