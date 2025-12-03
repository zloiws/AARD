"""
Page routes for tools web interface
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.templates import templates
from app.core.database import get_db
from app.models.tool import Tool, ToolStatus
from app.services.tool_service import ToolService
from sqlalchemy.orm import Session

router = APIRouter(tags=["tools_pages"])


@router.get("/tools", response_class=HTMLResponse)
async def tools_list(request: Request, db: Session = Depends(get_db)):
    """List all tools"""
    tool_service = ToolService(db)
    tools = tool_service.list_tools()
    
    # Group by status
    tools_by_status = {
        "draft": [],
        "waiting_approval": [],
        "active": [],
        "deprecated": [],
        "failed": []
    }
    
    for tool in tools:
        status = tool.status
        if status in tools_by_status:
            tools_by_status[status].append(tool)
    
    # Calculate statistics
    total_tools = len(tools)
    active_tools = len(tools_by_status["active"])
    
    return templates.TemplateResponse(
        "tools/list.html",
        {
            "request": request,
            "tools": tools,
            "tools_by_status": tools_by_status,
            "total_tools": total_tools,
            "active_tools": active_tools
        }
    )


@router.get("/tools/create", response_class=HTMLResponse)
async def tool_create_form(request: Request):
    """Tool creation form"""
    return templates.TemplateResponse(
        "tools/create.html",
        {
            "request": request
        }
    )


@router.get("/tools/{tool_id}", response_class=HTMLResponse)
async def tool_detail(request: Request, tool_id: UUID, db: Session = Depends(get_db)):
    """Tool detail page with metrics"""
    tool_service = ToolService(db)
    tool = tool_service.get_tool(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Calculate metrics
    metrics = {
        "total_executions": tool.total_executions,
        "successful_executions": tool.successful_executions,
        "failed_executions": tool.failed_executions,
        "success_rate": tool.success_rate or "0%",
        "average_execution_time": tool.average_execution_time or 0,
        "last_used": tool.last_used_at
    }
    
    return templates.TemplateResponse(
        "tools/detail.html",
        {
            "request": request,
            "tool": tool,
            "metrics": metrics
        }
    )


@router.get("/tools/{tool_id}/edit", response_class=HTMLResponse)
async def tool_edit_form(request: Request, tool_id: UUID, db: Session = Depends(get_db)):
    """Tool edit form"""
    tool_service = ToolService(db)
    tool = tool_service.get_tool(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    return templates.TemplateResponse(
        "tools/edit.html",
        {
            "request": request,
            "tool": tool
        }
    )

