"""Add plan templates table

Revision ID: 026_add_plan_templates
Revises: 025_fix_vector_dimension_768
Create Date: 2025-12-05 18:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '026_add_plan_templates'
down_revision = '025_fix_vector_dimension_768'
branch_labels = None
depends_on = None


def upgrade():
    # Create plan_templates table if it does not exist (idempotent)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'plan_templates') THEN
            CREATE TABLE plan_templates (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
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
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                last_used_at TIMESTAMP WITHOUT TIME ZONE
            );
        END IF;
    END
    $$;
    """)

    # Create indexes (use IF NOT EXISTS where possible)
    op.execute("CREATE INDEX IF NOT EXISTS idx_plan_templates_category ON plan_templates (category);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_plan_templates_status ON plan_templates (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_plan_templates_usage_count ON plan_templates (usage_count);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_plan_templates_success_rate ON plan_templates (success_rate);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_plan_templates_created_at ON plan_templates (created_at);")

    # GIN index for JSONB columns (for efficient JSON queries) - idempotent
    op.execute("CREATE INDEX IF NOT EXISTS idx_plan_templates_strategy_template_gin ON plan_templates USING GIN (strategy_template);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_plan_templates_steps_template_gin ON plan_templates USING GIN (steps_template);")

    # Convert embedding column to vector type if pgvector is available
    # This block is safe to run multiple times
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                -- Drop the ARRAY column and create vector column (if not already vector)
                ALTER TABLE plan_templates DROP COLUMN IF EXISTS embedding;
                BEGIN
                    ALTER TABLE plan_templates ADD COLUMN IF NOT EXISTS embedding vector(768);
                EXCEPTION WHEN duplicate_column THEN
                    -- already exists as vector, ignore
                    NULL;
                END;

                -- Create HNSW index for vector similarity search
                CREATE INDEX IF NOT EXISTS idx_plan_templates_embedding_hnsw 
                ON plan_templates 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            END IF;
        END $$;
    """)


def downgrade():
    # Drop vector index if exists
    op.execute('DROP INDEX IF EXISTS idx_plan_templates_embedding_hnsw;')
    
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS idx_plan_templates_strategy_template_gin;')
    op.execute('DROP INDEX IF EXISTS idx_plan_templates_steps_template_gin;')
    op.drop_index('idx_plan_templates_created_at', table_name='plan_templates')
    op.drop_index('idx_plan_templates_success_rate', table_name='plan_templates')
    op.drop_index('idx_plan_templates_usage_count', table_name='plan_templates')
    op.drop_index('idx_plan_templates_status', table_name='plan_templates')
    op.drop_index('idx_plan_templates_category', table_name='plan_templates')
    
    # Drop table
    op.drop_table('plan_templates')

