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
    
    # Run alembic via subprocess
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parent,
        env=os.environ.copy()
    )
    sys.exit(result.returncode)

