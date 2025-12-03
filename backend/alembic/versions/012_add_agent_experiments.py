"""add agent experiments

Revision ID: 012
Revises: 011
Create Date: 2025-12-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_experiments table
    op.create_table(
        'agent_experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agent_a_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_b_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('traffic_split', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('metrics_to_track', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('primary_metric', sa.String(100), nullable=True),
        sa.Column('success_threshold', sa.Float(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('max_duration_hours', sa.Integer(), nullable=True),
        sa.Column('min_samples_per_variant', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('max_samples_per_variant', sa.Integer(), nullable=True),
        sa.Column('agent_a_samples', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agent_b_samples', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agent_a_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('agent_b_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_level', sa.Float(), nullable=True, server_default='0.95'),
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('is_significant', sa.Boolean(), nullable=True),
        sa.Column('winner', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['agent_a_id'], ['agents.id']),
        sa.ForeignKeyConstraint(['agent_b_id'], ['agents.id']),
        sa.ForeignKeyConstraint(['winner'], ['agents.id']),
        sa.CheckConstraint('traffic_split >= 0 AND traffic_split <= 1', name='experiments_traffic_split_check'),
        sa.CheckConstraint('confidence_level >= 0 AND confidence_level <= 1', name='experiments_confidence_check'),
        sa.CheckConstraint("status IN ('draft', 'running', 'paused', 'completed', 'cancelled')", name='experiments_status_check'),
    )
    
    # Create experiment_results table
    op.create_table(
        'experiment_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('variant', sa.String(1), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('task_description', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('custom_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['experiment_id'], ['agent_experiments.id']),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id']),
        sa.CheckConstraint("variant IN ('A', 'B')", name='results_variant_check'),
        sa.CheckConstraint('quality_score >= 0 AND quality_score <= 1', name='results_quality_check'),
    )
    
    # Create indexes
    op.create_index('ix_experiments_status', 'agent_experiments', ['status'])
    op.create_index('ix_experiments_agent_a', 'agent_experiments', ['agent_a_id'])
    op.create_index('ix_experiments_agent_b', 'agent_experiments', ['agent_b_id'])
    op.create_index('ix_experiments_created_at', 'agent_experiments', ['created_at'])
    op.create_index('ix_results_experiment', 'experiment_results', ['experiment_id'])
    op.create_index('ix_results_agent', 'experiment_results', ['agent_id'])
    op.create_index('ix_results_variant', 'experiment_results', ['variant'])
    op.create_index('ix_results_created_at', 'experiment_results', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_results_created_at', table_name='experiment_results')
    op.drop_index('ix_results_variant', table_name='experiment_results')
    op.drop_index('ix_results_agent', table_name='experiment_results')
    op.drop_index('ix_results_experiment', table_name='experiment_results')
    op.drop_index('ix_experiments_created_at', table_name='agent_experiments')
    op.drop_index('ix_experiments_agent_b', table_name='agent_experiments')
    op.drop_index('ix_experiments_agent_a', table_name='agent_experiments')
    op.drop_index('ix_experiments_status', table_name='agent_experiments')
    op.drop_table('experiment_results')
    op.drop_table('agent_experiments')

