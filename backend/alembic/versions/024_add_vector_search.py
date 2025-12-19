"""Add vector search support with pgvector

Revision ID: 024_add_vector_search
Revises: 023_add_audit_reports
Create Date: 2025-12-05 17:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '024_add_vector_search'
down_revision = '023_add_audit_reports'
branch_labels = None
depends_on = None


def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # Add embedding column to agent_memories table
    # Using vector(768) for nomic-embed-text embeddings (default model)
    # Can be adjusted for other models (e.g., 1536 for OpenAI, 384 for sentence-transformers)
    # Note: We use ARRAY in SQLAlchemy model, but pgvector will handle it as vector type
    # The actual vector type is created via raw SQL
    op.execute("""
        ALTER TABLE agent_memories 
        ADD COLUMN IF NOT EXISTS embedding vector(768);
    """)
    
    # Create index for vector similarity search using HNSW (Hierarchical Navigable Small World)
    # HNSW is faster for approximate nearest neighbor search
    # Using cosine distance for semantic similarity
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agent_memories_embedding_hnsw 
        ON agent_memories 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)
    
    # Alternative: IVFFlat index (commented out, can be used if HNSW is not available)
    # IVFFlat is faster to build but slower for queries
    # op.execute("""
    #     CREATE INDEX IF NOT EXISTS idx_agent_memories_embedding_ivfflat 
    #     ON agent_memories 
    #     USING ivfflat (embedding vector_cosine_ops)
    #     WITH (lists = 100);
    # """)


def downgrade():
    # Drop index
    op.execute('DROP INDEX IF EXISTS idx_agent_memories_embedding_hnsw;')
    
    # Drop embedding column
    op.drop_column('agent_memories', 'embedding')
    
    # Note: We don't drop the vector extension as it might be used by other tables
    # If you want to drop it, uncomment the line below:
    # op.execute('DROP EXTENSION IF EXISTS vector;')

