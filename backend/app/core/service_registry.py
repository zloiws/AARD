"""
Service Registry - централизованный реестр сервисов
"""
from typing import Type, TypeVar, Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
import threading

from app.core.execution_context import ExecutionContext
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

T = TypeVar('T')


class ServiceRegistry:
    """
    Singleton реестр сервисов с lazy initialization
    
    Управляет созданием и кэшированием экземпляров сервисов,
    обеспечивая единообразный доступ через ExecutionContext.
    """
    
    _instance: Optional['ServiceRegistry'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ServiceRegistry, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Инициализация реестра"""
        if self._initialized:
            return
        
        self._services: Dict[str, Any] = {}
        self._service_factories: Dict[Type, Callable] = {}
        self._lock = threading.Lock()
        self._initialized = True
    
    def register_factory(
        self,
        service_class: Type[T],
        factory: Callable[[ExecutionContext], T]
    ) -> None:
        """
        Зарегистрировать фабрику для создания сервиса
        
        Args:
            service_class: Класс сервиса
            factory: Функция-фабрика, принимающая ExecutionContext и возвращающая экземпляр сервиса
        """
        with self._lock:
            self._service_factories[service_class] = factory
            logger.debug(f"Registered factory for {service_class.__name__}")
    
    def get_service(
        self,
        service_class: Type[T],
        context: ExecutionContext
    ) -> T:
        """
        Получить экземпляр сервиса для данного контекста
        
        Args:
            service_class: Класс сервиса
            context: ExecutionContext
            
        Returns:
            Экземпляр сервиса
        """
        # Создаем ключ на основе класса и workflow_id
        # Это позволяет иметь разные экземпляры для разных workflow
        service_key = f"{service_class.__name__}_{context.workflow_id}"
        
        with self._lock:
            # Проверяем, есть ли уже экземпляр для этого workflow
            if service_key in self._services:
                return self._services[service_key]
            
            # Создаем новый экземпляр
            if service_class in self._service_factories:
                # Используем зарегистрированную фабрику
                service = self._service_factories[service_class](context)
            else:
                # Пытаемся создать через стандартный способ
                # Сначала пробуем с ExecutionContext
                try:
                    service = service_class(context)
                except TypeError:
                    # Если не поддерживает ExecutionContext, пробуем с db
                    # Это для обратной совместимости
                    try:
                        service = service_class(context.db)
                    except Exception as e:
                        logger.error(f"Failed to create {service_class.__name__}: {e}", exc_info=True)
                        raise
            
            # Сохраняем в кэш
            self._services[service_key] = service
            return service
    
    def get_service_by_db(
        self,
        service_class: Type[T],
        db: Session
    ) -> T:
        """
        Получить экземпляр сервиса используя db Session (для обратной совместимости)
        
        Args:
            service_class: Класс сервиса
            db: Database Session
            
        Returns:
            Экземпляр сервиса
        """
        # Создаем минимальный контекст из db
        context = ExecutionContext.from_db_session(db)
        return self.get_service(service_class, context)
    
    def _create_service_fallback(
        self,
        service_class: Type[T],
        context: ExecutionContext
    ) -> T:
        """
        Создать сервис через fallback механизм (внутренний метод)
        
        Args:
            service_class: Класс сервиса
            context: ExecutionContext
            
        Returns:
            Экземпляр сервиса
        """
        # Пытаемся создать через стандартный способ
        # Сначала пробуем с ExecutionContext
        try:
            service = service_class(context)
        except TypeError:
            # Если не поддерживает ExecutionContext, пробуем с db
            # Это для обратной совместимости
            try:
                service = service_class(context.db)
            except Exception as e:
                        logger.error(
                            f"Failed to create service {service_class.__name__}: {e}",
                            exc_info=True
                        )
                        raise
            
            # Сохраняем в кэше
            self._services[service_key] = service
            logger.debug(f"Created and cached service {service_class.__name__} for workflow {context.workflow_id[:8]}")
            
            return service
    
    def clear_workflow_cache(self, workflow_id: str) -> None:
        """
        Очистить кэш сервисов для конкретного workflow
        
        Args:
            workflow_id: ID workflow
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._services.keys()
                if key.endswith(f"_{workflow_id}")
            ]
            for key in keys_to_remove:
                del self._services[key]
            logger.debug(f"Cleared cache for workflow {workflow_id[:8]}")
    
    def clear_all_cache(self) -> None:
        """Очистить весь кэш сервисов"""
        with self._lock:
            self._services.clear()
            logger.debug("Cleared all service cache")


# Глобальный экземпляр реестра
_registry: Optional[ServiceRegistry] = None
_registry_lock = threading.Lock()


def get_service_registry() -> ServiceRegistry:
    """
    Получить глобальный экземпляр ServiceRegistry
    
    Returns:
        ServiceRegistry singleton
    """
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ServiceRegistry()
    return _registry
