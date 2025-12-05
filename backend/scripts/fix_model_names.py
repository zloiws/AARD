"""Fix model names in database"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer

db = SessionLocal()

# Mapping of incorrect names to correct names
name_mapping = {
    "deepseek-r1-abliterated:8b": "huihui_ai/deepseek-r1-abliterated:8b",
    "qwen3-vl:8b": "qwen3-vl:8b",  # This one is correct
    "qwen3:8b": "qwen3:8b",  # This one is correct
}

print("=== Fixing model names ===")

servers = db.query(OllamaServer).filter(OllamaServer.is_active == True).all()
for server in servers:
    print(f"\nServer: {server.name}")
    models = db.query(OllamaModel).filter(
        OllamaModel.server_id == server.id,
        OllamaModel.is_active == True
    ).all()
    
    for model in models:
        old_name = model.model_name
        if old_name in name_mapping:
            new_name = name_mapping[old_name]
            if old_name != new_name:
                print(f"  Updating model: {old_name} -> {new_name}")
                model.model_name = new_name
                model.name = new_name  # Also update display name
                db.commit()
                print(f"    ✓ Updated")
            else:
                print(f"  Model {old_name} is already correct")
        else:
            print(f"  Model {old_name} - no mapping found (keeping as is)")

db.close()
print("\n=== Done ===")

