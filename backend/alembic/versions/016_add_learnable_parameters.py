"""Add system_parameters and uncertainty_parameters tables

Revision ID: 016_add_learnable_parameters
Revises: 015_add_system_settings
Create Date: 2025-12-10 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016_add_learnable_parameters'
down_revision = '015_add_system_settings'
branch_labels = None
depends_on = None


def upgrade():
    # Create uncertainty_parameters table
    op.create_table(
        'uncertainty_parameters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('parameter_name', sa.String(255), nullable=False, unique=True),
        sa.Column('parameter_type', sa.Enum('weight', 'threshold', 'keyword_list', 'count_threshold', 'similarity_threshold', name='parametertype'), nullable=False),
        sa.Column('numeric_value', sa.Float(), nullable=True),
        sa.Column('text_value', sa.Text(), nullable=True),
        sa.Column('json_value', postgresql.JSONB(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('learning_history', postgresql.JSONB(), nullable=True),
        sa.Column('performance_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('last_improved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('improvement_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
    )
    op.create_index('ix_uncertainty_parameters_parameter_name', 'uncertainty_parameters', ['parameter_name'], unique=True)
    
    # Create system_parameters table
    op.create_table(
        'system_parameters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('parameter_name', sa.String(255), nullable=False),
        sa.Column('category', sa.Enum('uncertainty', 'approval', 'critic', 'conflict_resolution', 'quota', 'planning', 'memory', 'execution', 'meta_learning', name='parametercategory'), nullable=False),
        sa.Column('parameter_type', sa.Enum('weight', 'threshold', 'keyword_list', 'count_threshold', 'similarity_threshold', 'penalty', 'bonus', name='systemparametertype'), nullable=False),
        sa.Column('numeric_value', sa.Float(), nullable=True),
        sa.Column('text_value', sa.Text(), nullable=True),
        sa.Column('json_value', postgresql.JSONB(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('learning_history', postgresql.JSONB(), nullable=True),
        sa.Column('performance_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('last_improved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('improvement_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('ix_system_parameters_parameter_name', 'system_parameters', ['parameter_name'], unique=True)
    op.create_index('ix_system_parameters_category', 'system_parameters', ['category'])


def downgrade():
    op.drop_index('ix_system_parameters_category', table_name='system_parameters')
    op.drop_index('ix_system_parameters_parameter_name', table_name='system_parameters')
    op.drop_table('system_parameters')
    op.drop_index('ix_uncertainty_parameters_parameter_name', table_name='uncertainty_parameters')
    op.drop_table('uncertainty_parameters')

