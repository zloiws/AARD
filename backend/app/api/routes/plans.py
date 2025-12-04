"""
API routes for task planning
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.database import get_db
from app.models.plan import Plan, PlanStatus
from app.models.task import Task
from app.services.planning_service import PlanningService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/plans", tags=["plans"])


class PlanCreateRequest(BaseModel):
    """Request to create a plan"""
    task_description: str = Field(..., description="Description of the task")
    task_id: Optional[UUID] = Field(None, description="Optional task ID to link plan to")
    context: Optional[dict] = Field(None, description="Additional context")


class PlanResponse(BaseModel):
    """Plan response model"""
    id: UUID
    task_id: UUID
    version: int
    goal: str
    strategy: Optional[dict]
    steps: List[dict]
    alternatives: Optional[List[dict]]
    status: str
    current_step: int
    estimated_duration: Optional[int]
    actual_duration: Optional[int]
    created_at: datetime
    approved_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PlanUpdateRequest(BaseModel):
    """Request to update a plan"""
    goal: Optional[str] = None
    strategy: Optional[dict] = None
    steps: Optional[List[dict]] = None
    alternatives: Optional[List[dict]] = None


class ReplanRequest(BaseModel):
    """Request to replan"""
    reason: str = Field(..., description="Reason for replanning")
    context: Optional[dict] = None


class PlanResponseWithLogs(PlanResponse):
    """Plan response with model logs"""
    model_logs: Optional[List[dict]] = Field(default=None, description="Model interaction logs")


@router.post("/", response_model=PlanResponseWithLogs)
async def create_plan(
    request: PlanCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new plan for a task"""
    try:
        planning_service = PlanningService(db)
        plan = await planning_service.generate_plan(
            task_description=request.task_description,
            task_id=request.task_id,
            context=request.context
        )
        
        # Get model logs from planning service
        model_logs = planning_service.model_logs.copy() if planning_service.model_logs else []
        
        return PlanResponseWithLogs(
            id=plan.id,
            task_id=plan.task_id,
            version=plan.version,
            goal=plan.goal,
            strategy=plan.strategy,
            steps=plan.steps,
            alternatives=plan.alternatives,
            status=plan.status,
            current_step=plan.current_step,
            estimated_duration=plan.estimated_duration,
            actual_duration=plan.actual_duration,
            created_at=plan.created_at,
            approved_at=plan.approved_at,
            model_logs=model_logs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating plan: {str(e)}")


@router.get("/", response_model=List[PlanResponse])
async def list_plans(
    task_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List plans, optionally filtered by task_id or status"""
    query = db.query(Plan)
    
    if task_id:
        query = query.filter(Plan.task_id == task_id)
    
    if status:
        # Use lowercase string to match DB constraint
        query = query.filter(Plan.status == status.lower())
    
    plans = query.order_by(Plan.created_at.desc()).limit(limit).all()
    
    return [
        PlanResponse(
            id=plan.id,
            task_id=plan.task_id,
            version=plan.version,
            goal=plan.goal,
            strategy=plan.strategy,
            steps=plan.steps,
            alternatives=plan.alternatives,
            status=plan.status,
            current_step=plan.current_step,
            estimated_duration=plan.estimated_duration,
            actual_duration=plan.actual_duration,
            created_at=plan.created_at,
            approved_at=plan.approved_at
        )
        for plan in plans
    ]


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Get plan by ID"""
    planning_service = PlanningService(db)
    plan = planning_service.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return PlanResponse(
        id=plan.id,
        task_id=plan.task_id,
        version=plan.version,
        goal=plan.goal,
        strategy=plan.strategy,
        steps=plan.steps,
        alternatives=plan.alternatives,
        status=plan.status,
        current_step=plan.current_step,
        estimated_duration=plan.estimated_duration,
        actual_duration=plan.actual_duration,
        created_at=plan.created_at,
        approved_at=plan.approved_at
    )


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: UUID,
    request: PlanUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update a plan"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if plan.status != "draft":  # Use lowercase string to match DB constraint
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update plan in {plan.status} status"
        )
    
    if request.goal is not None:
        plan.goal = request.goal
    if request.strategy is not None:
        plan.strategy = request.strategy
    if request.steps is not None:
        plan.steps = request.steps
    if request.alternatives is not None:
        plan.alternatives = request.alternatives
    
    db.commit()
    db.refresh(plan)
    
    return PlanResponse(
        id=plan.id,
        task_id=plan.task_id,
        version=plan.version,
        goal=plan.goal,
        strategy=plan.strategy,
        steps=plan.steps,
        alternatives=plan.alternatives,
        status=plan.status,
        current_step=plan.current_step,
        estimated_duration=plan.estimated_duration,
        actual_duration=plan.actual_duration,
        created_at=plan.created_at,
        approved_at=plan.approved_at
    )


@router.post("/{plan_id}/approve", response_model=PlanResponse)
async def approve_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Approve a plan"""
    planning_service = PlanningService(db)
    
    try:
        plan = planning_service.approve_plan(plan_id)
        
        return PlanResponse(
            id=plan.id,
            task_id=plan.task_id,
            version=plan.version,
            goal=plan.goal,
            strategy=plan.strategy,
            steps=plan.steps,
            alternatives=plan.alternatives,
            status=plan.status,
            current_step=plan.current_step,
            estimated_duration=plan.estimated_duration,
            actual_duration=plan.actual_duration,
            created_at=plan.created_at,
            approved_at=plan.approved_at
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{plan_id}/execute", response_model=PlanResponse)
async def execute_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Start plan execution"""
    from app.services.execution_service import ExecutionService
    
    execution_service = ExecutionService(db)
    
    try:
        # Execute plan asynchronously
        plan = await execution_service.execute_plan(plan_id)
        
        return PlanResponse(
            id=plan.id,
            task_id=plan.task_id,
            version=plan.version,
            goal=plan.goal,
            strategy=plan.strategy,
            steps=plan.steps,
            alternatives=plan.alternatives,
            status=plan.status,
            current_step=plan.current_step,
            estimated_duration=plan.estimated_duration,
            actual_duration=plan.actual_duration,
            created_at=plan.created_at,
            approved_at=plan.approved_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{plan_id}/replan", response_model=PlanResponse)
async def replan(
    plan_id: UUID,
    request: ReplanRequest,
    db: Session = Depends(get_db)
):
    """Create a new version of the plan"""
    planning_service = PlanningService(db)
    
    try:
        new_plan = await planning_service.replan(
            plan_id=plan_id,
            reason=request.reason,
            context=request.context
        )
        
        return PlanResponse(
            id=new_plan.id,
            task_id=new_plan.task_id,
            version=new_plan.version,
            goal=new_plan.goal,
            strategy=new_plan.strategy,
            steps=new_plan.steps,
            alternatives=new_plan.alternatives,
            status=new_plan.status,
            current_step=new_plan.current_step,
            estimated_duration=new_plan.estimated_duration,
            actual_duration=new_plan.actual_duration,
            created_at=new_plan.created_at,
            approved_at=new_plan.approved_at
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{plan_id}/status", response_model=dict)
async def get_plan_status(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Get plan execution status"""
    from app.services.execution_service import ExecutionService
    
    execution_service = ExecutionService(db)
    
    try:
        return execution_service.get_execution_status(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{plan_id}/quality")
async def get_plan_quality(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Get plan quality metrics"""
    from app.services.planning_metrics_service import PlanningMetricsService
    from app.services.planning_service import PlanningService
    
    try:
        planning_service = PlanningService(db)
        plan = planning_service.get_plan(plan_id)
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        metrics_service = PlanningMetricsService(db)
        quality_score = metrics_service.calculate_plan_quality_score(plan)
        breakdown = metrics_service.get_plan_quality_breakdown(plan_id)
        
        return {
            "plan_id": str(plan_id),
            "quality_score": quality_score,
            "breakdown": breakdown
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_planning_statistics(
    agent_id: Optional[UUID] = None,
    time_range_days: int = 30,
    db: Session = Depends(get_db)
):
    """Get planning statistics"""
    from app.services.planning_metrics_service import PlanningMetricsService
    
    try:
        metrics_service = PlanningMetricsService(db)
        stats = metrics_service.get_planning_statistics(
            agent_id=agent_id,
            time_range_days=time_range_days
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Interactive Execution endpoints
@router.post("/{plan_id}/pause")
async def pause_execution(
    plan_id: UUID,
    step_id: str,
    question: str,
    db: Session = Depends(get_db)
):
    """Pause plan execution for clarification"""
    from app.services.interactive_execution_service import InteractiveExecutionService
    
    service = InteractiveExecutionService(db)
    
    try:
        result = service.pause_for_clarification(plan_id, step_id, question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plan_id}/apply-correction")
async def apply_correction(
    plan_id: UUID,
    step_id: str,
    correction: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Apply human correction to execution step"""
    from app.services.interactive_execution_service import InteractiveExecutionService
    
    service = InteractiveExecutionService(db)
    
    try:
        result = service.apply_human_correction(plan_id, step_id, correction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plan_id}/resume")
async def resume_execution(
    plan_id: UUID,
    feedback: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Resume plan execution after pause"""
    from app.services.interactive_execution_service import InteractiveExecutionService
    
    service = InteractiveExecutionService(db)
    
    try:
        result = service.resume_execution(plan_id, feedback)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}/tree")
async def get_plan_tree(
    plan_id: UUID,
    include_metadata: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get hierarchical tree structure of plan steps
    
    Args:
        plan_id: Plan ID
        include_metadata: Whether to include full step metadata in tree nodes
        db: Database session
        
    Returns:
        Dictionary with tree structure containing nodes, root_nodes, total_steps, total_levels
    """
    from app.services.plan_tree_service import PlanTreeService
    
    planning_service = PlanningService(db)
    plan = planning_service.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    # Get steps from plan
    steps = plan.steps
    if isinstance(steps, str):
        import json
        try:
            steps = json.loads(steps)
        except json.JSONDecodeError:
            steps = []
    
    if not steps:
        return {
            "nodes": [],
            "root_nodes": [],
            "total_steps": 0,
            "total_levels": 0,
            "has_hierarchy": False,
            "plan_id": str(plan_id),
            "plan_version": plan.version
        }
    
    # Build tree structure
    tree_service = PlanTreeService()
    tree = tree_service.build_tree(steps, include_metadata=include_metadata)
    
    # Add plan metadata
    tree["plan_id"] = str(plan_id)
    tree["plan_version"] = plan.version
    tree["plan_status"] = plan.status
    tree["plan_goal"] = plan.goal
    
    return tree


@router.get("/{plan_id}/execution-state")
async def get_execution_state(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Get current interactive execution state"""
    from app.services.interactive_execution_service import InteractiveExecutionService
    
    service = InteractiveExecutionService(db)
    
    try:
        state = service.get_execution_state(plan_id)
        if not state:
            raise HTTPException(status_code=404, detail="Execution state not found")
        return state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

