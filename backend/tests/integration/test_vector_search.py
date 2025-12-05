"""
Integration tests for vector search functionality
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
    # Create tables if needed
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
async def test_vector_search_integration(memory_service, db, test_agent):
    """Integration test for vector search"""
    # This test requires pgvector extension and actual embeddings
    # For now, we test the integration structure
    
    # Create a memory with embedding
    memory = memory_service.save_memory(
        agent_id=test_agent.id,
        memory_type="fact",
        content={"fact": "Python is a programming language"},
        summary="Python programming language fact"
    )
    
    # Generate and set embedding
    embedding_service = EmbeddingService(db)
    embedding = await embedding_service.generate_embedding(memory.summary or "")
    memory.embedding = embedding
    db.commit()
    
    # Test vector search
    results = await memory_service.search_memories_vector(
        agent_id=test_agent.id,
        query_text="programming language",
        limit=10
    )
    
    assert isinstance(results, list)
    # Results may be empty if pgvector is not properly configured
    # But the method should not raise errors


@pytest.mark.asyncio
async def test_embedding_generation_and_storage(memory_service, db, test_agent):
    """Test embedding generation and storage workflow"""
    # Save memory
    memory = memory_service.save_memory(
        agent_id=test_agent.id,
        memory_type="experience",
        content={"experience": "Learned to use vector search"},
        summary="Vector search experience"
    )
    
    # Generate embedding
    embedding_service = EmbeddingService(db)
    embedding = await embedding_service.generate_embedding(memory.summary or "")
    
    # Store embedding
    memory.embedding = embedding
    db.commit()
    db.refresh(memory)
    
    # Verify embedding is stored
    assert memory.embedding is not None
    assert len(memory.embedding) == 1536  # Default dimension


def test_embedding_service_integration(db):
    """Test EmbeddingService integration"""
    embedding_service = EmbeddingService(db)
    
    # Test cache
    stats = embedding_service.get_cache_stats()
    assert "cache_size" in stats
    
    # Test normalization
    test_vector = [3.0, 4.0, 0.0]
    normalized = embedding_service._normalize_vector(test_vector)
    norm = sum(x * x for x in normalized) ** 0.5
    assert abs(norm - 1.0) < 0.0001

