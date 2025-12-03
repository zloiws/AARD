"""Test database connection"""
import sys
from pathlib import Path

# Setup path and env
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

print("Testing database connection...")
try:
    from app.core.database import engine
    conn = engine.connect()
    print("✓ Database connection successful!")
    
    # Test query
    from sqlalchemy import text
    result = conn.execute(text("SELECT version()"))
    version = result.fetchone()
    print(f"✓ PostgreSQL version: {version[0][:50]}...")
    
    # Check if extensions exist
    result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp')"))
    extensions = [row[0] for row in result.fetchall()]
    print(f"✓ Extensions found: {extensions}")
    
    if 'vector' not in extensions:
        print("⚠ WARNING: pgvector extension not found! Run: CREATE EXTENSION vector;")
    if 'uuid-ossp' not in extensions:
        print("⚠ WARNING: uuid-ossp extension not found! Run: CREATE EXTENSION \"uuid-ossp\";")
    
    conn.close()
except Exception as e:
    print(f"✗ Database connection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

