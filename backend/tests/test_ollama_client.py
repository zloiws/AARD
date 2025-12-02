"""
Tests for Ollama client
"""
import pytest
from app.core.ollama_client import OllamaClient, TaskType, OllamaError


@pytest.fixture
def ollama_client():
    """Create Ollama client instance"""
    return OllamaClient()


def test_model_selection(ollama_client):
    """Test model selection based on task type"""
    # Test code generation selects coding model
    instance = ollama_client.select_model_for_task(TaskType.CODE_GENERATION)
    assert instance is not None
    assert "coding" in instance.capabilities or "code" in instance.model.lower()
    
    # Test reasoning selects reasoning model
    instance = ollama_client.select_model_for_task(TaskType.REASONING)
    assert instance is not None


def test_cache_key_generation(ollama_client):
    """Test cache key generation"""
    key1 = ollama_client._get_cache_key("test prompt", "model1")
    key2 = ollama_client._get_cache_key("test prompt", "model1")
    key3 = ollama_client._get_cache_key("test prompt", "model2")
    
    assert key1 == key2  # Same prompt and model should generate same key
    assert key1 != key3  # Different model should generate different key


@pytest.mark.asyncio
async def test_health_check(ollama_client):
    """Test health check"""
    if ollama_client.instances:
        instance = ollama_client.instances[0]
        health = await ollama_client.health_check(instance)
        # Should return True if instance is available
        assert isinstance(health, bool)

