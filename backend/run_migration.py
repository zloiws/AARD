"""Run Alembic migrations with proper environment loading"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables
from dotenv import load_dotenv
env_file = BASE_DIR / ".env"
load_dotenv(env_file, override=True)

# Set working directory to backend
os.chdir(Path(__file__).resolve().parent)

if __name__ == "__main__":
    import subprocess
    import sys
    from sqlalchemy import create_engine
    from sqlalchemy.exc import SQLAlchemyError

    # Before running Alembic, verify we can connect to the database.
    try:
        from app.core.config import get_settings

        settings = get_settings()
        engine = create_engine(settings.database_url)
        # Try a short-lived connection
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - runtime check
        sys.stderr.write(
            "Database connectivity check failed before running Alembic migrations.\n"
            "Please verify your database is reachable and environment variables are set.\n"
            f"Error: {exc}\n"
        )
        sys.exit(2)

    # Run alembic via subprocess
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parent,
        env=os.environ.copy()
    )
    sys.exit(result.returncode)

