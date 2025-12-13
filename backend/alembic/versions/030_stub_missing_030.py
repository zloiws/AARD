"""stub 030 to satisfy migration graph

Revision ID: 030
Revises: 028
Create Date: 2025-12-13 18:26:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '030'
down_revision: Union[str, None] = '028_add_agent_conversations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # stub: original migration missing after rollback; no-op
    pass


def downgrade() -> None:
    pass
