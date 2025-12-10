"""
WorkflowEngine - расширение WorkflowTracker для управления состояниями workflow
Управляет жизненным циклом workflow, переходами между состояниями и обработкой событий
"""
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.workflow_tracker import WorkflowTracker, WorkflowStage, WorkflowEvent
from app.core.execution_context import ExecutionContext
from app.core.logging_config import LoggingConfig
from app.models.workflow_event import WorkflowEvent as DBWorkflowEvent, EventStatus, EventType, EventSource
from app.services.workflow_event_service import WorkflowEventService

logger = LoggingConfig.get_logger(__name__)


class WorkflowState(str, Enum):
    """Состояния workflow"""
    INITIALIZED = "initialized"
    PARSING = "parsing"
    PLANNING = "planning"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowTransition:
    """Переход между состояниями workflow"""
    def __init__(
        self,
        from_state: WorkflowState,
        to_state: WorkflowState,
        condition: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.condition = condition
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать переход в словарь"""
        return {
            "from_state": self.from_state.value if self.from_state else None,
            "to_state": self.to_state.value,
            "condition": self.condition,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class WorkflowEngine:
    """
    Расширение WorkflowTracker для управления состояниями workflow
    
    Функционал:
    - Управление состояниями workflow
    - Валидация переходов между состояниями
    - Обработка событий и обновление состояний
    - Интеграция с БД для персистентности
    - Поддержка паузы, возобновления, отмены
    """
    
    def __init__(self, context: ExecutionContext):
        """
        Инициализация WorkflowEngine
        
        Args:
            context: ExecutionContext с workflow_id и db session
        """
        self.context = context
        self.db = context.db
        self.workflow_id = context.workflow_id
        self.tracker = WorkflowTracker()
        try:
            self.event_service = WorkflowEventService(self.db)
        except Exception as e:
            logger.warning(f"Could not initialize WorkflowEventService: {e}")
            self.event_service = None
        
        # Текущее состояние workflow
        self._current_state: Optional[WorkflowState] = None
        
        # История переходов
        self._transitions: List[WorkflowTransition] = []
        
        # Разрешенные переходы
        self._allowed_transitions: Dict[WorkflowState, Set[WorkflowState]] = {
            WorkflowState.INITIALIZED: {WorkflowState.PARSING, WorkflowState.CANCELLED},
            WorkflowState.PARSING: {WorkflowState.PLANNING, WorkflowState.FAILED, WorkflowState.CANCELLED},
            WorkflowState.PLANNING: {
                WorkflowState.APPROVAL_PENDING,
                WorkflowState.APPROVED,
                WorkflowState.EXECUTING,
                WorkflowState.FAILED,
                WorkflowState.CANCELLED
            },
            WorkflowState.APPROVAL_PENDING: {
                WorkflowState.APPROVED,
                WorkflowState.CANCELLED,
                WorkflowState.FAILED
            },
            WorkflowState.APPROVED: {
                WorkflowState.EXECUTING,
                WorkflowState.CANCELLED
            },
            WorkflowState.EXECUTING: {
                WorkflowState.PAUSED,
                WorkflowState.COMPLETED,
                WorkflowState.FAILED,
                WorkflowState.RETRYING,
                WorkflowState.CANCELLED
            },
            WorkflowState.PAUSED: {
                WorkflowState.EXECUTING,
                WorkflowState.CANCELLED,
                WorkflowState.FAILED
            },
            WorkflowState.RETRYING: {
                WorkflowState.EXECUTING,
                WorkflowState.FAILED,
                WorkflowState.CANCELLED
            },
            WorkflowState.FAILED: {
                WorkflowState.RETRYING,
                WorkflowState.CANCELLED
            },
            WorkflowState.COMPLETED: set(),  # Финальное состояние
            WorkflowState.CANCELLED: set()   # Финальное состояние
        }
    
    def initialize(self, user_request: str, username: str = "user", interaction_type: str = "chat") -> None:
        """
        Инициализировать новый workflow
        
        Args:
            user_request: Запрос пользователя
            username: Имя пользователя
            interaction_type: Тип взаимодействия
        """
        # Инициализировать в трекере
        self.tracker.start_workflow(
            workflow_id=self.workflow_id,
            user_request=user_request,
            username=username,
            interaction_type=interaction_type
        )
        
        # Установить начальное состояние
        self._current_state = WorkflowState.INITIALIZED
        
        # Сохранить событие в БД
        self._save_state_change(
            from_state=None,
            to_state=WorkflowState.INITIALIZED,
            message=f"Workflow initialized: {user_request[:100]}",
            metadata={"user_request": user_request, "username": username, "interaction_type": interaction_type}
        )
        
        logger.info(
            f"Workflow {self.workflow_id} initialized",
            extra={"workflow_id": self.workflow_id, "state": WorkflowState.INITIALIZED.value}
        )
    
    def transition_to(
        self,
        new_state: WorkflowState,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """
        Перейти в новое состояние
        
        Args:
            new_state: Новое состояние
            message: Сообщение о переходе
            metadata: Дополнительные метаданные
            force: Принудительный переход (игнорировать валидацию)
            
        Returns:
            True если переход выполнен, False если не разрешен
        """
        if self._current_state is None:
            logger.warning(f"Cannot transition: workflow not initialized")
            return False
        
        # Проверка разрешенности перехода
        if not force:
            allowed = self._allowed_transitions.get(self._current_state, set())
            if new_state not in allowed:
                logger.warning(
                    f"Transition not allowed: {self._current_state.value} -> {new_state.value}",
                    extra={
                        "workflow_id": self.workflow_id,
                        "from_state": self._current_state.value,
                        "to_state": new_state.value
                    }
                )
                return False
        
        # Выполнить переход
        old_state = self._current_state
        self._current_state = new_state
        
        # Записать переход
        transition = WorkflowTransition(
            from_state=old_state,
            to_state=new_state,
            condition=message,
            metadata=metadata or {}
        )
        self._transitions.append(transition)
        
        # Сохранить в трекере
        stage = self._state_to_stage(new_state)
        self.tracker.add_event(
            stage=stage,
            message=message,
            details=metadata or {}
        )
        
        # Сохранить в БД
        self._save_state_change(
            from_state=old_state,
            to_state=new_state,
            message=message,
            metadata=metadata
        )
        
        logger.info(
            f"Workflow {self.workflow_id} transitioned: {old_state.value} -> {new_state.value}",
            extra={
                "workflow_id": self.workflow_id,
                "from_state": old_state.value,
                "to_state": new_state.value,
                "message": message
            }
        )
        
        return True
    
    def get_current_state(self) -> Optional[WorkflowState]:
        """Получить текущее состояние workflow"""
        return self._current_state
    
    def can_transition_to(self, new_state: WorkflowState) -> bool:
        """Проверить, возможен ли переход в новое состояние"""
        if self._current_state is None:
            return False
        allowed = self._allowed_transitions.get(self._current_state, set())
        return new_state in allowed
    
    def pause(self, reason: str = "Paused by system") -> bool:
        """Приостановить выполнение workflow"""
        if self._current_state != WorkflowState.EXECUTING:
            logger.warning(f"Cannot pause: workflow is not executing (current: {self._current_state})")
            return False
        
        return self.transition_to(
            WorkflowState.PAUSED,
            f"Workflow paused: {reason}",
            metadata={"reason": reason}
        )
    
    def resume(self) -> bool:
        """Возобновить выполнение workflow"""
        if self._current_state != WorkflowState.PAUSED:
            logger.warning(f"Cannot resume: workflow is not paused (current: {self._current_state})")
            return False
        
        return self.transition_to(
            WorkflowState.EXECUTING,
            "Workflow resumed",
            metadata={"resumed_at": datetime.now(timezone.utc).isoformat()}
        )
    
    def cancel(self, reason: str = "Cancelled by user") -> bool:
        """Отменить workflow"""
        if self._current_state in [WorkflowState.COMPLETED, WorkflowState.CANCELLED]:
            logger.warning(f"Cannot cancel: workflow already in final state (current: {self._current_state})")
            return False
        
        return self.transition_to(
            WorkflowState.CANCELLED,
            f"Workflow cancelled: {reason}",
            metadata={"reason": reason, "cancelled_at": datetime.now(timezone.utc).isoformat()},
            force=True  # Отмена возможна из любого состояния
        )
    
    def mark_completed(self, result: Optional[str] = None) -> bool:
        """Отметить workflow как завершенный"""
        if self._current_state not in [WorkflowState.EXECUTING, WorkflowState.APPROVED]:
            logger.warning(f"Cannot complete: workflow is not in executable state (current: {self._current_state})")
            return False
        
        return self.transition_to(
            WorkflowState.COMPLETED,
            "Workflow completed successfully",
            metadata={"result": result, "completed_at": datetime.now(timezone.utc).isoformat()}
        )
    
    def mark_failed(self, error: str, error_details: Optional[Dict[str, Any]] = None) -> bool:
        """Отметить workflow как проваленный"""
        return self.transition_to(
            WorkflowState.FAILED,
            f"Workflow failed: {error}",
            metadata={
                "error": error,
                "error_details": error_details or {},
                "failed_at": datetime.now(timezone.utc).isoformat()
            },
            force=True  # Ошибка может произойти в любом состоянии
        )
    
    def retry(self, reason: str = "Retrying after failure") -> bool:
        """Повторить выполнение после ошибки"""
        if self._current_state != WorkflowState.FAILED:
            logger.warning(f"Cannot retry: workflow is not failed (current: {self._current_state})")
            return False
        
        return self.transition_to(
            WorkflowState.RETRYING,
            f"Workflow retrying: {reason}",
            metadata={"reason": reason, "retry_started_at": datetime.now(timezone.utc).isoformat()}
        )
    
    def get_transition_history(self) -> List[WorkflowTransition]:
        """Получить историю переходов"""
        return self._transitions.copy()
    
    def get_state_info(self) -> Dict[str, Any]:
        """Получить информацию о текущем состоянии"""
        return {
            "workflow_id": self.workflow_id,
            "current_state": self._current_state.value if self._current_state else None,
            "transitions_count": len(self._transitions),
            "last_transition": self._transitions[-1].to_dict() if self._transitions else None,
            "allowed_next_states": [
                state.value for state in self._allowed_transitions.get(self._current_state, set())
            ] if self._current_state else []
        }
    
    def _state_to_stage(self, state: WorkflowState) -> WorkflowStage:
        """Преобразовать WorkflowState в WorkflowStage для трекера"""
        mapping = {
            WorkflowState.INITIALIZED: WorkflowStage.USER_REQUEST,
            WorkflowState.PARSING: WorkflowStage.REQUEST_PARSING,
            WorkflowState.PLANNING: WorkflowStage.ACTION_DETERMINATION,
            WorkflowState.APPROVAL_PENDING: WorkflowStage.ACTION_DETERMINATION,
            WorkflowState.APPROVED: WorkflowStage.ACTION_DETERMINATION,
            WorkflowState.EXECUTING: WorkflowStage.EXECUTION,
            WorkflowState.PAUSED: WorkflowStage.EXECUTION,
            WorkflowState.RETRYING: WorkflowStage.EXECUTION,
            WorkflowState.COMPLETED: WorkflowStage.RESULT,
            WorkflowState.FAILED: WorkflowStage.ERROR,
            WorkflowState.CANCELLED: WorkflowStage.ERROR
        }
        return mapping.get(state, WorkflowStage.EXECUTION)
    
    def _save_state_change(
        self,
        from_state: Optional[WorkflowState],
        to_state: WorkflowState,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Сохранить изменение состояния в БД"""
        if not self.event_service:
            return  # Пропускаем сохранение если сервис недоступен
        
        try:
            # Преобразуем WorkflowStage в WorkflowStage из модели
            from app.models.workflow_event import WorkflowStage as ModelWorkflowStage
            model_stage = ModelWorkflowStage(self._state_to_stage(to_state).value)
            
            self.event_service.save_event(
                workflow_id=self.workflow_id,
                event_type=EventType.STATE_CHANGE,
                event_source=EventSource.SYSTEM,
                stage=model_stage,
                message=message,
                status=EventStatus.SUCCESS,
                metadata={
                    "from_state": from_state.value if from_state else None,
                    "to_state": to_state.value,
                    **(metadata or {})
                },
                trace_id=self.context.trace_id
            )
        except Exception as e:
            logger.warning(f"Failed to save state change to DB: {e}", exc_info=True)
    
    @classmethod
    def from_context(cls, context: ExecutionContext) -> "WorkflowEngine":
        """
        Создать WorkflowEngine из ExecutionContext
        
        Args:
            context: ExecutionContext с workflow_id
            
        Returns:
            WorkflowEngine instance
        """
        return cls(context)
