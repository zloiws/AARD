"""add benchmark system tables

Revision ID: 021_add_benchmark_system
Revises: 020_add_workflow_events
Create Date: 2025-12-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '021_add_benchmark_system'
down_revision = '020_add_workflow_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create benchmark_tasks table
    op.create_table(
        'benchmark_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('task_description', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=True),
        sa.Column('evaluation_criteria', postgresql.JSONB(), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('task_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "task_type IN ('code_generation', 'code_analysis', 'reasoning', 'planning', 'general_chat')",
            name='benchmark_tasks_task_type_check'
        ),
    )
    
    # Create indexes for benchmark_tasks
    op.create_index('idx_benchmark_tasks_task_type', 'benchmark_tasks', ['task_type'])
    op.create_index('idx_benchmark_tasks_category', 'benchmark_tasks', ['category'])
    op.create_index('idx_benchmark_tasks_name', 'benchmark_tasks', ['name'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_benchmark_tasks_name', table_name='benchmark_tasks')
    op.drop_index('idx_benchmark_tasks_category', table_name='benchmark_tasks')
    op.drop_index('idx_benchmark_tasks_task_type', table_name='benchmark_tasks')
    
    # Drop table
    op.drop_table('benchmark_tasks')

