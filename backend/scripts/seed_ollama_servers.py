import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR.parent / ".env", override=True)

from datetime import datetime

from app.core.database import get_session_local
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer

SERVERS = [
    {
        "name": "ollama-101",
        "url": "http://10.39.0.101:11434",
        "api_version": "v1",
        "is_active": True,
        "is_default": True,
        "description": "Test Ollama server 10.39.0.101",
        "capabilities": ["general", "planning"],
        "max_concurrent": 2,
    },
    {
        "name": "ollama-6",
        "url": "http://10.39.0.6:11434",
        "api_version": "v1",
        "is_active": True,
        "is_default": False,
        "description": "Test Ollama server 10.39.0.6",
        "capabilities": ["general"],
        "max_concurrent": 1,
    },
]

DEFAULT_MODELS = [
    {"name": "deepseek-r1-abliterated:8b", "model_name": "deepseek-r1-abliterated:8b", "capabilities": ["planning", "dialog"]},
    {"name": "nomic-embed-text", "model_name": "nomic-embed-text", "capabilities": ["embedding"]},
]

def main():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        created = []
        for s in SERVERS:
            existing = db.query(OllamaServer).filter(OllamaServer.url == s["url"]).first()
            if existing:
                print(f"Server exists: {s['url']}")
                server = existing
            else:
                server = OllamaServer(
                    name=s["name"],
                    url=s["url"],
                    api_version=s.get("api_version", "v1"),
                    is_active=s.get("is_active", True),
                    is_default=s.get("is_default", False),
                    description=s.get("description"),
                    capabilities=s.get("capabilities"),
                    max_concurrent=s.get("max_concurrent", 1),
                    created_at=datetime.utcnow(),
                )
                db.add(server)
                db.commit()
                db.refresh(server)
                created.append(server.url)

            # ensure models exist for this server (only add embedding model on second server)
            for m in DEFAULT_MODELS:
                exists_m = db.query(OllamaModel).filter(OllamaModel.server_id == server.id, OllamaModel.model_name == m["model_name"]).first()
                if not exists_m:
                    mod = OllamaModel(
                        server_id=server.id,
                        name=m["name"],
                        model_name=m["model_name"],
                        capabilities=m.get("capabilities", []),
                        is_active=True,
                    )
                    db.add(mod)
        db.commit()
        if created:
            print("Created servers:", created)
        else:
            print("No new servers created.")
    except Exception as e:
        print("Error seeding servers:", e)
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()

if __name__ == "__main__":
    main()


