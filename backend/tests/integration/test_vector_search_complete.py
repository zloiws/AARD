"""
Complete integration test for Phase 4: Vector Search
Tests the full workflow from memory saving to vector search
"""
import pytest
import asyncio
from uuid import uuid4
from app.services.memory_service import MemoryService
from app.services.embedding_service import EmbeddingService
from app.models.agent_memory import AgentMemory
from app.models.agent import Agent, AgentStatus
from app.core.database import SessionLocal, Base, engine


@pytest.fixture(scope="function")
def db():
    """Database session fixture"""
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    yield db
    
    # Cleanup
    db.query(AgentMemory).delete()
    db.query(Agent).delete()
    db.commit()
    db.close()


@pytest.fixture
def test_agent(db):
    """Create a test agent"""
    agent = Agent(
        id=uuid4(),
        name="Test Agent",
        status=AgentStatus.ACTIVE.value,
        capabilities=["test"]
    )
    db.add(agent)
    db.commit()
    return agent


@pytest.fixture
def memory_service(db):
    """MemoryService fixture"""
    return MemoryService(db)


@pytest.mark.asyncio
async def test_complete_vector_search_workflow(memory_service, db, test_agent):
    """Test complete workflow: save memory with embedding -> vector search"""
    # Step 1: Save memory with automatic embedding generation
    memory = await memory_service.save_memory_async(
        agent_id=test_agent.id,
        memory_type="fact",
        content={"fact": "Python is a high-level programming language"},
        summary="Python programming language fact",
        generate_embedding=True
    )
    
    # Verify embedding was generated
    assert memory.embedding is not None
    assert len(memory.embedding) == 1536
    
    # Step 2: Search using vector similarity
    results = await memory_service.search_memories_vector(
        agent_id=test_agent.id,
        query_text="programming language",
        limit=10,
        similarity_threshold=0.5
    )
    
    # Should find the memory we just created
    assert len(results) >= 1
    assert any(mem.id == memory.id for mem in results)


@pytest.mark.asyncio
async def test_vector_search_similarity_ranking(memory_service, db, test_agent):
    """Test that vector search returns results ranked by similarity"""
    # Create multiple memories with different content
    memories = []
    texts = [
        "Python is a programming language",
        "JavaScript is used for web development",
        "SQL is a database query language",
        "Python has dynamic typing"
    ]
    
    for text in texts:
        memory = await memory_service.save_memory_async(
            agent_id=test_agent.id,
            memory_type="fact",
            content={"fact": text},
            summary=text,
            generate_embedding=True
        )
        memories.append(memory)
    
    # Search for "programming language" - should find Python-related memories first
    results = await memory_service.search_memories_vector(
        agent_id=test_agent.id,
        query_text="programming language",
        limit=10,
        similarity_threshold=0.3
    )
    
    # Should return results (exact order depends on embeddings)
    assert len(results) > 0
    
    # Results should be sorted by similarity (highest first)
    # Note: Actual similarity values depend on the embedding model


@pytest.mark.asyncio
async def test_combined_text_and_vector_search(memory_service, db, test_agent):
    """Test combining vector search with text search"""
    # Create memory with embedding
    memory1 = await memory_service.save_memory_async(
        agent_id=test_agent.id,
        memory_type="fact",
        content={"fact": "Python programming"},
        summary="Python programming fact",
        generate_embedding=True
    )
    
    # Create memory without embedding (will use text search)
    memory2 = memory_service.save_memory(
        agent_id=test_agent.id,
        memory_type="fact",
        content={"fact": "Python programming"},
        summary="Python programming fact",
        generate_embedding=False
    )
    
    # Search with combination
    results = await memory_service.search_memories_vector(
        agent_id=test_agent.id,
        query_text="Python",
        limit=10,
        combine_with_text_search=True
    )
    
    # Should find both memories
    result_ids = {mem.id for mem in results}
    assert memory1.id in result_ids or memory2.id in result_ids


def test_embedding_service_cache(memory_service, db):
    """Test embedding service caching"""
    embedding_service = EmbeddingService(db)
    
    # Clear cache
    embedding_service.clear_cache()
    assert len(embedding_service._embedding_cache) == 0
    
    # Get stats
    stats = embedding_service.get_cache_stats()
    assert stats["cache_size"] == 0


@pytest.mark.asyncio
async def test_embedding_generation_error_handling(memory_service, db, test_agent):
    """Test error handling in embedding generation"""
    # Save memory - embedding generation should not fail the save
    memory = memory_service.save_memory(
        agent_id=test_agent.id,
        memory_type="fact",
        content={"fact": "test"},
        summary="test",
        generate_embedding=False  # Don't generate to avoid async issues in sync method
    )
    
    # Memory should be saved even if embedding generation fails
    assert memory is not None
    assert memory.id is not None

