"""add audit reports table

Revision ID: 023_add_audit_reports
Revises: 022_add_project_metrics
Create Date: 2025-12-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = '023_add_audit_reports'
down_revision: Union[str, None] = '022_add_project_metrics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_reports table
    op.create_table(
        'audit_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('audit_type', sa.Enum('PERFORMANCE', 'QUALITY', 'PROMPTS', 'ERRORS', 'FULL', name='audittype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='auditstatus'), nullable=False, server_default='PENDING'),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('findings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('trends', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('audit_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_audit_reports_audit_type', 'audit_reports', ['audit_type'])
    op.create_index('ix_audit_reports_status', 'audit_reports', ['status'])
    op.create_index('ix_audit_reports_period_start', 'audit_reports', ['period_start'])
    op.create_index('ix_audit_reports_created_at', 'audit_reports', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_reports_created_at', table_name='audit_reports')
    op.drop_index('ix_audit_reports_period_start', table_name='audit_reports')
    op.drop_index('ix_audit_reports_status', table_name='audit_reports')
    op.drop_index('ix_audit_reports_audit_type', table_name='audit_reports')
    
    # Drop table
    op.drop_table('audit_reports')

