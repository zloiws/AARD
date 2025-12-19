"""
Tests for EmbeddingService
"""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.core.database import SessionLocal
from app.services.embedding_service import EmbeddingService


@pytest.fixture
def db():
    """Database session fixture"""
    return SessionLocal()


@pytest.fixture
def embedding_service(db):
    """EmbeddingService fixture"""
    return EmbeddingService(db)


def test_embedding_service_initialization(embedding_service):
    """Test EmbeddingService initialization"""
    assert embedding_service is not None
    assert embedding_service.DEFAULT_EMBEDDING_DIM == 1536
    assert len(embedding_service._embedding_cache) == 0


def test_normalize_vector(embedding_service):
    """Test vector normalization"""
    # Test normal vector
    vector = [3.0, 4.0, 0.0]
    normalized = embedding_service._normalize_vector(vector)
    
    # Check that norm is approximately 1.0
    norm = sum(x * x for x in normalized) ** 0.5
    assert abs(norm - 1.0) < 0.0001
    
    # Test zero vector
    zero_vector = [0.0] * 10
    normalized_zero = embedding_service._normalize_vector(zero_vector)
    assert normalized_zero == zero_vector
    
    # Test empty vector
    empty = embedding_service._normalize_vector([])
    assert len(empty) == 1536  # Should return default dimension


def test_cosine_similarity(embedding_service):
    """Test cosine similarity calculation"""
    # Identical vectors should have similarity 1.0
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    similarity = embedding_service.cosine_similarity(vec1, vec2)
    assert abs(similarity - 1.0) < 0.0001
    
    # Orthogonal vectors should have similarity 0.0
    vec1 = [1.0, 0.0]
    vec2 = [0.0, 1.0]
    similarity = embedding_service.cosine_similarity(vec1, vec2)
    assert abs(similarity - 0.0) < 0.0001
    
    # Different dimensions should raise error
    with pytest.raises(ValueError):
        embedding_service.cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])


def test_cache_embedding(embedding_service):
    """Test embedding caching"""
    text = "test text"
    embedding = [0.1] * 1536
    
    embedding_service._cache_embedding(text, embedding)
    assert text in embedding_service._embedding_cache
    assert embedding_service._embedding_cache[text] == embedding


def test_clear_cache(embedding_service):
    """Test cache clearing"""
    embedding_service._cache_embedding("test", [0.1] * 1536)
    assert len(embedding_service._embedding_cache) > 0
    
    embedding_service.clear_cache()
    assert len(embedding_service._embedding_cache) == 0


def test_get_cache_stats(embedding_service):
    """Test cache statistics"""
    stats = embedding_service.get_cache_stats()
    assert "cache_size" in stats
    assert "cache_limit" in stats
    assert "cache_usage_percent" in stats
    assert stats["cache_size"] == 0
    assert stats["cache_limit"] == 1000


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(embedding_service):
    """Test embedding generation for empty text"""
    embedding = await embedding_service.generate_embedding("")
    assert len(embedding) == 1536
    assert all(x == 0.0 for x in embedding)


@pytest.mark.asyncio
async def test_generate_embedding_with_cache(embedding_service):
    """Test embedding generation with caching"""
    text = "test text for caching"
    
    # Mock the Ollama API call
    with patch.object(embedding_service, '_generate_embedding_via_ollama', new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = [0.1] * 1536
        
        # First call - should call Ollama
        embedding1 = await embedding_service.generate_embedding(text, use_cache=True)
        assert mock_ollama.call_count == 1
        
        # Second call - should use cache
        embedding2 = await embedding_service.generate_embedding(text, use_cache=True)
        assert mock_ollama.call_count == 1  # Should not call again
        assert embedding1 == embedding2


@pytest.mark.asyncio
async def test_generate_embeddings_batch(embedding_service):
    """Test batch embedding generation"""
    texts = ["text 1", "text 2", "text 3"]
    
    # Mock the Ollama API call
    with patch.object(embedding_service, '_generate_embedding_via_ollama', new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = [0.1] * 1536
        
        embeddings = await embedding_service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == len(texts)
        assert all(len(emb) == 1536 for emb in embeddings)
        assert mock_ollama.call_count == len(texts)


@pytest.mark.asyncio
async def test_generate_embedding_error_handling(embedding_service):
    """Test error handling in embedding generation"""
    # Mock error in Ollama API
    with patch.object(embedding_service, '_generate_embedding_via_ollama', new_callable=AsyncMock) as mock_ollama:
        mock_ollama.side_effect = Exception("API Error")
        
        # Should return zero vector on error
        embedding = await embedding_service.generate_embedding("test text")
        assert len(embedding) == 1536
        assert all(x == 0.0 for x in embedding)

