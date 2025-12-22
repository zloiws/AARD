"""merge multiple recent heads

Revision ID: 20251217_merge_heads_custom
Revises: 20251216_event_assignment_enrich, 20251216_plan_hypotheses, d14b5839b85c
Create Date: 2025-12-17 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20251217_merge_heads_custom'
down_revision: Union[str, None] = ('20251216_event_assignment_enrich', '20251216_plan_hypotheses', 'd14b5839b85c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge migration - no schema changes, marks multiple heads as merged.
    pass


def downgrade() -> None:
    # No-op
    pass


