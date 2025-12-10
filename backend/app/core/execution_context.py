"""
Execution Context - единый контекст выполнения для всех сервисов
"""
from typing import Dict, Any, Optional
from uuid import uuid4
from sqlalchemy.orm import Session

from app.core.tracing import get_current_trace_id
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class ExecutionContext:
    """
    Единый контекст выполнения для всех сервисов
    
    Содержит:
    - db: Session - сессия БД
    - workflow_id: str - ID workflow для отслеживания
    - trace_id: Optional[str] - ID трассировки OpenTelemetry
    - session_id: Optional[str] - ID сессии чата
    - user_id: Optional[str] - ID пользователя
    - metadata: Dict[str, Any] - дополнительные метаданные
    """
    
    def __init__(
        self,
        db: Session,
        workflow_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализация ExecutionContext
        
        Args:
            db: Сессия базы данных
            workflow_id: ID workflow (генерируется автоматически, если не указан)
            trace_id: ID трассировки (получается автоматически, если не указан)
            session_id: ID сессии чата
            user_id: ID пользователя
            metadata: Дополнительные метаданные
        """
        self.db = db
        self.workflow_id = workflow_id or str(uuid4())
        self.trace_id = trace_id or get_current_trace_id()
        self.session_id = session_id
        self.user_id = user_id
        self.metadata = metadata or {}
        
        # PromptManager будет добавлен позже через set_prompt_manager
        self._prompt_manager: Optional[Any] = None
        
        # WorkflowEngine будет добавлен позже (для управления состояниями workflow)
        self._workflow_engine: Optional[Any] = None
    
    @property
    def prompt_manager(self) -> Optional[Any]:
        """Получить PromptManager из контекста"""
        return self._prompt_manager
    
    def set_prompt_manager(self, prompt_manager: Any) -> None:
        """Установить PromptManager в контекст"""
        self._prompt_manager = prompt_manager
    
    @property
    def workflow_engine(self) -> Optional[Any]:
        """Получить WorkflowEngine из контекста"""
        # Lazy initialization: создаем WorkflowEngine при первом обращении, если не установлен
        if self._workflow_engine is None:
            try:
                from app.core.workflow_engine import WorkflowEngine
                self._workflow_engine = WorkflowEngine(self)
            except Exception as e:
                logger.warning(f"Failed to create WorkflowEngine: {e}")
                return None
        return self._workflow_engine
    
    def set_workflow_engine(self, workflow_engine: Any) -> None:
        """Установить WorkflowEngine в контекст"""
        self._workflow_engine = workflow_engine
    
    def update_metadata(self, **kwargs: Any) -> None:
        """Обновить метаданные"""
        self.metadata.update(kwargs)
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Получить значение метаданных по ключу"""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать контекст в словарь для логирования"""
        return {
            "workflow_id": self.workflow_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "metadata_keys": list(self.metadata.keys())
        }
    
    @classmethod
    def from_db_session(
        cls,
        db: Session,
        workflow_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> "ExecutionContext":
        """
        Создать ExecutionContext из db session для обратной совместимости
        
        Args:
            db: Сессия базы данных
            workflow_id: Опциональный ID workflow
            session_id: Опциональный ID сессии
            user_id: Опциональный ID пользователя
            
        Returns:
            ExecutionContext
        """
        return cls(
            db=db,
            workflow_id=workflow_id,
            trace_id=get_current_trace_id(),
            session_id=session_id,
            user_id=user_id
        )
    
    @classmethod
    def from_request(
        cls,
        db: Session,
        request: Any,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> "ExecutionContext":
        """
        Создать ExecutionContext из FastAPI request
        
        Args:
            db: Сессия базы данных
            request: FastAPI Request объект
            session_id: Опциональный ID сессии
            user_id: Опциональный ID пользователя (можно получить из request.state или auth)
            
        Returns:
            ExecutionContext
        """
        # Генерируем workflow_id
        workflow_id = str(uuid4())
        
        # Получаем trace_id
        trace_id = get_current_trace_id()
        
        # Получаем user_id из request, если доступно
        if not user_id and hasattr(request, 'state') and hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        
        return cls(
            db=db,
            workflow_id=workflow_id,
            trace_id=trace_id,
            session_id=session_id,
            user_id=user_id
        )
    
    def __repr__(self) -> str:
        """Строковое представление контекста"""
        return (
            f"ExecutionContext(workflow_id={self.workflow_id[:8]}..., "
            f"trace_id={self.trace_id[:8] if self.trace_id else None}..., "
            f"session_id={self.session_id[:8] if self.session_id else None}...)"
        )
