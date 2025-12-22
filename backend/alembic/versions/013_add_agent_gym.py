"""Add agent gym tables (tests and benchmarks)

Revision ID: 013_add_agent_gym
Revises: 012_add_agent_experiments
Create Date: 2025-12-03 15:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_add_agent_gym'
down_revision = '012_add_agent_experiments'
branch_labels = None
depends_on = None


def upgrade():
    # Create agent_tests table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.agent_tests')")).scalar():
        op.create_table('agent_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('test_type', sa.String(50), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('input_data', postgresql.JSONB(), nullable=True),
        sa.Column('expected_output', postgresql.JSONB(), nullable=True),
        sa.Column('validation_rules', postgresql.JSONB(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('required_tools', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_tests_agent_id ON agent_tests (agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_tests_test_type ON agent_tests (test_type);")
    
    # Create agent_test_runs table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.agent_test_runs')")).scalar():
        op.create_table('agent_test_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('test_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_version', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('input_data', postgresql.JSONB(), nullable=True),
        sa.Column('output_data', postgresql.JSONB(), nullable=True),
        sa.Column('expected_output', postgresql.JSONB(), nullable=True),
        sa.Column('validation_passed', sa.String(10), nullable=True),
        sa.Column('validation_details', postgresql.JSONB(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('llm_calls', sa.Integer(), nullable=True),
        sa.Column('tool_calls', sa.Integer(), nullable=True),
        sa.Column('memory_usage_mb', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(255), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('run_by', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['test_id'], ['agent_tests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_test_runs_test_id ON agent_test_runs (test_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_test_runs_agent_id ON agent_test_runs (agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_test_runs_status ON agent_test_runs (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_test_runs_started_at ON agent_test_runs (started_at);")
    
    # Create agent_benchmarks table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.agent_benchmarks')")).scalar():
        op.create_table('agent_benchmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('benchmark_type', sa.String(50), nullable=False),
        sa.Column('agent_ids', postgresql.JSONB(), nullable=False),
        sa.Column('tasks', postgresql.JSONB(), nullable=False),
        sa.Column('iterations', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('parallel_execution', sa.String(10), nullable=False, server_default='false'),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_benchmarks_benchmark_type ON agent_benchmarks (benchmark_type);")
    
    # Create agent_benchmark_runs table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.agent_benchmark_runs')")).scalar():
        op.create_table('agent_benchmark_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('benchmark_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('agent_results', postgresql.JSONB(), nullable=False),
        sa.Column('summary', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(255), nullable=True),
        sa.Column('run_by', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['benchmark_id'], ['agent_benchmarks.id'], ondelete='CASCADE'),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_benchmark_runs_benchmark_id ON agent_benchmark_runs (benchmark_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_benchmark_runs_status ON agent_benchmark_runs (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_benchmark_runs_started_at ON agent_benchmark_runs (started_at);")


def downgrade():
    op.drop_index('ix_agent_benchmark_runs_started_at', table_name='agent_benchmark_runs')
    op.drop_index('ix_agent_benchmark_runs_status', table_name='agent_benchmark_runs')
    op.drop_index('ix_agent_benchmark_runs_benchmark_id', table_name='agent_benchmark_runs')
    op.drop_table('agent_benchmark_runs')
    
    op.drop_index('ix_agent_benchmarks_benchmark_type', table_name='agent_benchmarks')
    op.drop_table('agent_benchmarks')
    
    op.drop_index('ix_agent_test_runs_started_at', table_name='agent_test_runs')
    op.drop_index('ix_agent_test_runs_status', table_name='agent_test_runs')
    op.drop_index('ix_agent_test_runs_agent_id', table_name='agent_test_runs')
    op.drop_index('ix_agent_test_runs_test_id', table_name='agent_test_runs')
    op.drop_table('agent_test_runs')
    
    op.drop_index('ix_agent_tests_test_type', table_name='agent_tests')
    op.drop_index('ix_agent_tests_agent_id', table_name='agent_tests')
    op.drop_table('agent_tests')

