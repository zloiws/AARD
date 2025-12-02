"""
Page routes for web interface
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from app.core.templates import templates
from app.core.database import get_db
from app.services.ollama_service import OllamaService
from sqlalchemy.orm import Session

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """Main chat page - loads servers from database"""
    # Get servers from database (frontend will load models via API)
    servers = OllamaService.get_all_active_servers(db)
    
    servers_info = []
    for server in servers:
        servers_info.append({
            "id": str(server.id),
            "name": server.name,
            "url": server.url,
            "api_url": server.get_api_url(),
            "capabilities": server.capabilities or [],
            "is_available": server.is_available,
            "is_default": server.is_default
        })
    
    return templates.TemplateResponse(
        "main.html",  # Using unified interface with tabs
        {
            "request": request,
            "servers": servers_info  # Changed from models to servers
        }
    )

