"""
Web pages for settings (servers and models management)
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.core.database import get_db
from app.services.ollama_service import OllamaService
from app.models.ollama_server import OllamaServer
from app.models.ollama_model import OllamaModel

router = APIRouter(tags=["settings_pages"])


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Settings page for managing servers and models"""
    servers = OllamaService.get_all_active_servers(db)
    
    servers_info = []
    for server in servers:
        models = OllamaService.get_models_for_server(db, str(server.id))
        servers_info.append({
            "id": str(server.id),
            "name": server.name,
            "url": server.url,
            "api_url": server.get_api_url(),
            "is_available": server.is_available,
            "is_default": server.is_default,
            "models_count": len(models),
            "models": [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "model_name": m.model_name,
                    "is_active": m.is_active,
                    "capabilities": m.capabilities or [],
                    "priority": m.priority or 0
                }
                for m in models
            ]
        })
    
    return templates.TemplateResponse(
        "settings/index.html",
        {
            "request": request,
            "servers": servers_info
        }
    )

