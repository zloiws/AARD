"""extend task lifecycle

Revision ID: 017
Revises: 016
Create Date: 2025-12-03 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017_extend_task_lifecycle'
down_revision = '016_add_learning_patterns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to tasks table
    op.add_column('tasks', sa.Column('created_by_role', sa.String(50), nullable=True))
    op.add_column('tasks', sa.Column('approved_by', sa.String(255), nullable=True))
    op.add_column('tasks', sa.Column('approved_by_role', sa.String(50), nullable=True))
    op.add_column('tasks', sa.Column('autonomy_level', sa.Integer(), nullable=False, server_default='2'))
    
    # Note: TaskStatus enum values are handled by SQLAlchemy model
    # The database column uses String type (not enum), so no enum migration needed
    # The enum is only used in Python code for type safety


def downgrade() -> None:
    # Remove columns
    op.drop_column('tasks', 'autonomy_level')
    op.drop_column('tasks', 'approved_by_role')
    op.drop_column('tasks', 'approved_by')
    op.drop_column('tasks', 'created_by_role')
    
    # Note: Removing enum values is complex in PostgreSQL
    # We'll leave the enum values in place for safety
    # If needed, recreate the enum type manually

