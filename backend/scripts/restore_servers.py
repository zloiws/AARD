"""
Restore Ollama servers from .env configuration
Run this after clearing database to restore servers
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from pathlib import Path as PathLib

# Load .env
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import SessionLocal
from app.models.ollama_server import OllamaServer
from app.core.config import get_settings

def restore_servers():
    """Restore Ollama servers from .env configuration"""
    print("=" * 70)
    print(" Restoring Ollama Servers")
    print("=" * 70 + "\n")
    
    db = SessionLocal()
    
    try:
        settings = get_settings()
        
        # Delete existing servers first (in case of re-run)
        existing_servers = db.query(OllamaServer).all()
        if existing_servers:
            print(f"Removing {len(existing_servers)} existing servers...")
            for server in existing_servers:
                db.delete(server)
            db.commit()
            print("✅ Existing servers removed\n")
        
        print("Creating servers from .env configuration...\n")
        servers_created = 0
        
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
                capabilities=["general", "reasoning", "conversation"],
                max_concurrent=getattr(settings, 'ollama_max_concurrent_1', 2),
                priority=1,
                is_default=True,
                is_active=True,
                description=f"Default server from .env configuration. Model: {getattr(settings, 'ollama_model_1', 'N/A')}"
            )
            db.add(server1)
            servers_created += 1
            print(f"✅ Added server 1: {server1.name} at {url_1}")
        
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
                capabilities=["coding", "code_generation"],
                max_concurrent=getattr(settings, 'ollama_max_concurrent_2', 1),
                priority=0,
                is_default=False,
                is_active=True,
                description=f"Secondary server from .env configuration. Model: {getattr(settings, 'ollama_model_2', 'N/A')}"
            )
            db.add(server2)
            servers_created += 1
            print(f"✅ Added server 2: {server2.name} at {url_2}")
        
        db.commit()
        
        print("\n" + "=" * 70)
        print(f" ✅ Successfully restored {servers_created} server(s)!")
        print("=" * 70 + "\n")
        
        if servers_created == 0:
            print("⚠️  No servers found in .env configuration.")
            print("   Make sure OLLAMA_URL_1 and/or OLLAMA_URL_2 are set in .env file.\n")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error restoring servers: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = restore_servers()
    sys.exit(0 if success else 1)

