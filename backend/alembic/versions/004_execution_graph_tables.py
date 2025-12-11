"""create execution graph tables

Revision ID: 004_execution_graph
Revises: 003
Create Date: 2025-12-11 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_execution_graph'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create execution_graphs
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.execution_graphs')")).scalar():
        op.create_table('execution_graphs',
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_execution_graphs_session", "execution_graphs", ["session_id"])

    # Create execution_nodes
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.execution_nodes')")).scalar():
        op.create_table('execution_nodes',
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("graph_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("chat_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["graph_id"], ["execution_graphs.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_execution_nodes_graph", "execution_nodes", ["graph_id"])
    op.create_index("idx_execution_nodes_chat_message", "execution_nodes", ["chat_message_id"])

    # Create execution_edges
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.execution_edges')")).scalar():
        op.create_table('execution_edges',
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("graph_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["graph_id"], ["execution_graphs.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_execution_edges_graph", "execution_edges", ["graph_id"])


def downgrade() -> None:
    op.drop_index("idx_execution_edges_graph", table_name="execution_edges")
    op.drop_table("execution_edges")
    op.drop_index("idx_execution_nodes_chat_message", table_name="execution_nodes")
    op.drop_index("idx_execution_nodes_graph", table_name="execution_nodes")
    op.drop_table("execution_nodes")
    op.drop_index("idx_execution_graphs_session", table_name="execution_graphs")
    op.drop_table("execution_graphs")


