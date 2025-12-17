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


class AssignmentRequest(BaseModel):
    model_id: Optional[UUID] = None
    server_id: Optional[UUID] = None
    task_type: Optional[str] = None
    component_role: Optional[str] = None
    stage: Optional[str] = None
    scope: Optional[str] = "global"
    agent_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None


class AssignmentResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    model_id: Optional[UUID] = None
    server_id: Optional[UUID] = None
    task_type: Optional[str] = None
    component_role: Optional[str] = None
    stage: Optional[str] = None
    scope: Optional[str] = None
    agent_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    created_at: datetime
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


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


@router.get("/{prompt_id}/metrics")
async def get_prompt_metrics(
    prompt_id: UUID,
    db: Session = Depends(get_db)
):
    """Get metrics for a prompt"""
    prompt_service = PromptService(db)
    prompt = prompt_service.get_prompt(prompt_id)
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    # Get usage history from improvement_history
    usage_history = []
    if prompt.improvement_history:
        usage_results = [
            h for h in prompt.improvement_history 
            if h.get("type") == "usage_result"
        ]
        # Get last 50 results for history
        usage_history = usage_results[-50:] if len(usage_results) > 50 else usage_results
    
    return {
        "prompt_id": str(prompt.id),
        "prompt_name": prompt.name,
        "version": prompt.version,
        "usage_count": prompt.usage_count,
        "success_rate": prompt.success_rate,
        "avg_execution_time": prompt.avg_execution_time,
        "user_rating": prompt.user_rating,
        "usage_history": usage_history,
        "total_history_entries": len(usage_history)
    }


@router.get("/metrics/comparison")
async def compare_prompt_metrics(
    prompt_name: Optional[str] = None,
    parent_prompt_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Compare metrics across different versions of a prompt"""
    prompt_service = PromptService(db)
    
    if parent_prompt_id:
        # Get all versions of the parent prompt
        versions = prompt_service.get_prompt_versions(parent_prompt_id)
        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt {parent_prompt_id} not found"
            )
    elif prompt_name:
        # Get all versions by name
        all_prompts = prompt_service.list_prompts(name_search=prompt_name, limit=100)
        # Group by name and get versions for each
        versions = []
        for prompt in all_prompts:
            if prompt.name == prompt_name:
                versions.extend(prompt_service.get_prompt_versions(prompt.id))
        # Remove duplicates
        seen_ids = set()
        unique_versions = []
        for v in versions:
            if v.id not in seen_ids:
                seen_ids.add(v.id)
                unique_versions.append(v)
        versions = sorted(unique_versions, key=lambda x: x.version)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either prompt_name or parent_prompt_id must be provided"
        )
    
    # Build comparison data
    comparison = []
    for version in versions:
        usage_history = []
        if version.improvement_history:
            usage_results = [
                h for h in version.improvement_history 
                if h.get("type") == "usage_result"
            ]
            usage_history = usage_results[-20:] if len(usage_results) > 20 else usage_results
        
        comparison.append({
            "prompt_id": str(version.id),
            "version": version.version,
            "status": version.status,
            "usage_count": version.usage_count,
            "success_rate": version.success_rate,
            "avg_execution_time": version.avg_execution_time,
            "user_rating": version.user_rating,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "recent_usage_count": len(usage_history)
        })
    
    return {
        "prompt_name": versions[0].name if versions else None,
        "total_versions": len(comparison),
        "versions": comparison
    }


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


@router.post("/{prompt_id}/assign", response_model=AssignmentResponse)
async def assign_prompt(
    prompt_id: UUID,
    request: AssignmentRequest,
    db: Session = Depends(get_db),
    current_user: Optional["User"] = Depends(get_current_user_optional),
):
    """Assign prompt to model/server/task_type"""
    svc = PromptService(db)
    created_by = current_user.username if current_user else "system"
    try:
        assignment = svc.assign_prompt_to_model_or_server(
            prompt_id=prompt_id,
            model_id=request.model_id,
            server_id=request.server_id,
            task_type=request.task_type,
            component_role=request.component_role,
            stage=request.stage,
            scope=request.scope or "global",
            agent_id=request.agent_id,
            experiment_id=request.experiment_id,
            created_by=created_by,
        )
        return assignment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{prompt_id}/assignments", response_model=List[AssignmentResponse])
async def list_prompt_assignments(
    prompt_id: UUID,
    db: Session = Depends(get_db)
):
    svc = PromptService(db)
    assignments = svc.list_assignments(prompt_id=prompt_id)
    return assignments


@router.get("/assignments")
async def list_assignments(
    model_id: Optional[UUID] = None,
    server_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    svc = PromptService(db)
    assignments = svc.list_assignments(model_id=model_id, server_id=server_id)
    return [a.to_dict() for a in assignments]


@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a prompt assignment by id"""
    from app.models.prompt_assignment import PromptAssignment
    assignment = db.query(PromptAssignment).filter(PromptAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    try:
        db.delete(assignment)
        db.commit()
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
