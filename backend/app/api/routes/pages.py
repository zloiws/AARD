"""
Page routes for web interface
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from app.core.templates import templates

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main chat page - loads servers from database"""
    # Don't load servers here - frontend will load them via API
    # This makes the page load instantly even if DB is unavailable
    # Frontend will call /api/models/servers to get servers
    servers_info = []
    
    return templates.TemplateResponse(
        "main.html",  # Using unified interface with tabs
        {
            "request": request,
            "servers": servers_info  # Empty list - frontend will load via API
        }
    )

