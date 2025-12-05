"""Check models on Ollama server"""
import sys
import os
import asyncio
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.ollama_server import OllamaServer

async def check_models():
    db = SessionLocal()
    
    servers = db.query(OllamaServer).filter(OllamaServer.is_active == True).all()
    
    for server in servers:
        print(f"\n=== Server: {server.name} ===")
        print(f"URL: {server.url}")
        
        # Get base URL (without /v1)
        base_url = server.url
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        elif base_url.endswith("/v1/"):
            base_url = base_url[:-4]
        
        print(f"Base URL: {base_url}")
        
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
                # Get list of models
                response = await client.get("/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    print(f"Found {len(models)} models on server:")
                    for model in models:
                        model_name = model.get("name", "unknown")
                        print(f"  - {model_name}")
                else:
                    print(f"Error getting models: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error connecting to server: {e}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(check_models())


