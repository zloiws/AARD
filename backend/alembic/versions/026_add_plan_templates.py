"""Add plan templates table

Revision ID: 026_add_plan_templates
Revises: 025_fix_vector_dimension_768
Create Date: 2025-12-05 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '026_add_plan_templates'
down_revision = '025_fix_vector_dimension_768'
branch_labels = None
depends_on = None


def upgrade():
    # Create plan_templates table
    op.create_table(
        'plan_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('goal_pattern', sa.Text(), nullable=False),
        sa.Column('strategy_template', postgresql.JSONB(), nullable=True),
        sa.Column('steps_template', postgresql.JSONB(), nullable=False),
        sa.Column('alternatives_template', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_execution_time', sa.Integer(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_plan_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('source_task_descriptions', postgresql.ARRAY(sa.Text()), nullable=True),
        # Note: embedding column will be created as vector type via raw SQL
        # We use ARRAY in SQLAlchemy model, but pgvector handles it as vector type
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_plan_templates_category', 'plan_templates', ['category'])
    op.create_index('idx_plan_templates_status', 'plan_templates', ['status'])
    op.create_index('idx_plan_templates_usage_count', 'plan_templates', ['usage_count'])
    op.create_index('idx_plan_templates_success_rate', 'plan_templates', ['success_rate'])
    op.create_index('idx_plan_templates_created_at', 'plan_templates', ['created_at'])
    
    # GIN index for JSONB columns (for efficient JSON queries)
    op.execute("CREATE INDEX idx_plan_templates_strategy_template_gin ON plan_templates USING GIN (strategy_template);")
    op.execute("CREATE INDEX idx_plan_templates_steps_template_gin ON plan_templates USING GIN (steps_template);")
    
    # Convert embedding column to vector type if pgvector is available
    # Note: This requires the vector extension to be installed
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                -- Drop the ARRAY column and create vector column
                ALTER TABLE plan_templates DROP COLUMN IF EXISTS embedding;
                ALTER TABLE plan_templates ADD COLUMN embedding vector(768);
                
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

