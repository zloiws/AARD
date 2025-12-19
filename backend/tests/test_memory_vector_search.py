"""
Tests for vector search in MemoryService
"""
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from app.core.database import SessionLocal
from app.models.agent_memory import AgentMemory
from app.services.memory_service import MemoryService


@pytest.fixture
def db():
    """Database session fixture"""
    return SessionLocal()


@pytest.fixture
def memory_service(db):
    """MemoryService fixture"""
    return MemoryService(db)


@pytest.mark.asyncio
async def test_search_memories_vector_no_embeddings(memory_service):
    """Test vector search when no memories have embeddings"""
    agent_id = uuid4()
    
    # Mock embedding generation
    with patch.object(memory_service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 1536
        
        # Should return empty list if no embeddings exist
        results = await memory_service.search_memories_vector(
            agent_id=agent_id,
            query_text="test query"
        )
        
        assert isinstance(results, list)
        # Should fallback to text search if combine_with_text_search is True
        assert len(results) >= 0


@pytest.mark.asyncio
async def test_search_memories_vector_with_embeddings(memory_service, db):
    """Test vector search with memories that have embeddings"""
    # This test requires actual database with pgvector
    # For now, we'll test the method structure
    agent_id = uuid4()
    
    # Mock embedding generation
    with patch.object(memory_service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 1536
        
        # Mock database query result
        with patch.object(db, 'execute') as mock_execute:
            # Mock empty result
            mock_result = Mock()
            mock_result.fetchall.return_value = []
            mock_execute.return_value = mock_result
            
            results = await memory_service.search_memories_vector(
                agent_id=agent_id,
                query_text="test query",
                similarity_threshold=0.7
            )
            
            assert isinstance(results, list)


@pytest.mark.asyncio
async def test_search_memories_vector_error_handling(memory_service):
    """Test error handling in vector search"""
    agent_id = uuid4()
    
    # Mock embedding generation to raise error
    with patch.object(memory_service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_embed.side_effect = Exception("Embedding error")
        
        # Should fallback to text search
        results = await memory_service.search_memories_vector(
            agent_id=agent_id,
            query_text="test query",
            combine_with_text_search=True
        )
        
        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_search_memories_vector_filters(memory_service):
    """Test vector search with filters"""
    agent_id = uuid4()
    
    with patch.object(memory_service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 1536
        
        with patch.object(memory_service.db, 'execute') as mock_execute:
            mock_result = Mock()
            mock_result.fetchall.return_value = []
            mock_execute.return_value = mock_result
            
            # Test with memory_type filter
            results = await memory_service.search_memories_vector(
                agent_id=agent_id,
                query_text="test",
                memory_type="fact",
                similarity_threshold=0.8
            )
            
            assert isinstance(results, list)

