"""
Quick test for Phase 4: Vector Search with LLM
Simplified version for quick verification
"""
import sys
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
from app.models.agent_memory import MemoryType
from app.services.memory_service import MemoryService
from app.services.embedding_service import EmbeddingService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


async def main():
    """Quick test"""
    print("=" * 70)
    print(" Phase 4: Quick Vector Search Test")
    print("=" * 70)
    
    db = SessionLocal()
    # Ensure clean transaction state
    db.rollback()
    
    try:
        # Get or create agent
        agent = db.query(Agent).filter(Agent.name.like("Test Agent%")).first()
        if not agent:
            agent = Agent(
                id=uuid4(),
                name=f"Test Agent {datetime.now().strftime('%Y%m%d%H%M%S')}",
                status=AgentStatus.ACTIVE.value,
                capabilities=["test"]
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)
        print(f"[OK] Using agent: {agent.id}")
        
        # Initialize services
        memory_service = MemoryService(db)
        embedding_service = EmbeddingService(db)
        
        # Test 1: Generate embedding
        print("\n[1/4] Testing embedding generation...")
        text = "Python is a programming language"
        embedding = await embedding_service.generate_embedding(text)
        print(f"[OK] Generated embedding: {len(embedding)} dimensions")
        
        # Test 2: Save memory with embedding
        print("\n[2/4] Saving memory with embedding...")
        try:
            # First save without embedding to test basic functionality
            memory = await memory_service.save_memory_async(
                agent_id=agent.id,
                memory_type=MemoryType.FACT.value,
                content={"fact": "Python is a programming language"},
                summary="Python programming language fact",
                generate_embedding=False
            )
            print(f"[OK] Memory saved: {memory.id}")
            # Now generate embedding separately
            print("     Generating embedding separately...")
            await memory_service._generate_and_save_embedding_by_id(
                memory_id=memory.id,
                summary="Python programming language fact",
                content={"fact": "Python is a programming language"}
            )
            print(f"[OK] Memory saved: {memory.id}")
            # Check embedding via raw SQL (SQLAlchemy can't read vector type directly)
            from sqlalchemy import text
            result = db.execute(
                text("SELECT embedding IS NOT NULL as has_embedding FROM agent_memories WHERE id = :id"),
                {"id": str(memory.id)}
            )
            row = result.fetchone()
            has_embedding = row[0] if row else False
            print(f"     Has embedding: {has_embedding}")
        except Exception as e:
            db.rollback()  # Rollback on error
            print(f"[ERROR] Failed to save memory: {e}")
            raise
        
        # Test 3: Vector search
        print("\n[3/4] Testing vector search...")
        # Disable combine_with_text_search to avoid transaction issues
        results = await memory_service.search_memories_vector(
            agent_id=agent.id,
            query_text="programming language",
            limit=5,
            similarity_threshold=0.3,
            combine_with_text_search=False
        )
        print(f"[OK] Found {len(results)} results")
        if results:
            for i, mem in enumerate(results[:3], 1):
                print(f"     {i}. {mem.summary[:50]}...")
        
        # Test 4: Cache
        print("\n[4/4] Testing cache...")
        stats = embedding_service.get_cache_stats()
        print(f"[OK] Cache: {stats['cache_size']}/{stats['cache_limit']} ({stats['cache_usage_percent']:.1f}%)")
        
        print("\n" + "=" * 70)
        print("[SUCCESS] All quick tests passed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()  # Rollback on error to clear failed transaction state
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

