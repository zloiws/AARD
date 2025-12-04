"""add task digital twin

Revision ID: 018_add_task_digital_twin
Revises: 017_extend_task_lifecycle
Create Date: 2025-12-03 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_add_task_digital_twin'
down_revision = '017_extend_task_lifecycle'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add context field for Digital Twin concept
    # This JSONB field stores all task context:
    # - original user request
    # - active and historical ToDo lists
    # - generated artifacts (prompts, code, tables)
    # - execution logs, errors, validation results
    # - interaction history (approvals, corrections)
    op.add_column(
        'tasks',
        sa.Column(
            'context',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Digital Twin context: stores all task-related data including original request, todos, artifacts, logs, and interaction history'
        )
    )
    
    # Create GIN index on context JSONB field for efficient queries
    op.create_index(
        'idx_tasks_context',
        'tasks',
        ['context'],
        postgresql_using='gin',
        unique=False
    )


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_tasks_context', table_name='tasks')
    
    # Remove context column
    op.drop_column('tasks', 'context')

