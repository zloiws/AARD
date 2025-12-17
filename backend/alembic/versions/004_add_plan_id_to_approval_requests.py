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
    # Add plan_id column to approval_requests if not exists (idempotent)
    op.execute("ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS plan_id UUID;")

    # Add foreign key constraint if not exists
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'fk_approval_requests_plan_id'
        ) THEN
            ALTER TABLE approval_requests
            ADD CONSTRAINT fk_approval_requests_plan_id FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE;
        END IF;
    END$$;
    """)

    # Create index for plan_id if not exists
    op.execute("CREATE INDEX IF NOT EXISTS idx_approval_requests_plan ON approval_requests (plan_id);")


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_approval_requests_plan', table_name='approval_requests')
    
    # Drop foreign key
    op.drop_constraint('fk_approval_requests_plan_id', 'approval_requests', type_='foreignkey')
    
    # Drop column
    op.drop_column('approval_requests', 'plan_id')

