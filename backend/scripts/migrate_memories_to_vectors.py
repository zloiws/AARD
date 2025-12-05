"""
Script to migrate existing memories to vector embeddings
Generates embeddings for all memories that don't have them yet
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import SessionLocal
from app.models.agent_memory import AgentMemory
from app.services.embedding_service import EmbeddingService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


async def migrate_memories(
    batch_size: int = 10,
    dry_run: bool = False
):
    """
    Migrate existing memories to vector embeddings.
    
    Args:
        batch_size: Number of memories to process in each batch
        dry_run: If True, only show what would be done without making changes
    """
    print("=" * 70)
    print(" Memory to Vector Migration")
    print("=" * 70)
    
    if dry_run:
        print("\n[DRY RUN] No changes will be made\n")
    
    db = SessionLocal()
    
    try:
        # Get all memories without embeddings
        memories_without_embeddings = db.query(AgentMemory).filter(
            AgentMemory.embedding.is_(None)
        ).all()
        
        total = len(memories_without_embeddings)
        print(f"\nFound {total} memories without embeddings")
        
        if total == 0:
            print("\n✅ All memories already have embeddings!")
            return
        
        # Initialize embedding service
        embedding_service = EmbeddingService(db)
        
        # Process in batches
        processed = 0
        failed = 0
        skipped = 0
        
        print(f"\nProcessing in batches of {batch_size}...")
        print("-" * 70)
        
        for i in range(0, total, batch_size):
            batch = memories_without_embeddings[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            print(f"\nBatch {batch_num}/{total_batches} ({len(batch)} memories)")
            
            for memory in batch:
                try:
                    # Extract text for embedding
                    text_for_embedding = memory.summary
                    if not text_for_embedding:
                        # Try to extract from content
                        if isinstance(memory.content, dict):
                            text_for_embedding = (
                                memory.content.get("description") or
                                memory.content.get("text") or
                                memory.content.get("content") or
                                str(memory.content)
                            )
                        else:
                            text_for_embedding = str(memory.content)
                    
                    if not text_for_embedding or not text_for_embedding.strip():
                        print(f"  ⏭️  Skipped {memory.id}: no text available")
                        skipped += 1
                        continue
                    
                    if dry_run:
                        print(f"  [DRY RUN] Would generate embedding for {memory.id}: {text_for_embedding[:50]}...")
                        processed += 1
                    else:
                        # Generate embedding
                        embedding = await embedding_service.generate_embedding(text_for_embedding)
                        
                        # Save embedding
                        memory.embedding = embedding
                        db.commit()
                        
                        processed += 1
                        print(f"  ✅ {memory.id}: embedding generated ({len(embedding)} dims)")
                
                except Exception as e:
                    failed += 1
                    print(f"  ❌ {memory.id}: error - {e}")
                    logger.error(f"Error generating embedding for memory {memory.id}: {e}", exc_info=True)
                    db.rollback()
            
            # Progress update
            progress = ((i + len(batch)) / total) * 100
            print(f"\nProgress: {progress:.1f}% ({i + len(batch)}/{total})")
        
        # Summary
        print("\n" + "=" * 70)
        print(" Migration Summary")
        print("=" * 70)
        print(f"  Total memories: {total}")
        print(f"  Processed: {processed}")
        print(f"  Failed: {failed}")
        print(f"  Skipped: {skipped}")
        
        if not dry_run:
            # Verify results
            remaining = db.query(AgentMemory).filter(
                AgentMemory.embedding.is_(None)
            ).count()
            
            print(f"\n  Remaining without embeddings: {remaining}")
            
            if remaining == 0:
                print("\n✅ All memories migrated successfully!")
            else:
                print(f"\n⚠️  {remaining} memories still need embeddings")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate existing memories to vector embeddings")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of memories to process in each batch (default: 10)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    print("\n⚠️  This will generate embeddings for all memories without them.")
    print("   This may take a while depending on the number of memories.")
    if not args.dry_run:
        print("\n   Press Ctrl+C to cancel, or Enter to continue...")
        try:
            input()
        except KeyboardInterrupt:
            print("\n❌ Cancelled.")
            sys.exit(1)
    
    asyncio.run(migrate_memories(
        batch_size=args.batch_size,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()

