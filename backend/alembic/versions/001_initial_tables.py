"""initial tables

Revision ID: 001
Revises: 
Create Date: 2025-01-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('parent_task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('current_checkpoint_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_task_id'], ['tasks.id'], ),
        sa.CheckConstraint('priority >= 0 AND priority <= 9', name='tasks_priority_check'),
    )
    
    # Create indexes for tasks
    op.create_index('idx_tasks_status', 'tasks', ['status'])
    op.create_index('idx_tasks_priority', 'tasks', ['priority'])
    op.create_index('idx_tasks_created_at', 'tasks', ['created_at'])
    op.create_index('idx_tasks_parent', 'tasks', ['parent_task_id'])
    
    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.String(10), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('code', sa.Text(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('test_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('security_rating', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.CheckConstraint("type IN ('agent', 'tool')", name='artifacts_type_check'),
        sa.CheckConstraint("status IN ('draft', 'waiting_approval', 'active', 'deprecated')", name='artifacts_status_check'),
        sa.CheckConstraint('security_rating >= 0 AND security_rating <= 1', name='artifacts_security_rating_check'),
    )
    
    # Create indexes for artifacts
    op.create_index('idx_artifacts_type_status', 'artifacts', ['type', 'status'])
    op.create_index('idx_artifacts_version', 'artifacts', ['version'])
    
    # Create artifact_dependencies table
    op.create_table(
        'artifact_dependencies',
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('depends_on_artifact_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ),
        sa.ForeignKeyConstraint(['depends_on_artifact_id'], ['artifacts.id'], ),
    )


def downgrade() -> None:
    op.drop_table('artifact_dependencies')
    op.drop_index('idx_artifacts_version', table_name='artifacts')
    op.drop_index('idx_artifacts_type_status', table_name='artifacts')
    op.drop_table('artifacts')
    op.drop_index('idx_tasks_parent', table_name='tasks')
    op.drop_index('idx_tasks_created_at', table_name='tasks')
    op.drop_index('idx_tasks_priority', table_name='tasks')
    op.drop_index('idx_tasks_status', table_name='tasks')
    op.drop_table('tasks')

