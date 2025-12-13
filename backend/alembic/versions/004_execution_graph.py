\"\"\"stub 004_execution_graph to satisfy migration graph

Revision ID: 004_execution_graph
Revises: 003
Create Date: 2025-12-13 18:25:00.000000
\"\"\"
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_execution_graph'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # stub: original migration removed; no-op to preserve history
    pass


def downgrade() -> None:
    pass
\n*** End Patch

