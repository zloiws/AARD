"""
Apply plan_templates migration manually
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import engine
from sqlalchemy import text

def apply_migration():
    """Apply plan_templates migration"""
    print("=" * 70)
    print(" Applying plan_templates migration")
    print("=" * 70)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Read migration file
            migration_file = backend_dir / "alembic" / "versions" / "026_add_plan_templates.py"
            
            # Execute upgrade function
            print("\n[1/1] Creating plan_templates table...")
            
            # Create table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS plan_templates (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    category VARCHAR(100),
                    tags VARCHAR[],
                    goal_pattern TEXT NOT NULL,
                    strategy_template JSONB,
                    steps_template JSONB NOT NULL,
                    alternatives_template JSONB,
                    status VARCHAR(20) NOT NULL DEFAULT 'draft',
                    version INTEGER NOT NULL DEFAULT 1,
                    success_rate FLOAT,
                    avg_execution_time INTEGER,
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    source_plan_ids UUID[],
                    source_task_descriptions TEXT[],
                    embedding FLOAT[],
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    last_used_at TIMESTAMP
                );
            """))
            
            # Create indexes
            print("[2/2] Creating indexes...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_templates_category ON plan_templates (category);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_templates_status ON plan_templates (status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_templates_usage_count ON plan_templates (usage_count);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_templates_success_rate ON plan_templates (success_rate);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_templates_created_at ON plan_templates (created_at);"))
            
            # GIN indexes for JSONB
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_templates_strategy_template_gin ON plan_templates USING GIN (strategy_template);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_templates_steps_template_gin ON plan_templates USING GIN (steps_template);"))
            
            # Convert embedding to vector if pgvector is available
            conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                        -- Drop ARRAY column if exists and create vector column
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'plan_templates' AND column_name = 'embedding' AND data_type = 'ARRAY') THEN
                            ALTER TABLE plan_templates DROP COLUMN embedding;
                        END IF;
                        
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'plan_templates' AND column_name = 'embedding' AND udt_name = 'vector') THEN
                            ALTER TABLE plan_templates ADD COLUMN embedding vector(768);
                            
                            CREATE INDEX IF NOT EXISTS idx_plan_templates_embedding_hnsw 
                            ON plan_templates 
                            USING hnsw (embedding vector_cosine_ops)
                            WITH (m = 16, ef_construction = 64);
                        END IF;
                    END IF;
                END $$;
            """))
            
            trans.commit()
            
            print("\n" + "=" * 70)
            print("[SUCCESS] Migration applied successfully!")
            print("=" * 70)
            
        except Exception as e:
            trans.rollback()
            print(f"\n[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    apply_migration()

