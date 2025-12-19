"""
Script to fix vector dimension from 1536 to 768 for nomic-embed-text model
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import engine
from sqlalchemy import text


def fix_vector_dimension():
    """Fix vector dimension from 1536 to 768"""
    print("=" * 70)
    print(" Fixing vector dimension from 1536 to 768")
    print("=" * 70)
    
    with engine.connect() as conn:
        try:
            # Start transaction
            trans = conn.begin()
            
            # Drop index if exists
            print("\n[1/4] Dropping index...")
            conn.execute(text("DROP INDEX IF EXISTS idx_agent_memories_embedding_hnsw;"))
            print("[OK] Index dropped")
            
            # Drop column if exists
            print("\n[2/4] Dropping embedding column...")
            conn.execute(text("ALTER TABLE agent_memories DROP COLUMN IF EXISTS embedding;"))
            print("[OK] Column dropped")
            
            # Recreate with correct dimension
            print("\n[3/4] Creating embedding column with dimension 768...")
            conn.execute(text("ALTER TABLE agent_memories ADD COLUMN embedding vector(768);"))
            print("[OK] Column created")
            
            # Recreate index
            print("\n[4/4] Creating HNSW index...")
            conn.execute(text("""
                CREATE INDEX idx_agent_memories_embedding_hnsw 
                ON agent_memories 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """))
            print("[OK] Index created")
            
            # Commit transaction
            trans.commit()
            
            print("\n" + "=" * 70)
            print("[SUCCESS] Vector dimension fixed to 768!")
            print("=" * 70)
            
        except Exception as e:
            trans.rollback()
            print(f"\n[ERROR] Failed to fix vector dimension: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    fix_vector_dimension()

