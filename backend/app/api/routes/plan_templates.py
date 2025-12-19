"""
API routes for plan templates management
"""
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.plan_template import PlanTemplate, TemplateStatus
from app.services.plan_template_service import PlanTemplateService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(prefix="/api/plan-templates", tags=["plan-templates"])


@router.get("/", response_model=List[dict])
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status (active, draft, deprecated)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of templates to return"),
    db: Session = Depends(get_db)
):
    """
    List plan templates with optional filters.
    
    Returns:
        List of plan templates
    """
    try:
        service = PlanTemplateService(db)
        templates = service.list_templates(
            category=category,
            status=status,
            limit=limit
        )
        return [template.to_dict() for template in templates]
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/{template_id}", response_model=dict)
async def get_template(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a plan template by ID.
    
    Args:
        template_id: Template UUID
        
    Returns:
        Template details
    """
    try:
        service = PlanTemplateService(db)
        template = service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        return template.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@router.post("/{template_id}/use", response_model=dict)
async def use_template(
    template_id: UUID,
    task_description: str = Query(..., description="Task description to adapt template to"),
    db: Session = Depends(get_db)
):
    """
    Use a plan template for a task (find matching templates and return adapted steps).
    
    This endpoint searches for matching templates and returns adapted steps
    that can be used to create a plan.
    
    Args:
        template_id: Template UUID (optional, if not provided, will search for best match)
        task_description: Description of the task
        
    Returns:
        Adapted template steps and metadata
    """
    try:
        service = PlanTemplateService(db)
        
        # Get template
        template = service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Update usage count
        service.update_template_usage(template_id)
        
        return {
            "template": template.to_dict(),
            "task_description": task_description,
            "message": "Template retrieved. Use PlanningService to adapt it to your task."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error using template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to use template: {str(e)}")


@router.post("/search", response_model=List[dict])
async def search_templates(
    task_description: str = Query(..., description="Task description to search for"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of templates to return"),
    min_success_rate: float = Query(0.7, ge=0.0, le=1.0, description="Minimum success rate"),
    use_vector_search: bool = Query(True, description="Use vector search if available"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    db: Session = Depends(get_db)
):
    """
    Search for matching plan templates based on task description.
    
    Args:
        task_description: Description of the task
        limit: Maximum number of templates to return
        min_success_rate: Minimum success rate for templates
        use_vector_search: Whether to use vector search
        category: Optional category filter
        tags: Optional tags filter (comma-separated)
        
    Returns:
        List of matching templates, sorted by relevance
    """
    try:
        service = PlanTemplateService(db)
        
        # Parse tags if provided
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
        
        templates = service.find_matching_templates(
            task_description=task_description,
            limit=limit,
            min_success_rate=min_success_rate,
            use_vector_search=use_vector_search,
            category=category,
            tags=tag_list
        )
        
        return [template.to_dict() for template in templates]
    except Exception as e:
        logger.error(f"Error searching templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search templates: {str(e)}")


@router.get("/{template_id}/stats", response_model=dict)
async def get_template_stats(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get statistics for a plan template.
    
    Args:
        template_id: Template UUID
        
    Returns:
        Template statistics (usage count, success rate, etc.)
    """
    try:
        service = PlanTemplateService(db)
        template = service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        return {
            "template_id": str(template.id),
            "template_name": template.name,
            "usage_count": template.usage_count,
            "success_rate": template.success_rate,
            "avg_execution_time": template.avg_execution_time,
            "last_used_at": template.last_used_at.isoformat() if template.last_used_at else None,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "status": template.status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template stats {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get template stats: {str(e)}")

