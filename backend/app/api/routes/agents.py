"""
API routes for agent management
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.agent import Agent, AgentStatus, AgentCapability
from app.services.agent_service import AgentService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])


# Request/Response models
class AgentCreate(BaseModel):
    """Request model for creating an agent"""
    name: str = Field(..., description="Agent name (must be unique)")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent")
    capabilities: Optional[List[str]] = Field(None, description="List of agent capabilities")
    model_preference: Optional[str] = Field(None, description="Preferred LLM model")
    created_by: Optional[str] = Field(None, description="User who created the agent")
    temperature: Optional[str] = Field("0.7", description="Default temperature")
    max_concurrent_tasks: Optional[int] = Field(1, description="Max concurrent tasks")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")


class AgentUpdate(BaseModel):
    """Request model for updating an agent"""
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    capabilities: Optional[List[str]] = None
    model_preference: Optional[str] = None
    temperature: Optional[str] = None
    security_policies: Optional[dict] = None
    allowed_actions: Optional[List[str]] = None
    forbidden_actions: Optional[List[str]] = None
    max_concurrent_tasks: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    memory_limit_mb: Optional[int] = None
    metadata: Optional[dict] = None
    tags: Optional[List[str]] = None


class AgentResponse(BaseModel):
    """Response model for agent"""
    id: str
    name: str
    description: Optional[str]
    version: int
    parent_agent_id: Optional[str]
    status: str
    created_by: Optional[str]
    created_at: str
    updated_at: str
    activated_at: Optional[str]
    last_used_at: Optional[str]
    system_prompt: Optional[str]
    capabilities: Optional[List[str]]
    model_preference: Optional[str]
    temperature: Optional[str]
    identity_id: Optional[str]
    security_policies: Optional[dict]
    allowed_actions: Optional[List[str]]
    forbidden_actions: Optional[List[str]]
    max_concurrent_tasks: int
    rate_limit_per_minute: Optional[int]
    memory_limit_mb: Optional[int]
    total_tasks_executed: int
    successful_tasks: int
    failed_tasks: int
    average_execution_time: Optional[int]
    success_rate: Optional[str]
    metadata: Optional[dict]
    tags: Optional[List[str]]
    
    class Config:
        from_attributes = True


class AgentMetricsResponse(BaseModel):
    """Response model for agent metrics"""
    total_tasks_executed: int
    successful_tasks: int
    failed_tasks: int
    success_rate: Optional[str]
    average_execution_time: Optional[int]
    last_used_at: Optional[str]


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db)
):
    """Create a new agent"""
    try:
        service = AgentService(db)
        agent = service.create_agent(
            name=agent_data.name,
            description=agent_data.description,
            system_prompt=agent_data.system_prompt,
            capabilities=agent_data.capabilities,
            model_preference=agent_data.model_preference,
            created_by=agent_data.created_by,
            temperature=agent_data.temperature,
            max_concurrent_tasks=agent_data.max_concurrent_tasks,
            agent_metadata=agent_data.metadata,  # Map from API 'metadata' to DB 'agent_metadata'
            tags=agent_data.tags,
        )
        return AgentResponse(**agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    status: Optional[str] = Query(None, description="Filter by status"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
    active_only: bool = Query(False, description="Only return active agents"),
    db: Session = Depends(get_db)
):
    """List all agents with optional filters"""
    service = AgentService(db)
    agents = service.list_agents(
        status=status,
        capability=capability,
        active_only=active_only
    )
    return [AgentResponse(**agent.to_dict()) for agent in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Get agent by ID"""
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**agent.to_dict())


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: Session = Depends(get_db)
):
    """Update agent properties"""
    try:
        service = AgentService(db)
        update_data = agent_data.dict(exclude_unset=True)
        # Map 'metadata' from API to 'agent_metadata' for database
        if 'metadata' in update_data:
            update_data['agent_metadata'] = update_data.pop('metadata')
        agent = service.update_agent(agent_id, **update_data)
        return AgentResponse(**agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{agent_id}/activate", response_model=AgentResponse)
async def activate_agent(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Activate an agent"""
    try:
        service = AgentService(db)
        agent = service.activate_agent(agent_id)
        return AgentResponse(**agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{agent_id}/pause", response_model=AgentResponse)
async def pause_agent(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Pause an agent"""
    try:
        service = AgentService(db)
        agent = service.pause_agent(agent_id)
        return AgentResponse(**agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error pausing agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{agent_id}/deprecate", response_model=AgentResponse)
async def deprecate_agent(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Deprecate an agent"""
    try:
        service = AgentService(db)
        agent = service.deprecate_agent(agent_id)
        return AgentResponse(**agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deprecating agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_id}/metrics", response_model=AgentMetricsResponse)
async def get_agent_metrics(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Get agent performance metrics"""
    try:
        service = AgentService(db)
        metrics = service.get_agent_metrics(agent_id)
        return AgentMetricsResponse(**metrics)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting agent metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

