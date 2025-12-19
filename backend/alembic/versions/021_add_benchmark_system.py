"""add benchmark system tables

Revision ID: 021_add_benchmark_system
Revises: 020_add_workflow_events
Create Date: 2025-12-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '021_add_benchmark_system'
down_revision = '020_add_workflow_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create benchmark_tasks table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.benchmark_tasks')")).scalar():
        op.create_table('benchmark_tasks',
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
    op.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_tasks_task_type ON benchmark_tasks (task_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_tasks_category ON benchmark_tasks (category);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_benchmark_tasks_name ON benchmark_tasks (name);")
    
    # Create benchmark_results table
    # First create table without foreign keys to ollama tables (they may not exist)
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.benchmark_results')")).scalar():
        op.create_table('benchmark_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('benchmark_task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['benchmark_task_id'], ['benchmark_tasks.id'], ondelete='CASCADE'),
    )
    
    # Add foreign keys to ollama tables only if they exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'ollama_models' in existing_tables:
        op.create_foreign_key(
            'fk_benchmark_results_model',
            'benchmark_results', 'ollama_models',
            ['model_id'], ['id'],
            ondelete='SET NULL'
        )
    
    if 'ollama_servers' in existing_tables:
        op.create_foreign_key(
            'fk_benchmark_results_server',
            'benchmark_results', 'ollama_servers',
            ['server_id'], ['id'],
            ondelete='SET NULL'
        )
    
    # Create indexes for benchmark_results
    op.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_results_task_id ON benchmark_results (benchmark_task_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_results_model_id ON benchmark_results (model_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_results_server_id ON benchmark_results (server_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_results_created_at ON benchmark_results (created_at);")


def downgrade() -> None:
    # Drop foreign keys if they exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    try:
        op.drop_constraint('fk_benchmark_results_server', 'benchmark_results', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint('fk_benchmark_results_model', 'benchmark_results', type_='foreignkey')
    except:
        pass
    
    # Drop benchmark_results indexes
    op.drop_index('idx_benchmark_results_created_at', table_name='benchmark_results')
    op.drop_index('idx_benchmark_results_server_id', table_name='benchmark_results')
    op.drop_index('idx_benchmark_results_model_id', table_name='benchmark_results')
    op.drop_index('idx_benchmark_results_task_id', table_name='benchmark_results')
    
    # Drop benchmark_results table
    op.drop_table('benchmark_results')
    
    # Drop benchmark_tasks indexes
    op.drop_index('idx_benchmark_tasks_name', table_name='benchmark_tasks')
    op.drop_index('idx_benchmark_tasks_category', table_name='benchmark_tasks')
    op.drop_index('idx_benchmark_tasks_task_type', table_name='benchmark_tasks')
    
    # Drop benchmark_tasks table
    op.drop_table('benchmark_tasks')

