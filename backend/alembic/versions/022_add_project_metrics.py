"""add project metrics table

Revision ID: 022_add_project_metrics
Revises: 021_add_benchmark_system
Create Date: 2025-12-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = '022_add_project_metrics'
down_revision: Union[str, None] = '021_add_benchmark_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create project_metrics table
    op.create_table(
        'project_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('metric_type', sa.Enum('PERFORMANCE', 'TASK_SUCCESS', 'EXECUTION_TIME', 'TASK_DISTRIBUTION', 'TREND', 'AGGREGATE', name='metrictype'), nullable=False),
        sa.Column('metric_name', sa.String(length=255), nullable=False),
        sa.Column('period', sa.Enum('HOUR', 'DAY', 'WEEK', 'MONTH', name='metricperiod'), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('sum_value', sa.Float(), nullable=True),
        sa.Column('metric_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_project_metrics_metric_type', 'project_metrics', ['metric_type'])
    op.create_index('ix_project_metrics_metric_name', 'project_metrics', ['metric_name'])
    op.create_index('ix_project_metrics_period', 'project_metrics', ['period'])
    op.create_index('ix_project_metrics_period_start', 'project_metrics', ['period_start'])
    op.create_index('idx_project_metrics_type_name_period', 'project_metrics', ['metric_type', 'metric_name', 'period'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_project_metrics_type_name_period', table_name='project_metrics')
    op.drop_index('ix_project_metrics_period_start', table_name='project_metrics')
    op.drop_index('ix_project_metrics_period', table_name='project_metrics')
    op.drop_index('ix_project_metrics_metric_name', table_name='project_metrics')
    op.drop_index('ix_project_metrics_metric_type', table_name='project_metrics')
    
    # Drop table
    op.drop_table('project_metrics')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS metricperiod")
    op.execute("DROP TYPE IF EXISTS metrictype")

