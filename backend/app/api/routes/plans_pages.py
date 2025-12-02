"""
Page routes for plans web interface
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.templates import templates
from app.core.database import get_db
from app.models.plan import Plan
from app.services.planning_service import PlanningService
from sqlalchemy.orm import Session

router = APIRouter(tags=["plans_pages"])


@router.get("/plans/create", response_class=HTMLResponse)
async def plan_create_form(request: Request):
    """Plan creation form - MUST be before /plans/{plan_id} to avoid UUID parsing error"""
    return templates.TemplateResponse(
        "plans/create.html",
        {
            "request": request
        }
    )


@router.get("/plans", response_class=HTMLResponse)
async def plans_list(request: Request, db: Session = Depends(get_db)):
    """List all plans"""
    # Get all plans
    plans = db.query(Plan).order_by(Plan.created_at.desc()).limit(100).all()
    
    # Group by status
    plans_by_status = {
        "draft": [],
        "approved": [],
        "executing": [],
        "completed": [],
        "failed": [],
        "cancelled": []
    }
    
    for plan in plans:
        status = plan.status
        if status in plans_by_status:
            # Calculate total steps from JSON
            total_steps = 0
            if plan.steps:
                if isinstance(plan.steps, list):
                    total_steps = len(plan.steps)
                elif isinstance(plan.steps, str):
                    import json
                    try:
                        steps_list = json.loads(plan.steps)
                        total_steps = len(steps_list) if isinstance(steps_list, list) else 0
                    except:
                        total_steps = 0
            
            plans_by_status[status].append({
                "id": str(plan.id),
                "goal": plan.goal[:100] + "..." if len(plan.goal) > 100 else plan.goal,
                "status": plan.status,
                "version": plan.version,
                "current_step": plan.current_step,
                "total_steps": total_steps,
                "created_at": plan.created_at,
                "approved_at": plan.approved_at,
                "steps": plan.steps  # Pass steps for template
            })
    
    return templates.TemplateResponse(
        "plans/list.html",
        {
            "request": request,
            "plans": plans,
            "plans_by_status": plans_by_status,
            "total_plans": len(plans)
        }
    )


@router.get("/plans/{plan_id}", response_class=HTMLResponse)
async def plan_detail(
    request: Request,
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Plan details page"""
    planning_service = PlanningService(db)
    plan = planning_service.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Calculate progress
    total_steps = 0
    if plan.steps:
        if isinstance(plan.steps, list):
            total_steps = len(plan.steps)
        elif isinstance(plan.steps, str):
            import json
            try:
                steps_list = json.loads(plan.steps)
                total_steps = len(steps_list) if isinstance(steps_list, list) else 0
            except:
                total_steps = 0
    
    progress = (plan.current_step / total_steps * 100) if total_steps > 0 else 0
    
    # Parse steps if it's a JSON string
    steps = plan.steps
    if isinstance(steps, str):
        import json
        try:
            steps = json.loads(steps)
        except:
            steps = []
    
    # Parse strategy if it's a JSON string
    strategy = plan.strategy
    if isinstance(strategy, str):
        import json
        try:
            strategy = json.loads(strategy)
        except:
            strategy = {}
    
    # Parse alternatives if it's a JSON string
    alternatives = plan.alternatives
    if isinstance(alternatives, str):
        import json
        try:
            alternatives = json.loads(alternatives)
        except:
            alternatives = []
    
    return templates.TemplateResponse(
        "plans/detail.html",
        {
            "request": request,
            "plan": plan,
            "steps": steps,  # Pass parsed steps
            "strategy": strategy,  # Pass parsed strategy
            "alternatives": alternatives,  # Pass parsed alternatives
            "total_steps": total_steps,
            "progress": progress,
            "can_approve": plan.status == "draft",
            "can_execute": plan.status == "approved",
            "can_update": plan.status == "draft"
        }
    )



