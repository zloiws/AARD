"""
Script to fix missing agent_metadata column
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from app.core.database import engine

def fix_agent_metadata():
    """Add agent_metadata column if it doesn't exist"""
    print("Checking agents table...")
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'agents' AND column_name = 'agent_metadata'
        """))
        
        exists = result.fetchone() is not None
        
        if exists:
            print("[OK] Column agent_metadata already exists")
            return True
        
        print("[WARN] Column agent_metadata does not exist, adding...")
        
        try:
            # Add column
            conn.execute(text("""
                ALTER TABLE agents 
                ADD COLUMN agent_metadata JSONB
            """))
            conn.commit()
            print("[OK] Column agent_metadata added successfully")
            return True
        except Exception as e:
            print(f"[FAIL] Error adding column: {e}")
            conn.rollback()
            return False

if __name__ == "__main__":
    success = fix_agent_metadata()
    sys.exit(0 if success else 1)

