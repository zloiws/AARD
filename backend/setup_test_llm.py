"""Setup test LLM server for prompt testing"""
import os
import sys
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.ollama_server import OllamaServer
from app.models.ollama_model import OllamaModel
from app.services.ollama_service import OllamaService
from datetime import datetime

def setup_test_server():
    """Setup test Ollama server"""
    print("=== Setting up Test LLM Server ===\n")
    db: Session = SessionLocal()
    try:
        # Check existing servers
        existing = db.query(OllamaServer).filter(OllamaServer.is_active == True).all()
        print(f"Existing active servers: {len(existing)}")
        
        if existing:
            print("\nActive servers:")
            for server in existing:
                print(f"  - {server.name} ({server.url})")
                models = OllamaService.get_models_for_server(db, str(server.id))
                print(f"    Models: {len(models)}")
                for model in models[:3]:
                    print(f"      * {model.model_name}")
            return existing[0]
        
        # Try to get server from environment
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        print(f"\nNo servers found. Checking environment...")
        print(f"OLLAMA_BASE_URL: {ollama_url}")
        
        # Ask user
        print("\nTo test with LLM, you need to:")
        print("1. Have Ollama server running")
        print("2. Add server via web interface (Settings -> Ollama Servers)")
        print("3. Or provide server URL here")
        
        server_url = input("\nEnter Ollama server URL (or press Enter to skip): ").strip()
        if not server_url:
            print("Skipping LLM setup. Tests will run without LLM.")
            return None
        
        # Create test server
        print(f"\nCreating test server: {server_url}")
        server = OllamaServer(
            name="Test Server",
            url=server_url,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(server)
        db.commit()
        db.refresh(server)
        
        print(f"✓ Server created: {server.id}")
        
        # Try to sync models
        print("\nSyncing models...")
        try:
            OllamaService.sync_models_for_server(db, str(server.id))
            models = OllamaService.get_models_for_server(db, str(server.id))
            print(f"✓ Found {len(models)} models")
            for model in models[:5]:
                print(f"  - {model.model_name}")
        except Exception as e:
            print(f"⚠ Error syncing models: {e}")
            print("You can sync models later via Settings")
        
        return server
        
    finally:
        db.close()

if __name__ == "__main__":
    server = setup_test_server()
    if server:
        print(f"\n✓ Test server ready: {server.name} ({server.url})")
        print("\nYou can now run: python test_prompts_with_llm.py")
    else:
        print("\n⚠ No LLM server configured. Tests will run with fallback.")

