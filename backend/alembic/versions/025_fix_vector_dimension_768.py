"""Fix vector dimension to 768 for nomic-embed-text

Revision ID: 025_fix_vector_dimension_768
Revises: 024_add_vector_search
Create Date: 2025-12-05 17:35:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '025_fix_vector_dimension_768'
down_revision = '024_add_vector_search'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column exists and has wrong dimension
    # If column exists with vector(1536), we need to drop it and recreate with vector(768)
    # Note: We can't directly alter vector dimension in PostgreSQL, so we need to:
    # 1. Drop the index
    # 2. Drop the column
    # 3. Recreate with correct dimension
    # 4. Recreate the index
    
    # Check if column exists
    op.execute("""
        DO $$
        BEGIN
            -- Check if embedding column exists
            IF EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'agent_memories' 
                AND column_name = 'embedding'
            ) THEN
                -- Drop index if exists
                DROP INDEX IF EXISTS idx_agent_memories_embedding_hnsw;
                
                -- Drop column
                ALTER TABLE agent_memories DROP COLUMN embedding;
                
                -- Recreate with correct dimension (768 for nomic-embed-text)
                ALTER TABLE agent_memories 
                ADD COLUMN embedding vector(768);
                
                -- Recreate index
                CREATE INDEX idx_agent_memories_embedding_hnsw 
                ON agent_memories 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            ELSE
                -- Column doesn't exist, create it with correct dimension
                ALTER TABLE agent_memories 
                ADD COLUMN embedding vector(768);
                
                -- Create index
                CREATE INDEX idx_agent_memories_embedding_hnsw 
                ON agent_memories 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            END IF;
        END $$;
    """)


def downgrade():
    # Drop index and column
    op.execute('DROP INDEX IF EXISTS idx_agent_memories_embedding_hnsw;')
    op.execute('ALTER TABLE agent_memories DROP COLUMN IF EXISTS embedding;')

