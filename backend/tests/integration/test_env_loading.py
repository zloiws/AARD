"""Test environment loading"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
print(f"ENV_FILE: {ENV_FILE}")
print(f"Exists: {ENV_FILE.exists()}")

# Load manually
load_dotenv(ENV_FILE, override=True)

# Check all required vars
required_vars = [
    "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "OLLAMA_URL_1", "OLLAMA_MODEL_1", "OLLAMA_URL_2", "OLLAMA_MODEL_2",
    "SECRET_KEY"
]

print("\nChecking environment variables:")
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"  ✓ {var}={value[:20]}..." if len(value) > 20 else f"  ✓ {var}={value}")
    else:
        print(f"  ✗ {var} NOT FOUND")

# Now try Settings
print("\nTrying to load Settings...")
os.environ["POSTGRES_HOST"] = os.getenv("POSTGRES_HOST", "")
os.environ["POSTGRES_DB"] = os.getenv("POSTGRES_DB", "")
os.environ["POSTGRES_USER"] = os.getenv("POSTGRES_USER", "")
os.environ["POSTGRES_PASSWORD"] = os.getenv("POSTGRES_PASSWORD", "")
os.environ["OLLAMA_URL_1"] = os.getenv("OLLAMA_URL_1", "")
os.environ["OLLAMA_MODEL_1"] = os.getenv("OLLAMA_MODEL_1", "")
os.environ["OLLAMA_URL_2"] = os.getenv("OLLAMA_URL_2", "")
os.environ["OLLAMA_MODEL_2"] = os.getenv("OLLAMA_MODEL_2", "")
os.environ["SECRET_KEY"] = os.getenv("SECRET_KEY", "")

from app.core.config import get_settings
try:
    settings = get_settings()
    print("✓ Settings loaded!")
    print(f"  DB: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

