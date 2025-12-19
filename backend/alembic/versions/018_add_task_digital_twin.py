"""add task digital twin

Revision ID: 018_add_task_digital_twin
Revises: 017_extend_task_lifecycle
Create Date: 2025-12-03 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
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
    # Add context JSONB field if not exists
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS context JSONB;")
    op.execute("COMMENT ON COLUMN tasks.context IS 'Digital Twin context: stores all task-related data including original request, todos, artifacts, logs, and interaction history';")

    # Create GIN index on context JSONB field for efficient queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_context ON tasks (context);")


def downgrade() -> None:
    # Remove index and column if exist
    op.execute("DROP INDEX IF EXISTS idx_tasks_context;")
    op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS context;")

