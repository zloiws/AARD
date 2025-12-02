"""
API routes for task queues
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.task_queue import TaskQueue, QueueTask
from app.services.task_queue_manager import TaskQueueManager
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(prefix="/api/queues", tags=["queues"])


class QueueCreateRequest(BaseModel):
    """Request model for creating a queue"""
    name: str = Field(..., description="Queue name (must be unique)")
    description: Optional[str] = Field(None, description="Queue description")
    max_concurrent: int = Field(1, ge=1, description="Maximum concurrent tasks")
    priority: int = Field(5, ge=0, le=9, description="Queue priority (0-9)")


class QueueResponse(BaseModel):
    """Queue response model"""
    id: str
    name: str
    description: Optional[str]
    max_concurrent: int
    priority: int
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class TaskCreateRequest(BaseModel):
    """Request model for creating a task"""
    task_type: str = Field(..., description="Type of task")
    task_data: dict = Field(..., description="Task data")
    priority: int = Field(5, ge=0, le=9, description="Task priority (0-9)")
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")


class TaskResponse(BaseModel):
    """Task response model"""
    id: str
    queue_id: str
    task_type: str
    status: str
    priority: int
    retry_count: int
    max_retries: int
    assigned_worker: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=QueueResponse)
async def create_queue(
    request: QueueCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new task queue"""
    try:
        manager = TaskQueueManager(db)
        
        # Check if queue with this name already exists
        existing = manager.get_queue_by_name(request.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Queue with name '{request.name}' already exists")
        
        queue = manager.create_queue(
            name=request.name,
            description=request.description,
            max_concurrent=request.max_concurrent,
            priority=request.priority
        )
        
        return QueueResponse(
            id=str(queue.id),
            name=queue.name,
            description=queue.description,
            max_concurrent=queue.max_concurrent,
            priority=queue.priority,
            is_active=queue.is_active,
            created_at=queue.created_at.isoformat(),
            updated_at=queue.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[QueueResponse])
async def list_queues(
    active_only: bool = Query(True, description="Show only active queues"),
    db: Session = Depends(get_db)
):
    """List all task queues"""
    try:
        manager = TaskQueueManager(db)
        queues = manager.list_queues(active_only=active_only)
        
        return [
            QueueResponse(
                id=str(q.id),
                name=q.name,
                description=q.description,
                max_concurrent=q.max_concurrent,
                priority=q.priority,
                is_active=q.is_active,
                created_at=q.created_at.isoformat(),
                updated_at=q.updated_at.isoformat(),
            )
            for q in queues
        ]
        
    except Exception as e:
        logger.error(f"Error listing queues: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{queue_id}", response_model=QueueResponse)
async def get_queue(
    queue_id: str,
    db: Session = Depends(get_db)
):
    """Get a queue by ID"""
    try:
        queue_uuid = UUID(queue_id)
        manager = TaskQueueManager(db)
        queue = manager.get_queue(queue_uuid)
        
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        return QueueResponse(
            id=str(queue.id),
            name=queue.name,
            description=queue.description,
            max_concurrent=queue.max_concurrent,
            priority=queue.priority,
            is_active=queue.is_active,
            created_at=queue.created_at.isoformat(),
            updated_at=queue.updated_at.isoformat(),
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid queue ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{queue_id}/tasks", response_model=TaskResponse)
async def add_task(
    queue_id: str,
    request: TaskCreateRequest,
    db: Session = Depends(get_db)
):
    """Add a task to a queue"""
    try:
        queue_uuid = UUID(queue_id)
        manager = TaskQueueManager(db)
        
        task = manager.add_task(
            queue_id=queue_uuid,
            task_type=request.task_type,
            task_data=request.task_data,
            priority=request.priority,
            max_retries=request.max_retries
        )
        
        return TaskResponse(
            id=str(task.id),
            queue_id=str(task.queue_id),
            task_type=task.task_type,
            status=task.status,
            priority=task.priority,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            assigned_worker=task.assigned_worker,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{queue_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(
    queue_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks"),
    db: Session = Depends(get_db)
):
    """List tasks in a queue"""
    try:
        queue_uuid = UUID(queue_id)
        manager = TaskQueueManager(db)
        
        queue = manager.get_queue(queue_uuid)
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        query = db.query(QueueTask).filter(QueueTask.queue_id == queue_uuid)
        
        if status:
            query = query.filter(QueueTask.status == status.lower())
        
        tasks = query.order_by(
            QueueTask.priority.desc(),
            QueueTask.created_at
        ).limit(limit).all()
        
        return [
            TaskResponse(
                id=str(t.id),
                queue_id=str(t.queue_id),
                task_type=t.task_type,
                status=t.status,
                priority=t.priority,
                retry_count=t.retry_count,
                max_retries=t.max_retries,
                assigned_worker=t.assigned_worker,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in tasks
        ]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid queue ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{queue_id}/tasks/next")
async def get_next_task(
    queue_id: str,
    worker_id: str = Body(..., embed=True, description="Worker ID"),
    db: Session = Depends(get_db)
):
    """Get next task from queue for a worker"""
    try:
        queue_uuid = UUID(queue_id)
        manager = TaskQueueManager(db)
        
        task = manager.get_next_task(queue_uuid, worker_id)
        
        if not task:
            return {"task": None}
        
        return {
            "task": {
                "id": str(task.id),
                "queue_id": str(task.queue_id),
                "task_type": task.task_type,
                "task_data": task.task_data,
                "priority": task.priority,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
            }
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid queue ID format")
    except Exception as e:
        logger.error(f"Error getting next task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    result_data: Optional[dict] = Body(None, embed=True, description="Result data"),
    db: Session = Depends(get_db)
):
    """Mark a task as completed"""
    try:
        task_uuid = UUID(task_id)
        manager = TaskQueueManager(db)
        
        manager.complete_task(task_uuid, result_data)
        
        return {"status": "completed", "task_id": task_id}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error completing task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/fail")
async def fail_task(
    task_id: str,
    error_message: str = Body(..., embed=True, description="Error message"),
    retry: bool = Body(True, embed=True, description="Whether to retry"),
    db: Session = Depends(get_db)
):
    """Mark a task as failed"""
    try:
        task_uuid = UUID(task_id)
        manager = TaskQueueManager(db)
        
        manager.fail_task(task_uuid, error_message, retry)
        
        return {"status": "failed", "task_id": task_id, "will_retry": retry}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error failing task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{queue_id}/stats")
async def get_queue_stats(
    queue_id: str,
    db: Session = Depends(get_db)
):
    """Get statistics for a queue"""
    try:
        queue_uuid = UUID(queue_id)
        manager = TaskQueueManager(db)
        
        stats = manager.get_queue_stats(queue_uuid)
        return stats
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failed-tasks", response_model=List[TaskResponse])
async def get_failed_tasks(
    queue_id: Optional[str] = Query(None, description="Filter by queue ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks"),
    db: Session = Depends(get_db)
):
    """Get failed tasks (Dead Letter Queue)"""
    try:
        manager = TaskQueueManager(db)
        
        queue_uuid = UUID(queue_id) if queue_id else None
        tasks = manager.get_failed_tasks(queue_uuid, limit)
        
        return [
            TaskResponse(
                id=str(t.id),
                queue_id=str(t.queue_id),
                task_type=t.task_type,
                status=t.status,
                priority=t.priority,
                retry_count=t.retry_count,
                max_retries=t.max_retries,
                assigned_worker=t.assigned_worker,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in tasks
        ]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid queue ID format")
    except Exception as e:
        logger.error(f"Error getting failed tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

