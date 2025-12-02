"""Fix .env loading"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get project root
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

print(f"Looking for .env at: {ENV_FILE}")
print(f"Exists: {ENV_FILE.exists()}")

if ENV_FILE.exists():
    # Load with override
    load_dotenv(ENV_FILE, override=True)
    print("\n✅ .env loaded")
    
    # Check variables
    required_vars = [
        "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
        "OLLAMA_URL_1", "OLLAMA_MODEL_1", "OLLAMA_URL_2", "OLLAMA_MODEL_2",
        "SECRET_KEY"
    ]
    
    print("\nChecking variables:")
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var} = {value[:30]}..." if len(value) > 30 else f"  ✅ {var} = {value}")
        else:
            print(f"  ❌ {var} = NOT FOUND")
            missing.append(var)
    
    if missing:
        print(f"\n❌ Missing variables: {missing}")
        sys.exit(1)
    else:
        print("\n✅ All required variables found!")
        
        # Test Settings
        print("\nTesting Settings...")
        try:
            from app.core.config import get_settings
            settings = get_settings()
            print("✅ Settings loaded successfully!")
            print(f"   DB: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
            print(f"   Ollama 1: {settings.ollama_url_1}")
            print(f"   Ollama 2: {settings.ollama_url_2}")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Settings failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
else:
    print(f"❌ .env file not found at {ENV_FILE}")
    print("\nPlease create .env file with required variables.")
    sys.exit(1)

