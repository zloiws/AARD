"""
Task Lifecycle Manager - управление жизненным циклом задач
Реализует ToDo-список как Workflow Engine с четкими статусами и переходами
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.execution_context import ExecutionContext
from app.core.logging_config import LoggingConfig
from app.models.task import Task, TaskStatus
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class TaskRole(str, Enum):
    """Роли в жизненном цикле задачи"""
    PLANNER = "planner"  # Создает план
    VALIDATOR = "validator"  # Проверяет план
    HUMAN = "human"  # Утверждает план
    EXECUTOR = "executor"  # Выполняет план
    SYSTEM = "system"  # Системные действия


class TaskLifecycleManager:
    """
    Менеджер жизненного цикла задач
    
    Управляет переходами между статусами согласно workflow:
    DRAFT → PENDING_APPROVAL → APPROVED → IN_PROGRESS → COMPLETED/FAILED
    
    С учетом ролей и прав доступа
    """
    
    # Разрешенные переходы между статусами
    ALLOWED_TRANSITIONS: Dict[TaskStatus, List[TaskStatus]] = {
        TaskStatus.DRAFT: [TaskStatus.PENDING_APPROVAL, TaskStatus.CANCELLED],
        TaskStatus.PENDING: [TaskStatus.PLANNING, TaskStatus.CANCELLED],
        TaskStatus.PLANNING: [TaskStatus.PENDING_APPROVAL, TaskStatus.FAILED, TaskStatus.CANCELLED],
        TaskStatus.PENDING_APPROVAL: [TaskStatus.APPROVED, TaskStatus.CANCELLED, TaskStatus.DRAFT],
        TaskStatus.WAITING_APPROVAL: [TaskStatus.APPROVED, TaskStatus.CANCELLED],  # Legacy
        TaskStatus.APPROVED: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
        TaskStatus.IN_PROGRESS: [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.PAUSED,
            TaskStatus.ON_HOLD,
            TaskStatus.CANCELLED
        ],
        TaskStatus.EXECUTING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],  # Legacy
        TaskStatus.PAUSED: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
        TaskStatus.ON_HOLD: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
        TaskStatus.COMPLETED: [],  # Финальное состояние
        TaskStatus.FAILED: [TaskStatus.DRAFT, TaskStatus.CANCELLED],  # Можно перепланировать
        TaskStatus.CANCELLED: []  # Финальное состояние
    }
    
    # Роли, которые могут выполнять переходы
    ROLE_PERMISSIONS: Dict[TaskStatus, List[TaskRole]] = {
        TaskStatus.DRAFT: [TaskRole.PLANNER, TaskRole.SYSTEM],
        TaskStatus.PENDING_APPROVAL: [TaskRole.VALIDATOR, TaskRole.HUMAN, TaskRole.SYSTEM],
        TaskStatus.APPROVED: [TaskRole.HUMAN, TaskRole.SYSTEM],
        TaskStatus.IN_PROGRESS: [TaskRole.EXECUTOR, TaskRole.SYSTEM],
        TaskStatus.PAUSED: [TaskRole.HUMAN, TaskRole.EXECUTOR, TaskRole.SYSTEM],
        TaskStatus.ON_HOLD: [TaskRole.HUMAN, TaskRole.EXECUTOR, TaskRole.SYSTEM],
        TaskStatus.COMPLETED: [TaskRole.EXECUTOR, TaskRole.SYSTEM],
        TaskStatus.FAILED: [TaskRole.EXECUTOR, TaskRole.SYSTEM, TaskRole.PLANNER],  # Planner может перепланировать
        TaskStatus.CANCELLED: [TaskRole.HUMAN, TaskRole.SYSTEM]
    }
    
    def __init__(self, db: Session):
        """
        Initialize Task Lifecycle Manager
        
        Args:
            db: Database session
        """
        self.db = db
    
    def transition(
        self,
        task: Task,
        new_status: TaskStatus,
        role: TaskRole,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Выполнить переход задачи в новый статус
        
        Args:
            task: Задача для перехода
            new_status: Новый статус
            role: Роль, выполняющая переход
            reason: Причина перехода
            metadata: Дополнительные метаданные
            
        Returns:
            True если переход выполнен, False если не разрешен
        """
        old_status = task.status
        
        # Проверить, разрешен ли переход
        if not self.can_transition(task, new_status, role):
            logger.warning(
                f"Transition not allowed: {old_status.value} -> {new_status.value} by {role.value}",
                extra={
                    "task_id": str(task.id),
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "role": role.value
                }
            )
            return False
        
        # Выполнить переход
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)
        
        # Обновить контекст задачи (Digital Twin)
        context = task.get_context()
        if "status_history" not in context:
            context["status_history"] = []
        
        context["status_history"].append({
            "from_status": old_status.value,
            "to_status": new_status.value,
            "role": role.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        })
        
        # Обновить роль в зависимости от статуса
        if new_status == TaskStatus.APPROVED:
            task.approved_by_role = role.value
        elif new_status == TaskStatus.IN_PROGRESS:
            task.created_by_role = role.value
        
        task.update_context(context, merge=False)
        
        self.db.commit()
        
        logger.info(
            f"Task {task.id} transitioned: {old_status.value} -> {new_status.value}",
            extra={
                "task_id": str(task.id),
                "old_status": old_status.value,
                "new_status": new_status.value,
                "role": role.value,
                "reason": reason
            }
        )
        
        return True
    
    def can_transition(
        self,
        task: Task,
        new_status: TaskStatus,
        role: TaskRole
    ) -> bool:
        """
        Проверить, возможен ли переход
        
        Args:
            task: Задача
            new_status: Новый статус
            role: Роль, выполняющая переход
            
        Returns:
            True если переход разрешен
        """
        current_status = task.status
        
        # Проверить, разрешен ли переход по статусам
        allowed_statuses = self.ALLOWED_TRANSITIONS.get(current_status, [])
        if new_status not in allowed_statuses:
            return False
        
        # Проверить права роли
        allowed_roles = self.ROLE_PERMISSIONS.get(new_status, [TaskRole.SYSTEM])
        if role not in allowed_roles and TaskRole.SYSTEM not in allowed_roles:
            return False
        
        return True
    
    def get_allowed_transitions(
        self,
        task: Task,
        role: TaskRole
    ) -> List[TaskStatus]:
        """
        Получить список разрешенных переходов для задачи и роли
        
        Args:
            task: Задача
            role: Роль
            
        Returns:
            Список разрешенных статусов
        """
        current_status = task.status
        allowed_statuses = self.ALLOWED_TRANSITIONS.get(current_status, [])
        
        # Фильтровать по правам роли
        result = []
        for status in allowed_statuses:
            allowed_roles = self.ROLE_PERMISSIONS.get(status, [TaskRole.SYSTEM])
            if role in allowed_roles or TaskRole.SYSTEM in allowed_roles:
                result.append(status)
        
        return result
    
    def get_status_info(self, status: TaskStatus) -> Dict[str, Any]:
        """
        Получить информацию о статусе
        
        Args:
            status: Статус задачи
            
        Returns:
            Информация о статусе
        """
        return {
            "status": status.value,
            "allowed_transitions": [
                s.value for s in self.ALLOWED_TRANSITIONS.get(status, [])
            ],
            "allowed_roles": [
                r.value for r in self.ROLE_PERMISSIONS.get(status, [TaskRole.SYSTEM])
            ]
        }

