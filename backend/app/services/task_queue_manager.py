"""
Task Queue Manager for managing task queues and distribution
"""
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.metrics import (queue_size, queue_task_duration_seconds,
                              queue_tasks_processed_total, queue_tasks_total)
from app.models.task_queue import QueueTask, TaskQueue
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class TaskQueueManager:
    """Service for managing task queues"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_queue(
        self,
        name: str,
        description: Optional[str] = None,
        max_concurrent: int = 1,
        priority: int = 5
    ) -> TaskQueue:
        """
        Create a new task queue
        
        Args:
            name: Queue name (must be unique)
            description: Queue description
            max_concurrent: Maximum concurrent tasks
            priority: Queue priority (0-9)
            
        Returns:
            Created TaskQueue
        """
        queue = TaskQueue(
            name=name,
            description=description,
            max_concurrent=max_concurrent,
            priority=priority,
            is_active=True
        )
        
        self.db.add(queue)
        self.db.commit()
        self.db.refresh(queue)
        
        logger.info(f"Created task queue: {name}")
        return queue
    
    def get_queue(self, queue_id: UUID) -> Optional[TaskQueue]:
        """Get a queue by ID"""
        return self.db.query(TaskQueue).filter(TaskQueue.id == queue_id).first()
    
    def get_queue_by_name(self, name: str) -> Optional[TaskQueue]:
        """Get a queue by name"""
        return self.db.query(TaskQueue).filter(TaskQueue.name == name).first()
    
    def list_queues(self, active_only: bool = True) -> List[TaskQueue]:
        """List all queues"""
        query = self.db.query(TaskQueue)
        if active_only:
            query = query.filter(TaskQueue.is_active == True)
        return query.order_by(desc(TaskQueue.priority), TaskQueue.name).all()
    
    def add_task(
        self,
        queue_id: UUID,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 5,
        max_retries: int = 3
    ) -> QueueTask:
        """
        Add a task to a queue
        
        Args:
            queue_id: Queue ID
            task_type: Type of task
            task_data: Task data
            priority: Task priority (0-9)
            max_retries: Maximum retry attempts
            
        Returns:
            Created QueueTask
        """
        queue = self.get_queue(queue_id)
        if not queue:
            raise ValueError(f"Queue {queue_id} not found")
        
        if not queue.is_active:
            raise ValueError(f"Queue {queue.name} is not active")
        
        task = QueueTask(
            queue_id=queue_id,
            task_type=task_type,
            task_data=task_data,
            priority=priority,
            status="pending",
            max_retries=max_retries
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        # Record queue metrics
        queue_tasks_total.labels(
            queue_name=queue.name,
            priority=priority
        ).inc()
        
        # Update queue size gauge
        pending_count = self.db.query(QueueTask).filter(
            QueueTask.queue_id == queue_id,
            QueueTask.status == "pending"
        ).count()
        queue_size.labels(queue_name=queue.name, status="pending").set(pending_count)
        
        logger.debug(
            f"Added task to queue {queue.name}",
            extra={
                "task_id": str(task.id),
                "task_type": task_type,
                "priority": priority,
            }
        )
        
        return task
    
    def get_next_task(
        self,
        queue_id: UUID,
        worker_id: str
    ) -> Optional[QueueTask]:
        """
        Get next task from queue for a worker
        
        Args:
            queue_id: Queue ID
            worker_id: Worker ID
            
        Returns:
            Next QueueTask or None
        """
        queue = self.get_queue(queue_id)
        if not queue or not queue.is_active:
            return None
        
        # Check how many tasks are currently processing
        processing_count = self.db.query(QueueTask).filter(
            and_(
                QueueTask.queue_id == queue_id,
                QueueTask.status == "processing"
            )
        ).count()
        
        if processing_count >= queue.max_concurrent:
            return None
        
        # Get next task: pending or queued, ordered by priority and created_at
        task = self.db.query(QueueTask).filter(
            and_(
                QueueTask.queue_id == queue_id,
                or_(
                    QueueTask.status == "pending",
                    and_(
                        QueueTask.status == "queued",
                        or_(
                            QueueTask.next_retry_at.is_(None),
                            QueueTask.next_retry_at <= datetime.now(timezone.utc)
                        )
                    )
                )
            )
        ).order_by(
            desc(QueueTask.priority),
            QueueTask.created_at
        ).first()
        
        if task:
            # Assign to worker
            task.status = "processing"
            task.assigned_worker = worker_id
            task.started_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(task)
            
            # Update queue size
            pending_count = self.db.query(QueueTask).filter(
                QueueTask.queue_id == queue_id,
                QueueTask.status == "pending"
            ).count()
            processing_count = self.db.query(QueueTask).filter(
                QueueTask.queue_id == queue_id,
                QueueTask.status == "processing"
            ).count()
            queue_size.labels(queue_name=queue.name, status="pending").set(pending_count)
            queue_size.labels(queue_name=queue.name, status="processing").set(processing_count)
            
            logger.debug(
                f"Assigned task to worker {worker_id}",
                extra={
                    "task_id": str(task.id),
                    "queue_id": str(queue_id),
                }
            )
        
        return task
    
    def complete_task(
        self,
        task_id: UUID,
        result_data: Optional[Dict[str, Any]] = None
    ):
        """
        Mark a task as completed
        
        Args:
            task_id: Task ID
            result_data: Result data
        """
        task = self.db.query(QueueTask).filter(QueueTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = "completed"
        task.result_data = result_data
        task.completed_at = datetime.now(timezone.utc)
        task.assigned_worker = None
        
        # Calculate processing duration
        processing_duration = None
        if task.started_at:
            processing_duration = (task.completed_at - task.started_at).total_seconds()
        
        self.db.commit()
        self.db.refresh(task)
        
        # Update metrics
        queue = self.get_queue(task.queue_id)
        if queue:
            queue_tasks_processed_total.labels(
                queue_name=queue.name,
                status="success"
            ).inc()
            
            if processing_duration is not None:
                queue_task_duration_seconds.labels(
                    queue_name=queue.name
                ).observe(processing_duration)
            
            # Update queue size
            pending_count = self.db.query(QueueTask).filter(
                QueueTask.queue_id == task.queue_id,
                QueueTask.status == "pending"
            ).count()
            processing_count = self.db.query(QueueTask).filter(
                QueueTask.queue_id == task.queue_id,
                QueueTask.status == "processing"
            ).count()
            queue_size.labels(queue_name=queue.name, status="pending").set(pending_count)
            queue_size.labels(queue_name=queue.name, status="processing").set(processing_count)
        
        logger.debug(f"Task {task_id} completed")
    
    def fail_task(
        self,
        task_id: UUID,
        error_message: str,
        retry: bool = True
    ):
        """
        Mark a task as failed
        
        Args:
            task_id: Task ID
            error_message: Error message
            retry: Whether to retry the task
        """
        task = self.db.query(QueueTask).filter(QueueTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.retry_count += 1
        
        if retry and task.retry_count <= task.max_retries:
            # Schedule retry with exponential backoff
            delay = self._calculate_retry_delay(task.retry_count)
            task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            task.status = "queued"
            task.error_message = error_message
            task.assigned_worker = None
            
            logger.info(
                f"Task {task_id} failed, scheduled retry {task.retry_count}/{task.max_retries}",
                extra={
                    "task_id": str(task_id),
                    "retry_count": task.retry_count,
                    "next_retry_at": task.next_retry_at.isoformat(),
                }
            )
        else:
            # Move to failed status (Dead Letter Queue)
            task.status = "failed"
            task.error_message = error_message
            task.assigned_worker = None
            task.completed_at = datetime.now(timezone.utc)
            
            # Calculate processing duration
            processing_duration = None
            if task.started_at:
                processing_duration = (task.completed_at - task.started_at).total_seconds()
            
            logger.warning(
                f"Task {task_id} failed permanently after {task.retry_count} retries",
                extra={
                    "task_id": str(task_id),
                    "error": error_message,
                }
            )
        
        self.db.commit()
        self.db.refresh(task)
    
    def cancel_task(self, task_id: UUID):
        """Cancel a task"""
        task = self.db.query(QueueTask).filter(QueueTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = "cancelled"
        task.assigned_worker = None
        task.completed_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(f"Task {task_id} cancelled")
    
    def _calculate_retry_delay(self, retry_count: int, base_delay: int = 10) -> int:
        """
        Calculate retry delay with exponential backoff
        
        Args:
            retry_count: Current retry count
            base_delay: Base delay in seconds
            
        Returns:
            Delay in seconds
        """
        delay = base_delay * (2 ** (retry_count - 1))
        max_delay = 3600  # 1 hour
        return min(delay, max_delay)
    
    def get_queue_stats(self, queue_id: UUID) -> Dict[str, Any]:
        """
        Get statistics for a queue
        
        Args:
            queue_id: Queue ID
            
        Returns:
            Statistics dictionary
        """
        queue = self.get_queue(queue_id)
        if not queue:
            raise ValueError(f"Queue {queue_id} not found")
        
        tasks = self.db.query(QueueTask).filter(QueueTask.queue_id == queue_id).all()
        
        stats = {
            "queue_id": str(queue_id),
            "queue_name": queue.name,
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == "pending"),
            "queued": sum(1 for t in tasks if t.status == "queued"),
            "processing": sum(1 for t in tasks if t.status == "processing"),
            "completed": sum(1 for t in tasks if t.status == "completed"),
            "failed": sum(1 for t in tasks if t.status == "failed"),
            "cancelled": sum(1 for t in tasks if t.status == "cancelled"),
            "max_concurrent": queue.max_concurrent,
        }
        
        return stats
    
    def get_failed_tasks(self, queue_id: Optional[UUID] = None, limit: int = 100) -> List[QueueTask]:
        """
        Get failed tasks (Dead Letter Queue)
        
        Args:
            queue_id: Optional queue ID to filter
            limit: Maximum number of tasks to return
            
        Returns:
            List of failed tasks
        """
        query = self.db.query(QueueTask).filter(QueueTask.status == "failed")
        
        if queue_id:
            query = query.filter(QueueTask.queue_id == queue_id)
        
        return query.order_by(desc(QueueTask.completed_at)).limit(limit).all()

