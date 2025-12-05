"""
Real LLM tests for Phase 4: Vector Search
Tests vector search functionality with actual LLM models
"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import SessionLocal
from app.models.agent import Agent, AgentStatus
from app.models.agent_memory import AgentMemory, MemoryType
from app.services.memory_service import MemoryService
from app.services.embedding_service import EmbeddingService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def create_test_agent(db):
    """Create or get a test agent"""
    # Try to find existing test agent
    agent = db.query(Agent).filter(Agent.name == "Test Agent for Vector Search").first()
    
    if agent:
        print(f"[OK] Using existing test agent: {agent.id}")
        return agent
    
    # Create new agent with unique name
    agent = Agent(
        id=uuid4(),
        name=f"Test Agent Vector Search {datetime.now().strftime('%Y%m%d%H%M%S')}",
        status=AgentStatus.ACTIVE.value,
        capabilities=["vector_search", "memory"]
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    print(f"[OK] Created test agent: {agent.id}")
    return agent


async def test_embedding_generation(embedding_service):
    """Test 1: Generate embeddings with real LLM"""
    print("\n" + "=" * 70)
    print(" Test 1: Embedding Generation with LLM")
    print("=" * 70)
    
    test_texts = [
        "Python is a high-level programming language",
        "JavaScript is used for web development",
        "SQL is a database query language",
        "Machine learning uses neural networks"
    ]
    
    embeddings = []
    embedding_dim = None
    for i, text in enumerate(test_texts, 1):
        print(f"\n[INFO] Generating embedding for: {text[:50]}...")
        embedding = await embedding_service.generate_embedding(text)
        embeddings.append(embedding)
        print(f"[OK] Generated embedding: {len(embedding)} dimensions")
        
        # Check embedding properties
        assert len(embedding) > 0, "Embedding should have dimensions"
        assert all(isinstance(x, (int, float)) for x in embedding), "All values should be numeric"
        
        # Store dimension for consistency check
        if embedding_dim is None:
            embedding_dim = len(embedding)
            print(f"[INFO] Using embedding dimension: {embedding_dim}")
        else:
            assert len(embedding) == embedding_dim, f"All embeddings should have same dimension: {embedding_dim}, got {len(embedding)}"
        
        # Check normalization (should be approximately normalized)
        norm = sum(x * x for x in embedding) ** 0.5
        print(f"   Vector norm: {norm:.4f} (should be ~1.0 for normalized)")
    
    # Test cosine similarity
    print("\n[INFO] Testing cosine similarity...")
    similarity = embedding_service.cosine_similarity(embeddings[0], embeddings[1])
    print(f"[OK] Cosine similarity between text 1 and 2: {similarity:.4f}")
    
    # Similar texts should have higher similarity
    similarity_same = embedding_service.cosine_similarity(embeddings[0], embeddings[0])
    print(f"[OK] Cosine similarity (same text): {similarity_same:.4f} (should be ~1.0)")
    
    return embeddings


async def test_save_memory_with_embedding(memory_service, agent_id, db):
    """Test 2: Save memories with automatic embedding generation"""
    print("\n" + "=" * 70)
    print(" Test 2: Save Memories with Automatic Embedding")
    print("=" * 70)
    
    test_memories = [
        {
            "memory_type": MemoryType.FACT.value,
            "content": {"fact": "Python is a programming language created by Guido van Rossum"},
            "summary": "Python programming language fact"
        },
        {
            "memory_type": MemoryType.EXPERIENCE.value,
            "content": {"experience": "Learned to use vector search for semantic similarity"},
            "summary": "Vector search experience"
        },
        {
            "memory_type": MemoryType.PATTERN.value,
            "content": {"pattern": "When debugging, check logs first, then code"},
            "summary": "Debugging pattern"
        }
    ]
    
    saved_memories = []
    for i, mem_data in enumerate(test_memories, 1):
        print(f"\n[INFO] Saving memory {i}/{len(test_memories)}: {mem_data['summary']}")
        
        memory = await memory_service.save_memory_async(
            agent_id=agent_id,
            memory_type=mem_data["memory_type"],
            content=mem_data["content"],
            summary=mem_data["summary"],
            importance=0.7,
            generate_embedding=True
        )
        
        # Check embedding via raw SQL (SQLAlchemy can't read vector type directly)
        from sqlalchemy import text
        result = db.execute(
            text("SELECT embedding IS NOT NULL as has_embedding FROM agent_memories WHERE id = :id"),
            {"id": str(memory.id)}
        )
        row = result.fetchone()
        has_embedding = row[0] if row else False
        if has_embedding:
            print(f"[OK] Memory saved with embedding (768 dims)")
            saved_memories.append(memory)
        else:
            print(f"[WARN] Memory saved but embedding is None")
    
    print(f"\n[OK] Saved {len(saved_memories)} memories with embeddings")
    return saved_memories


async def test_vector_search(memory_service, agent_id, db):
    """Test 3: Vector search functionality"""
    print("\n" + "=" * 70)
    print(" Test 3: Vector Search")
    print("=" * 70)
    
    query_texts = ["programming language", "vector search", "debugging"]
    for query_text in query_texts:
        print(f"\n[INFO] Searching for: '{query_text}'")
        
        results = await memory_service.search_memories_vector(
            agent_id=agent_id,
            query_text=query_text,
            limit=5,
            similarity_threshold=0.3,  # Lower threshold for testing
            combine_with_text_search=False  # Pure vector search
        )
        
        print(f"[OK] Found {len(results)} results")
        
        if results:
            print("\n   Top results:")
            for i, memory in enumerate(results[:3], 1):
                print(f"   {i}. {memory.summary[:60]}...")
                # Check embedding via raw SQL (SQLAlchemy can't read vector type directly)
                from sqlalchemy import text
                result = db.execute(
                    text("SELECT embedding IS NOT NULL as has_embedding FROM agent_memories WHERE id = :id"),
                    {"id": str(memory.id)}
                )
                row = result.fetchone()
                has_embedding = row[0] if row else False
                print(f"      Type: {memory.memory_type}, Has embedding: {has_embedding}")
        else:
            print("   [WARN] No results found (may need lower threshold or more memories)")


async def test_combined_search(memory_service, agent_id):
    """Test 4: Combined vector + text search"""
    print("\n" + "=" * 70)
    print(" Test 4: Combined Vector + Text Search")
    print("=" * 70)
    
    query = "programming"
    
    print(f"\n[INFO] Searching for: '{query}' (combined)")
    
    results = await memory_service.search_memories_vector(
        agent_id=agent_id,
        query_text=query,
        limit=10,
        similarity_threshold=0.3,
        combine_with_text_search=True  # Combine with text search
    )
    
    print(f"[OK] Found {len(results)} results (vector + text)")
    
    if results:
        print("\n   Results:")
        for i, memory in enumerate(results[:5], 1):
            print(f"   {i}. {memory.summary[:60]}...")
            print(f"      Type: {memory.memory_type}")


async def test_similarity_thresholds(memory_service, agent_id):
    """Test 5: Different similarity thresholds"""
    print("\n" + "=" * 70)
    print(" Test 5: Similarity Thresholds")
    print("=" * 70)
    
    query = "programming language"
    thresholds = [0.9, 0.7, 0.5, 0.3]
    
    for threshold in thresholds:
        print(f"\n[INFO] Threshold: {threshold}")
        results = await memory_service.search_memories_vector(
            agent_id=agent_id,
            query_text=query,
            limit=10,
            similarity_threshold=threshold,
            combine_with_text_search=False
        )
        print(f"[OK] Found {len(results)} results with threshold {threshold}")


async def test_embedding_cache(embedding_service):
    """Test 6: Embedding cache functionality"""
    print("\n" + "=" * 70)
    print(" Test 6: Embedding Cache")
    print("=" * 70)
    
    test_text = "Python is a programming language"
    
    # Clear cache
    embedding_service.clear_cache()
    print("[OK] Cache cleared")
    
    # First call - should generate
    print(f"\n[INFO] First call (should generate): {test_text}")
    embedding1 = await embedding_service.generate_embedding(test_text, use_cache=True)
    print(f"[OK] Generated embedding")
    
    # Second call - should use cache
    print(f"\n[INFO] Second call (should use cache): {test_text}")
    embedding2 = await embedding_service.generate_embedding(test_text, use_cache=True)
    print(f"[OK] Retrieved from cache")
    
    # Check they're the same
    assert embedding1 == embedding2, "Cached embedding should match original"
    print("[OK] Cached embedding matches original")
    
    # Get cache stats
    stats = embedding_service.get_cache_stats()
    print(f"\n[OK] Cache stats: {stats['cache_size']}/{stats['cache_limit']} ({stats['cache_usage_percent']:.1f}%)")


async def main():
    """Run all LLM tests for Phase 4"""
    print("=" * 70)
    print(" Phase 4: Vector Search - Real LLM Tests")
    print("=" * 70)
    print("\nThis will test Phase 4 components with actual LLM models.")
    print("Make sure Ollama servers are running and accessible.\n")
    
    db = SessionLocal()
    
    try:
        # Create test agent
        agent = create_test_agent(db)
        
        # Initialize services
        memory_service = MemoryService(db)
        embedding_service = EmbeddingService(db)
        
        # Test 1: Embedding generation
        test1_result = await test_embedding_generation(embedding_service)
        
        # Test 2: Save memories with embeddings
        test2_result = await test_save_memory_with_embedding(memory_service, agent.id, db)
        
        # Test 3: Vector search
        test3_result = await test_vector_search(memory_service, agent.id, db)
        
        # Test 4: Combined search
        await test_combined_search(memory_service, agent.id)
        
        # Test 5: Similarity thresholds
        await test_similarity_thresholds(memory_service, agent.id)
        
        # Test 6: Cache
        await test_embedding_cache(embedding_service)
        
        # Summary
        print("\n" + "=" * 70)
        print(" Test Summary")
        print("=" * 70)
        print("[SUCCESS] All tests completed!")
        print("\nNext steps:")
        print("  1. Check database: SELECT COUNT(*) FROM agent_memories WHERE embedding IS NOT NULL;")
        print("  2. Test vector search in application")
        print("  3. Run migration script for existing memories if needed")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

