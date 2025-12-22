"""
Page routes for system settings management UI
"""
from app.core.database import get_db
from app.core.templates import templates
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

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
