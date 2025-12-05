"""Sync models for all active servers"""
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
from app.services.ollama_service import OllamaService

async def sync_all_models():
    """Sync models for all active servers"""
    print("=== Syncing Models for All Servers ===\n")
    db: Session = SessionLocal()
    try:
        # Get all active servers
        servers = OllamaService.get_all_active_servers(db)
        
        if not servers:
            print("⚠ No active servers found!")
            return False
        
        print(f"Found {len(servers)} active server(s)\n")
        
        # Import discover function
        from app.api.routes.servers import discover_server_models
        
        for server in servers:
            print(f"Syncing models for: {server.name} ({server.url})")
            try:
                # Use the discover function from API routes
                result = await discover_server_models(str(server.id), db)
                models_found = result.get("models_found", 0)
                models_added = result.get("models_added", 0)
                print(f"  ✓ Found {models_found} models (added {models_added} new)")
                models = OllamaService.get_models_for_server(db, str(server.id))
                for model in models[:5]:
                    print(f"    - {model.model_name}")
                if len(models) > 5:
                    print(f"    ... and {len(models) - 5} more")
            except Exception as e:
                print(f"  ✗ Error: {e}")
            print()
        
        print("✅ Model sync completed!")
        return True
        
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(sync_all_models())

