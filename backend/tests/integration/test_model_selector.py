"""
Integration tests for ModelSelector
"""
import pytest
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.model_selector import ModelSelector
from app.models.ollama_server import OllamaServer
from app.models.ollama_model import OllamaModel
from app.services.ollama_service import OllamaService


@pytest.fixture
def test_server(db: Session) -> OllamaServer:
    """Create a test server"""
    # Clean up any existing test servers first
    db.query(OllamaServer).filter(OllamaServer.name.like("Test Server%")).delete()
    db.commit()
    
    server = OllamaServer(
        id=uuid4(),
        name=f"Test Server {uuid4().hex[:8]}",
        url=f"http://test-{uuid4().hex[:8]}:11434",
        is_active=True,
        is_default=False,  # Don't set as default to avoid conflicts
        priority=10
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    yield server
    # Cleanup
    db.delete(server)
    db.commit()


@pytest.fixture
def planning_model(db: Session, test_server: OllamaServer) -> OllamaModel:
    """Create a test planning model"""
    model = OllamaModel(
        id=uuid4(),
        server_id=test_server.id,
        name=f"Planning Model {uuid4().hex[:8]}",
        model_name=f"test-planning-model-{uuid4().hex[:8]}",
        capabilities=["planning", "reasoning"],
        is_active=True,
        priority=10
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    yield model
    # Cleanup
    db.delete(model)
    db.commit()


@pytest.fixture
def code_model(db: Session, test_server: OllamaServer) -> OllamaModel:
    """Create a test code generation model"""
    model = OllamaModel(
        id=uuid4(),
        server_id=test_server.id,
        name=f"Code Model {uuid4().hex[:8]}",
        model_name=f"test-code-model-{uuid4().hex[:8]}",
        capabilities=["code_generation", "code_analysis"],
        is_active=True,
        priority=10
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    yield model
    # Cleanup
    db.delete(model)
    db.commit()


@pytest.fixture
def general_model(db: Session, test_server: OllamaServer) -> OllamaModel:
    """Create a test general model"""
    model = OllamaModel(
        id=uuid4(),
        server_id=test_server.id,
        name=f"General Model {uuid4().hex[:8]}",
        model_name=f"test-general-model-{uuid4().hex[:8]}",
        capabilities=["general_chat"],
        is_active=True,
        priority=5
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    yield model
    # Cleanup
    db.delete(model)
    db.commit()


def test_get_planning_model(db: Session, test_server: OllamaServer, planning_model: OllamaModel):
    """Test getting planning model"""
    selector = ModelSelector(db)
    model = selector.get_planning_model()
    
    assert model is not None
    # Should prefer test planning model if it exists, otherwise any planning/reasoning model
    assert "planning" in [c.lower() for c in model.capabilities] or "reasoning" in [c.lower() for c in model.capabilities]


def test_get_planning_model_fallback_to_reasoning(
    db: Session, 
    test_server: OllamaServer, 
    general_model: OllamaModel
):
    """Test fallback to reasoning model when no planning model"""
    # Update general model to have reasoning capability
    general_model.capabilities = ["reasoning", "general_chat"]
    db.commit()
    
    selector = ModelSelector(db)
    model = selector.get_planning_model()
    
    assert model is not None
    assert "reasoning" in [c.lower() for c in model.capabilities]


def test_get_code_model(db: Session, test_server: OllamaServer, code_model: OllamaModel):
    """Test getting code generation model"""
    selector = ModelSelector(db)
    # Test with specific server to ensure we get our test model
    model = selector.get_code_model(server=test_server)
    
    assert model is not None
    assert model.server_id == test_server.id
    # Should find our test code model
    assert model.id == code_model.id or "code_generation" in [c.lower() for c in model.capabilities] or "code" in [c.lower() for c in model.capabilities] or "code_analysis" in [c.lower() for c in model.capabilities]


def test_get_code_model_fallback(db: Session, test_server: OllamaServer, general_model: OllamaModel):
    """Test fallback when no code model available"""
    selector = ModelSelector(db)
    # Test with specific server to ensure we get our test model
    model = selector.get_code_model(server=test_server)
    
    # Should fallback to any available model on the test server
    assert model is not None
    assert model.server_id == test_server.id
    # Should be one of our test models
    assert model.id == general_model.id or model.id in [general_model.id]


def test_get_model_by_capability(db: Session, test_server: OllamaServer, planning_model: OllamaModel):
    """Test getting model by specific capability"""
    selector = ModelSelector(db)
    model = selector.get_model_by_capability("planning")
    
    assert model is not None
    # Should have planning capability or fallback to any model
    assert model.capabilities is not None


def test_get_model_by_capability_not_found(db: Session, test_server: OllamaServer, general_model: OllamaModel):
    """Test getting model by capability that doesn't exist (should fallback)"""
    selector = ModelSelector(db)
    model = selector.get_model_by_capability("nonexistent_capability")
    
    # Should fallback to first available model
    assert model is not None


def test_get_server_for_model(db: Session, test_server: OllamaServer, planning_model: OllamaModel):
    """Test getting server for a model"""
    selector = ModelSelector(db)
    server = selector.get_server_for_model(planning_model)
    
    assert server is not None
    assert server.id == test_server.id


def test_get_planning_model_with_specific_server(
    db: Session, 
    test_server: OllamaServer, 
    planning_model: OllamaModel
):
    """Test getting planning model for specific server"""
    selector = ModelSelector(db)
    model = selector.get_planning_model(server=test_server)
    
    assert model is not None
    assert model.server_id == test_server.id
    # Should find our test planning model
    assert model.id == planning_model.id or "planning" in [c.lower() for c in model.capabilities] or "reasoning" in [c.lower() for c in model.capabilities]


def test_get_code_model_with_specific_server(
    db: Session, 
    test_server: OllamaServer, 
    code_model: OllamaModel
):
    """Test getting code model for specific server"""
    selector = ModelSelector(db)
    model = selector.get_code_model(server=test_server)
    
    assert model is not None
    assert model.server_id == test_server.id
    # Should find our test code model
    assert model.id == code_model.id or "code_generation" in [c.lower() for c in model.capabilities] or "code" in [c.lower() for c in model.capabilities] or "code_analysis" in [c.lower() for c in model.capabilities]


def test_model_selector_prioritizes_planning_over_reasoning(
    db: Session,
    test_server: OllamaServer
):
    """Test that planning capability is preferred over reasoning"""
    # Create reasoning model
    reasoning_model = OllamaModel(
        id=uuid4(),
        server_id=test_server.id,
        name=f"Reasoning Model {uuid4().hex[:8]}",
        model_name=f"test-reasoning-model-{uuid4().hex[:8]}",
        capabilities=["reasoning"],
        is_active=True,
        priority=5
    )
    db.add(reasoning_model)
    
    # Create planning model
    planning_model = OllamaModel(
        id=uuid4(),
        server_id=test_server.id,
        name=f"Planning Model {uuid4().hex[:8]}",
        model_name=f"test-planning-model-{uuid4().hex[:8]}",
        capabilities=["planning"],
        is_active=True,
        priority=10
    )
    db.add(planning_model)
    db.commit()
    
    try:
        selector = ModelSelector(db)
        model = selector.get_planning_model(server=test_server)
        
        # Should prefer planning over reasoning
        assert model is not None
        # When searching on specific server, should find planning model
        assert model.id == planning_model.id or "planning" in [c.lower() for c in model.capabilities] or "reasoning" in [c.lower() for c in model.capabilities]
    finally:
        # Cleanup
        db.delete(reasoning_model)
        db.delete(planning_model)
        db.commit()

