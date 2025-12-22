"""extend ollama_models with name/is_active and ensure embedding column

Revision ID: 034
Revises: 033
Create Date: 2025-12-11 18:20:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to ollama_models expected by restore script
    op.execute(
        """
        ALTER TABLE IF EXISTS ollama_models
        ADD COLUMN IF NOT EXISTS name varchar(255),
        ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true;
        """
    )

    # Ensure embedding column exists on agent_memories (single statement)
    op.execute("ALTER TABLE IF EXISTS agent_memories ADD COLUMN IF NOT EXISTS embedding vector(768);")


def downgrade() -> None:
    pass


