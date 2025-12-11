"""add plan_id to approval_requests

Revision ID: 004
Revises: 003
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add plan_id column to approval_requests
    op.add_column(
        'approval_requests',
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_approval_requests_plan_id',
        'approval_requests',
        'plans',
        ['plan_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index for plan_id
    op.execute("CREATE INDEX IF NOT EXISTS idx_approval_requests_plan ON approval_requests (plan_id);")


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_approval_requests_plan', table_name='approval_requests')
    
    # Drop foreign key
    op.drop_constraint('fk_approval_requests_plan_id', 'approval_requests', type_='foreignkey')
    
    # Drop column
    op.drop_column('approval_requests', 'plan_id')

