"""Initial unified schema migration (idempotent).

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-12-11 17:00:00
"""

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    conn = op.get_bind()
    # Use raw SQL with IF NOT EXISTS to make migration idempotent and safe for partial DBs.
    conn.execute(sa.text("""
    CREATE TABLE IF NOT EXISTS ollama_servers (
        id SERIAL PRIMARY KEY,
        url VARCHAR(255) UNIQUE,
        name VARCHAR(255),
        host VARCHAR(255),
        is_active BOOLEAN DEFAULT true,
        server_metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """))

    conn.execute(sa.text("""
    CREATE TABLE IF NOT EXISTS ollama_models (
        id SERIAL PRIMARY KEY,
        server_id INTEGER REFERENCES ollama_servers(id),
        model_name VARCHAR(255),
        name VARCHAR(255),
        is_active BOOLEAN DEFAULT true,
        details JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        UNIQUE (server_id, model_name)
    );
    """))

    conn.execute(sa.text("""
    CREATE TABLE IF NOT EXISTS agents (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """))

    conn.execute(sa.text("""
    CREATE TABLE IF NOT EXISTS tools (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """))

    conn.execute(sa.text("""
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255),
        status VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """))

    conn.execute(sa.text("""
    CREATE TABLE IF NOT EXISTS plans (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255),
        data JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """))

    conn.execute(sa.text("""
    CREATE TABLE IF NOT EXISTS workflow_events (
        id SERIAL PRIMARY KEY,
        plan_id INTEGER REFERENCES plans(id),
        event_type VARCHAR(255),
        payload JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """))


def downgrade() -> None:
    # Downgrade intentionally left blank for initial unified migration.
    pass


