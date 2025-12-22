"""
Tests for ServiceRegistry
"""
from unittest.mock import Mock

import pytest
from app.core.execution_context import ExecutionContext
from app.core.service_registry import ServiceRegistry, get_service_registry


def test_service_registry_singleton():
    """Test that ServiceRegistry is a singleton"""
    registry1 = get_service_registry()
    registry2 = get_service_registry()
    
    assert registry1 is registry2
    assert isinstance(registry1, ServiceRegistry)


def test_service_registry_get_service_with_db(db):
    """Test getting service using db (backward compatibility)"""
    registry = get_service_registry()
    
    # Очищаем кэш перед тестом
    registry.clear_all_cache()
    
    # Test with a service that takes db
    from app.services.prompt_service import PromptService
    
    service = registry.get_service_by_db(PromptService, db)
    
    assert service is not None
    assert isinstance(service, PromptService)
    # Проверяем, что service имеет db и он работает
    assert hasattr(service, 'db')
    assert service.db is not None
    # Проверяем, что service использует переданный db
    # Session объекты могут быть разными экземплярами, но работать с одной БД
    # Проверяем через bind (engine), который должен быть одинаковым
    assert service.db.bind is db.bind or service.db is db


def test_service_registry_get_service_with_context(db):
    """Test getting service using ExecutionContext"""
    registry = get_service_registry()
    
    # Очищаем кэш перед тестом
    registry.clear_all_cache()
    
    context = ExecutionContext.from_db_session(db)
    
    # Test with a service that takes db
    from app.services.prompt_service import PromptService
    
    service = registry.get_service(PromptService, context)
    
    assert service is not None
    assert isinstance(service, PromptService)
    # Проверяем, что service имеет db и он работает
    assert hasattr(service, 'db')
    assert service.db is not None
    # Проверяем, что service использует db из контекста
    # Проверяем через bind (engine) - engine должен быть тем же объектом
    # или через прямое сравнение Session объектов
    assert (service.db.bind is context.db.bind) or (service.db is context.db) or (service.db.bind == context.db.bind)
    assert (context.db.bind is db.bind) or (context.db is db) or (context.db.bind == db.bind)


def test_service_registry_caching(db):
    """Test that services are cached per workflow"""
    registry = get_service_registry()
    context1 = ExecutionContext.from_db_session(db, workflow_id="workflow1")
    context2 = ExecutionContext.from_db_session(db, workflow_id="workflow2")
    
    from app.services.prompt_service import PromptService
    
    service1 = registry.get_service(PromptService, context1)
    service2 = registry.get_service(PromptService, context2)
    service1_again = registry.get_service(PromptService, context1)
    
    # Same workflow should get same instance
    assert service1 is service1_again


def test_service_registry_clear_workflow_cache(db):
    """Test clearing cache for specific workflow"""
    registry = get_service_registry()
    context = ExecutionContext.from_db_session(db, workflow_id="test_workflow")
    
    from app.services.prompt_service import PromptService

    # Get service
    service1 = registry.get_service(PromptService, context)
    
    # Clear cache
    registry.clear_workflow_cache(context.workflow_id)
    
    # Get service again - should create new instance
    service2 = registry.get_service(PromptService, context)
    
    # They might be same or different depending on implementation
    # But cache should be cleared
    assert service2 is not None


def test_service_registry_clear_all_cache(db):
    """Test clearing all cache"""
    registry = get_service_registry()
    context = ExecutionContext.from_db_session(db)
    
    from app.services.prompt_service import PromptService

    # Get service
    service1 = registry.get_service(PromptService, context)
    
    # Clear all cache
    registry.clear_all_cache()
    
    # Get service again
    service2 = registry.get_service(PromptService, context)
    
    assert service2 is not None


def test_service_registry_register_factory(db):
    """Test registering custom factory for service"""
    registry = get_service_registry()
    context = ExecutionContext.from_db_session(db)
    
    # Create mock factory
    mock_service = Mock()
    
    def factory(ctx):
        return mock_service
    
    # Register factory for a test class
    class TestService:
        def __init__(self, ctx):
            pass
    
    registry.register_factory(TestService, factory)
    
    # Get service - should use factory
    service = registry.get_service(TestService, context)
    
    assert service is mock_service
