"""merge all heads

Revision ID: d14b5839b85c
Revises: 001_initial_schema, 004_execution_graph, 029, 030, 036
Create Date: 2025-12-14 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd14b5839b85c'
down_revision: Union[str, None] = ('001_initial_schema', '004_execution_graph', '029', '016', '036')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
