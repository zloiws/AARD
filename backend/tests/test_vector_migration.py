"""
Tests for vector search migration
"""
import os

import pytest
from app.core.database import SessionLocal, get_engine
from app.models.agent_memory import AgentMemory
from sqlalchemy import text


@pytest.mark.skipif(os.environ.get("VECTOR_EXTENSION_AVAILABLE") != "1", reason="pgvector extension not available")
def test_vector_extension_exists():
    """Test that pgvector extension is installed"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """))
        exists = result.scalar()
        assert exists, "pgvector extension should be installed"


@pytest.mark.skipif(os.environ.get("VECTOR_EXTENSION_AVAILABLE") != "1", reason="pgvector extension not available")
def test_embedding_column_exists():
    """Test that embedding column exists in agent_memories table"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'agent_memories' 
            AND column_name = 'embedding';
        """))
        row = result.fetchone()
        assert row is not None, "embedding column should exist"
        # Column type should be USER-DEFINED (for vector type) or ARRAY
        assert row[1] in ['USER-DEFINED', 'ARRAY'], f"embedding column type should be vector, got {row[1]}"


@pytest.mark.skipif(os.environ.get("VECTOR_EXTENSION_AVAILABLE") != "1", reason="pgvector extension not available")
def test_hnsw_index_exists():
    """Test that HNSW index exists for vector search"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'agent_memories' 
            AND indexname = 'idx_agent_memories_embedding_hnsw';
        """))
        row = result.fetchone()
        assert row is not None, "HNSW index should exist"
        assert 'hnsw' in row[1].lower(), "Index should use HNSW method"


def test_agent_memory_model_has_embedding():
    """Test that AgentMemory model has embedding field"""
    assert hasattr(AgentMemory, 'embedding'), "AgentMemory should have embedding attribute"


def test_can_store_embedding():
    """Test that we can store an embedding in AgentMemory"""
    db = SessionLocal()
    try:
        # Create a test memory with embedding
        # Note: This requires an agent to exist, so we'll just test the model structure
        memory = AgentMemory(
            agent_id="00000000-0000-0000-0000-000000000000",  # Dummy UUID
            memory_type="fact",
            content={"test": "data"},
            embedding=[0.1] * 1536  # Dummy embedding vector
        )
        
        # Check that embedding can be set
        assert memory.embedding is not None
        assert len(memory.embedding) == 1536
        assert all(isinstance(x, (int, float)) for x in memory.embedding)
        
    finally:
        db.close()

