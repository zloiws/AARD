\"\"\"add execution graph tables (idempotent)

Revision ID: 036
Revises: 035_enrich_agents_table_with_model_columns
Create Date: 2025-12-13 18:20:00.000000
\"\"\"
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '036'
down_revision: Union[str, None] = '035_enrich_agents_table_with_model_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use idempotent SQL to create tables if they do not exist
    op.execute(
        \"\"\"CREATE TABLE IF NOT EXISTS execution_graphs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID,
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL
        );\"\"\"
    )

    op.execute(
        \"\"\"CREATE TABLE IF NOT EXISTS execution_nodes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            graph_id UUID REFERENCES execution_graphs(id) ON DELETE CASCADE,
            node_type VARCHAR(100),
            payload JSONB,
            status VARCHAR(50),
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL
        );\"\"\"
    )

    op.execute(
        \"\"\"CREATE TABLE IF NOT EXISTS execution_edges (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            graph_id UUID REFERENCES execution_graphs(id) ON DELETE CASCADE,
            from_node UUID REFERENCES execution_nodes(id) ON DELETE CASCADE,
            to_node UUID REFERENCES execution_nodes(id) ON DELETE CASCADE,
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL
        );\"\"\"
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_execution_nodes_graph_id ON execution_nodes(graph_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_execution_edges_graph_id ON execution_edges(graph_id);")


def downgrade() -> None:
    # Downgrade by dropping tables if they exist
    op.execute("DROP TABLE IF EXISTS execution_edges CASCADE;")
    op.execute("DROP TABLE IF EXISTS execution_nodes CASCADE;")
    op.execute("DROP TABLE IF EXISTS execution_graphs CASCADE;")


