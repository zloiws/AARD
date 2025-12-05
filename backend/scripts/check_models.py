"""Check models in database"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer

db = SessionLocal()

print("=== Servers ===")
servers = db.query(OllamaServer).filter(OllamaServer.is_active == True).all()
for server in servers:
    print(f"Server: {server.name}")
    print(f"  URL: {server.url}")
    print(f"  API URL: {server.get_api_url()}")
    print(f"  Models:")
    models = db.query(OllamaModel).filter(
        OllamaModel.server_id == server.id,
        OllamaModel.is_active == True
    ).limit(5).all()
    for model in models:
        print(f"    - ID: {model.id}")
        print(f"      name: '{model.name}'")
        print(f"      model_name: '{model.model_name}'")
        print(f"      is_active: {model.is_active}")
    print()

db.close()

