"""
Script to initialize Ollama servers in database from .env or manually
Run from backend directory: python init_servers.py
"""
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent
BASE_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from app.core.database import SessionLocal
from app.models.ollama_server import OllamaServer
from app.core.config import get_settings

def init_servers():
    """Initialize Ollama servers from .env configuration"""
    db = SessionLocal()
    
    try:
        settings = get_settings()
        
        # Check if servers already exist
        existing_count = db.query(OllamaServer).count()
        if existing_count > 0:
            print(f"Found {existing_count} existing servers in database. Skipping initialization.")
            print("Use API /api/servers to manage servers or delete existing ones first.")
            return
        
        print("Initializing Ollama servers from .env configuration...")
        
        # Server 1 from .env
        if hasattr(settings, 'ollama_url_1') and settings.ollama_url_1:
            url_1 = settings.ollama_url_1
            # Remove /v1 if present to get base URL
            if url_1.endswith("/v1"):
                url_1 = url_1[:-3]
            elif url_1.endswith("/v1/"):
                url_1 = url_1[:-4]
            
            server1 = OllamaServer(
                name="Server 1 - General/Reasoning",
                url=url_1,
                api_version="v1",
                capabilities=["general", "reasoning", "conversation"] if hasattr(settings, 'ollama_capabilities_1') else None,
                max_concurrent=getattr(settings, 'ollama_max_concurrent_1', 2),
                priority=1,
                is_default=True,
                is_active=True,
                description=f"Default server from .env configuration. Model: {getattr(settings, 'ollama_model_1', 'N/A')}"
            )
            db.add(server1)
            print(f"✓ Added server 1: {url_1}")
        
        # Server 2 from .env
        if hasattr(settings, 'ollama_url_2') and settings.ollama_url_2:
            url_2 = settings.ollama_url_2
            # Remove /v1 if present to get base URL
            if url_2.endswith("/v1"):
                url_2 = url_2[:-3]
            elif url_2.endswith("/v1/"):
                url_2 = url_2[:-4]
            
            server2 = OllamaServer(
                name="Server 2 - Coding",
                url=url_2,
                api_version="v1",
                capabilities=["coding", "code_generation"] if hasattr(settings, 'ollama_capabilities_2') else None,
                max_concurrent=getattr(settings, 'ollama_max_concurrent_2', 1),
                priority=0,
                is_default=False,
                is_active=True,
                description=f"Secondary server from .env configuration. Model: {getattr(settings, 'ollama_model_2', 'N/A')}"
            )
            db.add(server2)
            print(f"✓ Added server 2: {url_2}")
        
        db.commit()
        print("\n✓ Servers initialized successfully!")
        print("\nNext steps:")
        print("1. Discover models on servers: POST /api/servers/{server_id}/discover")
        print("2. List servers: GET /api/servers")
        print("3. Manage servers via API: /api/servers")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error initializing servers: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_servers()

