"""
Page routes for system settings management UI
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.core.database import get_db

router = APIRouter(tags=["settings_pages"])


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    """System settings management page"""
    return templates.TemplateResponse(
        "settings/index.html",
        {
            "request": request
        }
    )
