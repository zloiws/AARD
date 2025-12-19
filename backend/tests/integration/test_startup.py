"""Test server startup"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env first
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
print(f"Loading .env from: {ENV_FILE}")
print(f"Exists: {ENV_FILE.exists()}")

if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)
    print("✅ .env loaded")
else:
    print("❌ .env not found!")
    sys.exit(1)

# Check variables
print("\nChecking variables:")
for var in ["POSTGRES_HOST", "SECRET_KEY", "OLLAMA_URL_1"]:
    value = os.getenv(var)
    print(f"  {var}: {'✅' if value else '❌'} {value[:30] if value else 'NOT FOUND'}")

# Now test imports
print("\nTesting imports...")
try:
    from app.core.config import get_settings
    settings = get_settings()
    print("✅ Settings loaded")
    print(f"   DB: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
except Exception as e:
    print(f"❌ Settings failed: {e}")
    sys.exit(1)

try:
    from app.core.database import Base, get_db
    print("✅ Database module imported")
except Exception as e:
    print(f"❌ Database import failed: {e}")
    sys.exit(1)

try:
    from app.api.routes import approvals, artifacts, prompts
    print("✅ API routes imported")
except Exception as e:
    print(f"❌ Routes import failed: {e}")
    sys.exit(1)

try:
    # main.py is in backend/, not app/
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import main
    print("✅ Main app imported")
    print("\n🎉 All imports successful! Server should start now.")
    print("\n💡 To start server, run:")
    print("   cd backend")
    print("   python main.py")
except Exception as e:
    print(f"❌ Main app import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

