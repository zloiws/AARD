"""
Page routes for agents web interface
"""
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.templates import templates
from app.models.agent import Agent, AgentStatus
from app.services.agent_service import AgentService
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

router = APIRouter(tags=["agents_pages"])


@router.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request, db: Session = Depends(get_db)):
    """List all agents"""
    agent_service = AgentService(db)
    agents = agent_service.list_agents()
    
    # Group by status
    agents_by_status = {
        "draft": [],
        "waiting_approval": [],
        "active": [],
        "paused": [],
        "deprecated": [],
        "failed": []
    }
    
    for agent in agents:
        status = agent.status
        if status in agents_by_status:
            agents_by_status[status].append(agent)
    
    # Calculate statistics
    total_agents = len(agents)
    active_agents = len(agents_by_status["active"])
    
    return templates.TemplateResponse(
        "agents/list.html",
        {
            "request": request,
            "agents": agents,
            "agents_by_status": agents_by_status,
            "total_agents": total_agents,
            "active_agents": active_agents
        }
    )


@router.get("/agents/create", response_class=HTMLResponse)
async def agent_create_form(request: Request, db: Session = Depends(get_db)):
    """Agent creation form"""
    from app.models.tool import ToolStatus
    from app.services.tool_service import ToolService
    
    tool_service = ToolService(db)
    available_tools = tool_service.list_tools(status=ToolStatus.ACTIVE)
    
    return templates.TemplateResponse(
        "agents/create.html",
        {
            "request": request,
            "available_tools": available_tools
        }
    )


@router.get("/agents/{agent_id}", response_class=HTMLResponse)
async def agent_detail(request: Request, agent_id: UUID, db: Session = Depends(get_db)):
    """Agent detail page with metrics"""
    agent_service = AgentService(db)
    agent = agent_service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get available tools for assignment
    from app.models.tool import ToolStatus
    from app.services.tool_service import ToolService
    
    tool_service = ToolService(db)
    available_tools = tool_service.list_tools(status=ToolStatus.ACTIVE)
    
    # Calculate metrics
    metrics = {
        "total_tasks": agent.total_tasks_executed,
        "successful_tasks": agent.successful_tasks,
        "failed_tasks": agent.failed_tasks,
        "success_rate": agent.success_rate or "0%",
        "average_execution_time": agent.average_execution_time or 0,
        "last_used": agent.last_used_at
    }
    
    return templates.TemplateResponse(
        "agents/detail.html",
        {
            "request": request,
            "agent": agent,
            "metrics": metrics,
            "available_tools": available_tools
        }
    )


@router.get("/agents/{agent_id}/edit", response_class=HTMLResponse)
async def agent_edit_form(request: Request, agent_id: UUID, db: Session = Depends(get_db)):
    """Agent edit form"""
    agent_service = AgentService(db)
    agent = agent_service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    from app.models.tool import ToolStatus
    from app.services.tool_service import ToolService
    
    tool_service = ToolService(db)
    available_tools = tool_service.list_tools(status=ToolStatus.ACTIVE)
    
    return templates.TemplateResponse(
        "agents/edit.html",
        {
            "request": request,
            "agent": agent,
            "available_tools": available_tools
        }
    )

