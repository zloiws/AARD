"""Test configuration loading"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
print(f"ENV_FILE path: {ENV_FILE}")
print(f"Exists: {ENV_FILE.exists()}")

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"POSTGRES_HOST={os.getenv('POSTGRES_HOST')}")
    print(f"POSTGRES_DB={os.getenv('POSTGRES_DB')}")
    print(f"POSTGRES_USER={os.getenv('POSTGRES_USER')}")
    print(f"OLLAMA_URL_1={os.getenv('OLLAMA_URL_1')}")
    print(f"OLLAMA_MODEL_1={os.getenv('OLLAMA_MODEL_1')}")
else:
    print("ERROR: .env file not found!")

# Test settings
try:
    from app.core.config import get_settings
    settings = get_settings()
    print(f"\n✓ Settings loaded successfully!")
    print(f"DB Host: {settings.postgres_host}")
    print(f"DB Name: {settings.postgres_db}")
    print(f"Ollama 1: {settings.ollama_url_1}")
    print(f"Ollama 2: {settings.ollama_url_2}")
except Exception as e:
    print(f"\n✗ Error loading settings: {e}")
    import traceback
    traceback.print_exc()

