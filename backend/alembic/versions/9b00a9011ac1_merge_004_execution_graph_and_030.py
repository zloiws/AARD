"""merge 004_execution_graph and 030

Revision ID: 9b00a9011ac1
Revises: 004_execution_graph, 030
Create Date: 2025-12-11 17:45:40.369679

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9b00a9011ac1'
down_revision: Union[str, None] = ('004_execution_graph', '016')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

