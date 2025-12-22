"""Setup test server 10.39.0.6 in database"""
import asyncio
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uuid import uuid4

from app.core.database import SessionLocal
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer


async def setup_server():
    db = SessionLocal()
    
    # Check if server exists
    server = db.query(OllamaServer).filter(
        OllamaServer.url == "http://10.39.0.6:11434"
    ).first()
    
    if not server:
        print("Creating server 10.39.0.6...")
        server = OllamaServer(
            name=f"Test Server 10.39.0.6",
            url="http://10.39.0.6:11434",
            is_active=True
        )
        db.add(server)
        db.commit()
        db.refresh(server)
        print(f"✓ Server created: {server.id}")
    else:
        print(f"✓ Server already exists: {server.id}")
        server.is_active = True
        db.commit()
    
    # Get models from server
    base_url = "http://10.39.0.6:11434"
    print(f"\nFetching models from {base_url}...")
    
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            response = await client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"Found {len(models)} models on server")
                
                # Update or create models in DB
                for model_data in models:
                    model_name = model_data.get("name", "")
                    if not model_name:
                        continue
                    
                    # Check if model exists
                    existing = db.query(OllamaModel).filter(
                        OllamaModel.server_id == server.id,
                        OllamaModel.model_name == model_name
                    ).first()
                    
                    if existing:
                        existing.is_active = True
                        existing.name = model_name
                        print(f"  ✓ Updated: {model_name}")
                    else:
                        new_model = OllamaModel(
                            server_id=server.id,
                            name=model_name,
                            model_name=model_name,
                            is_active=True
                        )
                        db.add(new_model)
                        print(f"  + Created: {model_name}")
                
                db.commit()
                print(f"\n✓ Models synchronized")
            else:
                print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(setup_server())

