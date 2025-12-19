"""
Create an Alembic autogenerate revision and apply migrations.

Usage:
    python backend/scripts/autogen_and_apply_migration.py --message "add test_table"

This script:
 - loads environment variables from backend/.env (or project .env),
 - checks DB connectivity,
 - runs `alembic revision --autogenerate -m "{message}"`,
 - reports created revision file(s) under alembic/versions/,
 - runs `alembic upgrade head`.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path for app imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load env
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)


def _run_cmd(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, env=os.environ.copy())
    return proc.returncode


def main():
    parser = argparse.ArgumentParser(description="Autogen and apply Alembic migration")
    parser.add_argument("--message", "-m", default="autogen", help="Revision message")
    args = parser.parse_args()

    # Ensure alembic/versions exists
    versions_dir = BASE_DIR / "alembic" / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)

    # Check DB connectivity
    try:
        from app.core.config import get_settings
        from sqlalchemy import create_engine, text

        settings = get_settings()
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(
            "Database connectivity check failed. Ensure DB is reachable and env vars are set.\n"
            f"Error: {exc}\n"
        )
        sys.exit(2)

    # Record existing revision files
    before = set()
    if versions_dir.exists():
        before = set(p.name for p in versions_dir.iterdir() if p.is_file())

    # Run alembic revision --autogenerate
    backend_cwd = BASE_DIR
    msg = args.message
    # Prefer alembic.exe from venv Scripts on Windows if present, otherwise fall back to python -m alembic
    alembic_exe = BASE_DIR / "venv" / "Scripts" / "alembic.exe"
    if alembic_exe.exists():
        alembic_base = [str(alembic_exe)]
    else:
        alembic_base = [sys.executable, "-m", "alembic"]

    rev_cmd = alembic_base + ["revision", "--autogenerate", "-m", msg]
    rc = _run_cmd(rev_cmd, cwd=backend_cwd)
    if rc != 0:
        sys.stderr.write(f"Alembic revision command failed with exit code {rc}\n")
        sys.exit(rc)

    # Detect new files
    after = set(p.name for p in versions_dir.iterdir() if p.is_file())
    new_files = sorted(list(after - before))
    if not new_files:
        sys.stderr.write("No new revision file was created (autogenerate produced no changes).\n")
    else:
        sys.stdout.write("Created revision files:\n")
        for nf in new_files:
            sys.stdout.write(f" - alembic/versions/{nf}\n")

    # Apply migrations
    up_cmd = alembic_base + ["upgrade", "head"]
    rc = _run_cmd(up_cmd, cwd=backend_cwd)
    if rc != 0:
        sys.stderr.write(f"Alembic upgrade failed with exit code {rc}\n")
        sys.exit(rc)

    sys.stdout.write("Alembic autogen and upgrade completed successfully.\n")


if __name__ == "__main__":
    main()


