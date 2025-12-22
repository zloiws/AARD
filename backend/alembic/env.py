"""
Alembic environment configuration
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

# Load environment variables BEFORE importing app modules
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

from urllib.parse import urlparse, urlunparse

from alembic import context
from app.core.config import get_settings
# Import Base and models for autogenerate
from app.core.database import Base
from app.models import *  # noqa: F401, F403 - Import all models
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object
config = context.config
# Override sqlalchemy.url from config if not set in alembic.ini
def _mask_database_url(url: str) -> str:
    """Mask password in a database URL for safe logging."""
    try:
        p = urlparse(url)
        if p.username:
            netloc = p.hostname or ""
            if p.username:
                netloc = f"{p.username}:***@{netloc}"
            if p.port:
                netloc = f"{netloc}:{p.port}"
            return urlunparse((p.scheme, netloc, p.path or "", p.params or "", p.query or "", p.fragment or ""))
    except Exception:
        return url
    return url

try:
    settings = get_settings()
except Exception as exc:  # pragma: no cover - helpful runtime error path
    msg = (
        "Failed to load application settings required by Alembic.\n"
        "Common causes:\n"
        "- Missing or mislocated `.env` file (expected at project root or `backend/.env`).\n"
        "- Required POSTGRES_* environment variables not set (see `backend/app/core/config.py`).\n\n"
        f"Original error: {exc}\n"
    )
    sys.stderr.write(msg)
    raise

config.set_main_option("sqlalchemy.url", settings.database_url)
try:
    # Log the DB URL used by Alembic (mask password)
    masked = _mask_database_url(settings.database_url)
    sys.stderr.write(f"Alembic will use database URL: {masked}\n")
except Exception:
    # Best-effort logging; do not fail migrations because of logging
    pass

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

