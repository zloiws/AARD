"""
Workflow tracker for real-time execution monitoring
Tracks current request execution process from user input to result
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum
import threading
from collections import deque

from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class WorkflowStage(str, Enum):
    """Workflow execution stages"""
    USER_REQUEST = "user_request"
    REQUEST_PARSING = "request_parsing"
    ACTION_DETERMINATION = "action_determination"
    EXECUTION = "execution"
    RESULT = "result"
    ERROR = "error"


class WorkflowEvent:
    """Single workflow event"""
    def __init__(
        self,
        stage: WorkflowStage,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.stage = stage
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stage": self.stage.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class WorkflowTracker:
    """Global workflow tracker for current execution"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(WorkflowTracker, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._lock = threading.Lock()
        self._current_workflow_id: Optional[str] = None
        self._events: deque = deque(maxlen=1000)  # Keep last 1000 events
        self._workflows: Dict[str, List[WorkflowEvent]] = {}
        self._initialized = True
    
    def start_workflow(self, workflow_id: str, user_request: str, username: str = "user", interaction_type: str = "chat") -> None:
        """Start tracking a new workflow
        
        Args:
            workflow_id: Unique workflow identifier
            user_request: User request or task description
            username: Username or source of request
            interaction_type: Type of interaction (chat, planning, test, etc.)
        """
        with self._lock:
            self._current_workflow_id = workflow_id
            
            # Format message based on interaction type
            type_labels = {
                "chat": "Основной чат",
                "planning": "Планирование задачи",
                "test": "Тест",
                "execution": "Выполнение",
                "system": "Система"
            }
            type_label = type_labels.get(interaction_type, interaction_type.capitalize())
            
            event = WorkflowEvent(
                stage=WorkflowStage.USER_REQUEST,
                message=f'{type_label}, запрос пользователя @{username}: \"{user_request}\"',
                details={"user_request": user_request, "username": username, "interaction_type": interaction_type}
            )
            self._events.append(event)
            if workflow_id not in self._workflows:
                self._workflows[workflow_id] = []
            self._workflows[workflow_id].append(event)
            logger.info(f"Workflow {workflow_id} started", extra={"user_request": user_request, "type": interaction_type})
    
    def add_event(
        self,
        stage: WorkflowStage,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> None:
        """Add event to current workflow"""
        with self._lock:
            wf_id = workflow_id or self._current_workflow_id
            if not wf_id:
                # No active workflow, create a temporary one
                wf_id = f"temp_{datetime.now(timezone.utc).timestamp()}"
                self._current_workflow_id = wf_id
                if wf_id not in self._workflows:
                    self._workflows[wf_id] = []
            
            event = WorkflowEvent(stage=stage, message=message, details=details or {})
            self._events.append(event)
            
            if wf_id not in self._workflows:
                self._workflows[wf_id] = []
            self._workflows[wf_id].append(event)
            
            logger.debug(f"Workflow event: {stage.value} - {message}")
    
    def get_current_workflow(self) -> Optional[List[Dict[str, Any]]]:
        """Get current workflow events"""
        with self._lock:
            if not self._current_workflow_id:
                # Return recent events if no active workflow
                return [event.to_dict() for event in list(self._events)[-20:]] if self._events else None
            
            events = self._workflows.get(self._current_workflow_id, [])
            return [event.to_dict() for event in events] if events else None
    
    def get_all_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all recent events (last N)"""
        with self._lock:
            return [event.to_dict() for event in list(self._events)[-limit:]]
    
    def finish_workflow(self, result: Optional[str] = None, error: Optional[str] = None) -> None:
        """Finish current workflow"""
        with self._lock:
            if not self._current_workflow_id:
                return
            
            if error:
                event = WorkflowEvent(
                    stage=WorkflowStage.ERROR,
                    message=f"Ошибка выполнения: {error}",
                    details={"error": error}
                )
            else:
                event = WorkflowEvent(
                    stage=WorkflowStage.RESULT,
                    message=f"Результат: {result or 'Выполнение завершено'}",
                    details={"result": result}
                )
            
            self._events.append(event)
            if self._current_workflow_id in self._workflows:
                self._workflows[self._current_workflow_id].append(event)
            
            logger.info(f"Workflow {self._current_workflow_id} finished")
            
            # Clear current workflow after a delay (to allow viewing results)
            # For now, we keep it until new workflow starts
    
    def clear_current(self) -> None:
        """Clear current workflow (start fresh)"""
        with self._lock:
            self._current_workflow_id = None


# Global instance
_workflow_tracker: Optional[WorkflowTracker] = None


def get_workflow_tracker() -> WorkflowTracker:
    """Get global workflow tracker instance"""
    global _workflow_tracker
    if _workflow_tracker is None:
        _workflow_tracker = WorkflowTracker()
    return _workflow_tracker

