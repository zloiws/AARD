"""create minimal agents, tools, ollama and tasks tables

Revision ID: 032
Revises: 031
Create Date: 2025-12-11 18:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # agents table (minimal)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agents (
            id uuid PRIMARY KEY,
            name varchar(255) NOT NULL,
            status varchar(50),
            capabilities jsonb,
            created_at timestamptz DEFAULT now()
        );
        """
    )

    # tools table (minimal)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tools (
            id uuid PRIMARY KEY,
            name varchar(255) NOT NULL,
            description text,
            created_at timestamptz DEFAULT now()
        );
        """
    )

    # ollama_servers table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ollama_servers (
            id uuid PRIMARY KEY,
            name varchar(255),
            url varchar(1024),
            created_at timestamptz DEFAULT now()
        );
        """
    )

    # ollama_models table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ollama_models (
            id uuid PRIMARY KEY,
            server_id uuid REFERENCES ollama_servers(id) ON DELETE CASCADE,
            model_name varchar(255),
            created_at timestamptz DEFAULT now()
        );
        """
    )

    # tasks table (if not exists)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id uuid PRIMARY KEY,
            description text NOT NULL,
            status varchar(50),
            autonomy_level integer DEFAULT 2,
            context jsonb,
            created_at timestamptz DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks;")
    op.execute("DROP TABLE IF EXISTS ollama_models;")
    op.execute("DROP TABLE IF EXISTS ollama_servers;")
    op.execute("DROP TABLE IF EXISTS tools;")
    op.execute("DROP TABLE IF EXISTS agents;")


