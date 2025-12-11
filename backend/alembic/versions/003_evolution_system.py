"""add evolution system tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create prompts table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.prompts')")).scalar():
        op.create_table('prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('prompt_type', sa.String(50), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('parent_prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_execution_time', sa.Float(), nullable=True),
        sa.Column('user_rating', sa.Float(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('last_improved_at', sa.DateTime(), nullable=True),
        sa.Column('improvement_history', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['parent_prompt_id'], ['prompts.id'], ),
        sa.CheckConstraint("prompt_type IN ('system', 'agent', 'tool', 'meta', 'context')", name='prompts_type_check'),
        sa.CheckConstraint("status IN ('active', 'deprecated', 'testing')", name='prompts_status_check'),
        sa.CheckConstraint('level >= 0 AND level <= 4', name='prompts_level_check'),
    )
    
    # Create indexes for prompts
    op.create_index('idx_prompts_type', 'prompts', ['prompt_type'])
    op.create_index('idx_prompts_status', 'prompts', ['status'])
    op.create_index('idx_prompts_level', 'prompts', ['level'])
    op.create_index('idx_prompts_parent', 'prompts', ['parent_prompt_id'])
    op.create_index('idx_prompts_name', 'prompts', ['name'])
    
    # Create approval_requests table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.approval_requests')")).scalar():
        op.create_table('approval_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('request_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('risk_assessment', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('required_action', sa.String(20), nullable=True),
        sa.Column('human_feedback', sa.Text(), nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('decision_timeout', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.CheckConstraint("request_type IN ('new_artifact', 'artifact_update', 'prompt_change', 'execution_step', 'plan_approval')", name='approval_requests_type_check'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'modified')", name='approval_requests_status_check'),
    )
    
    # Create indexes for approval_requests
    op.create_index('idx_approval_requests_status', 'approval_requests', ['status'])
    op.create_index('idx_approval_requests_type', 'approval_requests', ['request_type'])
    op.create_index('idx_approval_requests_artifact', 'approval_requests', ['artifact_id'])
    op.create_index('idx_approval_requests_prompt', 'approval_requests', ['prompt_id'])
    op.create_index('idx_approval_requests_task', 'approval_requests', ['task_id'])
    op.create_index('idx_approval_requests_created', 'approval_requests', ['created_at'])
    
    # Create evolution_history table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.evolution_history')")).scalar():
        op.create_table('evolution_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('change_type', sa.String(50), nullable=True),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.Column('before_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('after_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('trigger_type', sa.String(50), nullable=True),
        sa.Column('trigger_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('improvement_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("entity_type IN ('artifact', 'prompt', 'agent_behavior', 'tool_behavior', 'task', 'plan')", name='evolution_history_entity_type_check'),
        sa.CheckConstraint("change_type IN ('created', 'updated', 'improved', 'deprecated', 'optimized')", name='evolution_history_change_type_check'),
    )
    
    # Create indexes for evolution_history
    op.create_index('idx_evolution_entity', 'evolution_history', ['entity_type', 'entity_id'])
    op.create_index('idx_evolution_change_type', 'evolution_history', ['change_type'])
    op.create_index('idx_evolution_trigger', 'evolution_history', ['trigger_type'])
    op.create_index('idx_evolution_created', 'evolution_history', ['created_at'])
    op.create_index('idx_evolution_success', 'evolution_history', ['success'])
    
    # Create feedback table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.feedback')")).scalar():
        op.create_table('feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('insights_extracted', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.CheckConstraint("entity_type IN ('artifact', 'prompt', 'agent', 'tool', 'task', 'plan')", name='feedback_entity_type_check'),
        sa.CheckConstraint("feedback_type IN ('explicit', 'implicit', 'contextual')", name='feedback_feedback_type_check'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='feedback_rating_check'),
    )
    
    # Create indexes for feedback
    op.create_index('idx_feedback_entity', 'feedback', ['entity_type', 'entity_id'])
    op.create_index('idx_feedback_type', 'feedback', ['feedback_type'])
    op.create_index('idx_feedback_processed', 'feedback', ['processed'])
    op.create_index('idx_feedback_task', 'feedback', ['task_id'])
    op.create_index('idx_feedback_created', 'feedback', ['created_at'])
    
    # Create plans table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.plans')")).scalar():
        op.create_table('plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('goal', sa.Text(), nullable=False),
        sa.Column('strategy', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('steps', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('alternatives', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_duration', sa.Integer(), nullable=True),
        sa.Column('actual_duration', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('draft', 'approved', 'executing', 'completed', 'failed', 'cancelled')", name='plans_status_check'),
    )
    
    # Create indexes for plans
    op.create_index('idx_plans_task', 'plans', ['task_id'])
    op.create_index('idx_plans_status', 'plans', ['status'])
    op.create_index('idx_plans_version', 'plans', ['task_id', 'version'])
    
    # Update tasks table to reference plans (add foreign key if not exists)
    # Note: plan_id column already exists from migration 001


def downgrade() -> None:
    op.drop_index('idx_plans_version', table_name='plans')
    op.drop_index('idx_plans_status', table_name='plans')
    op.drop_index('idx_plans_task', table_name='plans')
    op.drop_table('plans')
    op.drop_index('idx_feedback_created', table_name='feedback')
    op.drop_index('idx_feedback_task', table_name='feedback')
    op.drop_index('idx_feedback_processed', table_name='feedback')
    op.drop_index('idx_feedback_type', table_name='feedback')
    op.drop_index('idx_feedback_entity', table_name='feedback')
    op.drop_table('feedback')
    op.drop_index('idx_evolution_success', table_name='evolution_history')
    op.drop_index('idx_evolution_created', table_name='evolution_history')
    op.drop_index('idx_evolution_trigger', table_name='evolution_history')
    op.drop_index('idx_evolution_change_type', table_name='evolution_history')
    op.drop_index('idx_evolution_entity', table_name='evolution_history')
    op.drop_table('evolution_history')
    op.drop_index('idx_approval_requests_created', table_name='approval_requests')
    op.drop_index('idx_approval_requests_task', table_name='approval_requests')
    op.drop_index('idx_approval_requests_prompt', table_name='approval_requests')
    op.drop_index('idx_approval_requests_artifact', table_name='approval_requests')
    op.drop_index('idx_approval_requests_type', table_name='approval_requests')
    op.drop_index('idx_approval_requests_status', table_name='approval_requests')
    op.drop_table('approval_requests')
    op.drop_index('idx_prompts_name', table_name='prompts')
    op.drop_index('idx_prompts_parent', table_name='prompts')
    op.drop_index('idx_prompts_level', table_name='prompts')
    op.drop_index('idx_prompts_status', table_name='prompts')
    op.drop_index('idx_prompts_type', table_name='prompts')
    op.drop_table('prompts')

