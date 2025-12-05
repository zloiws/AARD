"""Check which tables are missing from database"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables
from dotenv import load_dotenv
env_file = BASE_DIR / ".env"
load_dotenv(env_file, override=True)

from sqlalchemy import create_engine, text
from app.core.config import get_settings

# Expected tables from models
EXPECTED_TABLES = [
    'tasks', 'plans', 'artifacts', 'approval_requests',
    'ollama_servers', 'ollama_models', 'prompts',
    'agents', 'tools', 'checkpoints', 'traces',
    'request_logs', 'task_queues', 'workflow_events',
    'chat_sessions', 'users', 'agent_experiments',
    'agent_tests', 'agent_memory', 'learning_patterns',
    'evolution_runs', 'evolution_agents'
]

if __name__ == "__main__":
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Get all existing tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """))
        existing_tables = {row[0] for row in result}
        
        print("Existing tables:")
        for table in sorted(existing_tables):
            print(f"  ✓ {table}")
        
        print("\nMissing tables:")
        missing = []
        for table in EXPECTED_TABLES:
            if table not in existing_tables:
                print(f"  ✗ {table}")
                missing.append(table)
        
        if not missing:
            print("\n✓ All expected tables exist!")
        else:
            print(f"\n⚠ {len(missing)} tables are missing")

