"""add ollama server extra columns and embedding column

Revision ID: 033
Revises: 032
Create Date: 2025-12-11 18:10:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to ollama_servers
    op.execute(
        """
        ALTER TABLE IF EXISTS ollama_servers
        ADD COLUMN IF NOT EXISTS api_version varchar(32),
        ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true,
        ADD COLUMN IF NOT EXISTS is_default boolean DEFAULT false;
        """
    )

    # Ensure embedding column exists on agent_memories (if table exists)
    # Use vector(768) if pgvector installed; otherwise fallback to float8[]
    try:
        op.execute("ALTER TABLE IF EXISTS agent_memories ADD COLUMN IF NOT EXISTS embedding vector(768);")
    except Exception:
        op.execute("ALTER TABLE IF EXISTS agent_memories ADD COLUMN IF NOT EXISTS embedding double precision[];")


def downgrade() -> None:
    # no-op for downgrade to be safe
    pass


