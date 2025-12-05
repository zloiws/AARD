"""
Update Alembic migration state to match current database state
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

# Import Alembic
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

print("=" * 70)
print(" Updating Migration State")
print("=" * 70)

# Get database URL
db_url = os.getenv("DATABASE_URL")
if not db_url:
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "aard")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Check current revision
engine = create_engine(db_url)
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current_rev = result.scalar()
        print(f"\nCurrent revision: {current_rev}")
except Exception as e:
    print(f"\n⚠️  Could not read current revision: {e}")
    current_rev = None

# Get latest revision from migrations
alembic_cfg = Config("alembic.ini")

# Get head revision
try:
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(alembic_cfg)
    head_rev = script.get_current_head()
    print(f"Head revision: {head_rev}")
except Exception as e:
    print(f"⚠️  Could not determine head revision: {e}")
    head_rev = "023_add_audit_reports"  # Latest known revision

if current_rev != head_rev:
    print(f"\n⚠️  Migration state ({current_rev}) does not match head ({head_rev})")
    print("   Updating migration state to head...")
    
    try:
        command.stamp(alembic_cfg, head_rev)
        print(f"✅ Migration state updated to {head_rev}")
    except Exception as e:
        print(f"❌ Failed to update migration state: {e}")
        sys.exit(1)
else:
    print(f"\n✅ Migration state is already at head ({head_rev})")

print("\n" + "=" * 70)

