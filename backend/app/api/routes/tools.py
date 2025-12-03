"""
API routes for tool management
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tool import Tool, ToolStatus, ToolCategory
from app.services.tool_service import ToolService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)
router = APIRouter(prefix="/api/tools", tags=["tools"])


# Request/Response models
class ToolCreate(BaseModel):
    """Request model for creating a tool"""
    name: str = Field(..., description="Tool name (must be unique)")
    description: Optional[str] = Field(None, description="Tool description")
    category: Optional[str] = Field(None, description="Tool category")
    code: Optional[str] = Field(None, description="Tool code (Python function)")
    entry_point: Optional[str] = Field("execute", description="Function name to call")
    language: str = Field("python", description="Programming language")
    input_schema: Optional[dict] = Field(None, description="JSON Schema for input parameters")
    output_schema: Optional[dict] = Field(None, description="JSON Schema for output")
    parameters: Optional[List[dict]] = Field(None, description="Simplified parameter definitions")
    dependencies: Optional[List[str]] = Field(None, description="List of required packages")
    requirements: Optional[str] = Field(None, description="requirements.txt content")
    created_by: Optional[str] = Field(None, description="User who created the tool")
    timeout_seconds: Optional[int] = Field(None, description="Execution timeout in seconds")
    requires_approval: bool = Field(False, description="Require approval before execution")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    examples: Optional[List[dict]] = Field(None, description="Example usage")


class ToolUpdate(BaseModel):
    """Request model for updating a tool"""
    description: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    entry_point: Optional[str] = None
    language: Optional[str] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    parameters: Optional[List[dict]] = None
    dependencies: Optional[List[str]] = None
    requirements: Optional[str] = None
    security_policies: Optional[dict] = None
    allowed_agents: Optional[List[str]] = None
    forbidden_agents: Optional[List[str]] = None
    requires_approval: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    max_memory_mb: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    metadata: Optional[dict] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[dict]] = None


class ToolResponse(BaseModel):
    """Response model for tool"""
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    version: int
    parent_tool_id: Optional[str]
    status: str
    created_by: Optional[str]
    created_at: str
    updated_at: str
    activated_at: Optional[str]
    last_used_at: Optional[str]
    code: Optional[str]
    entry_point: Optional[str]
    language: str
    input_schema: Optional[dict]
    output_schema: Optional[dict]
    parameters: Optional[List[dict]]
    dependencies: Optional[List[str]]
    requirements: Optional[str]
    security_policies: Optional[dict]
    allowed_agents: Optional[List[str]]
    forbidden_agents: Optional[List[str]]
    requires_approval: bool
    timeout_seconds: Optional[int]
    max_memory_mb: Optional[int]
    rate_limit_per_minute: Optional[int]
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time: Optional[int]
    success_rate: Optional[str]
    metadata: Optional[dict]
    tags: Optional[List[str]]
    examples: Optional[List[dict]]
    
    class Config:
        from_attributes = True


class ToolMetricsResponse(BaseModel):
    """Response model for tool metrics"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: Optional[str]
    average_execution_time: Optional[int]
    last_used_at: Optional[str]


@router.post("/", response_model=ToolResponse, status_code=201)
async def create_tool(
    tool_data: ToolCreate,
    db: Session = Depends(get_db)
):
    """Create a new tool"""
    try:
        service = ToolService(db)
        tool = service.create_tool(
            name=tool_data.name,
            description=tool_data.description,
            category=tool_data.category,
            code=tool_data.code,
            entry_point=tool_data.entry_point,
            language=tool_data.language,
            input_schema=tool_data.input_schema,
            output_schema=tool_data.output_schema,
            parameters=tool_data.parameters,
            dependencies=tool_data.dependencies,
            requirements=tool_data.requirements,
            created_by=tool_data.created_by,
            timeout_seconds=tool_data.timeout_seconds,
            requires_approval=tool_data.requires_approval,
            tool_metadata=tool_data.metadata,  # Map from API 'metadata' to DB 'tool_metadata'
            tags=tool_data.tags,
            examples=tool_data.examples,
        )
        return ToolResponse(**tool.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    active_only: bool = Query(False, description="Only return active tools"),
    db: Session = Depends(get_db)
):
    """List all tools with optional filters"""
    service = ToolService(db)
    tools = service.list_tools(
        status=status,
        category=category,
        active_only=active_only
    )
    return [ToolResponse(**tool.to_dict()) for tool in tools]


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID,
    db: Session = Depends(get_db)
):
    """Get tool by ID"""
    service = ToolService(db)
    tool = service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return ToolResponse(**tool.to_dict())


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    tool_data: ToolUpdate,
    db: Session = Depends(get_db)
):
    """Update tool properties"""
    try:
        service = ToolService(db)
        update_data = tool_data.dict(exclude_unset=True)
        # Map 'metadata' from API to 'tool_metadata' for database
        if 'metadata' in update_data:
            update_data['tool_metadata'] = update_data.pop('metadata')
        tool = service.update_tool(tool_id, **update_data)
        return ToolResponse(**tool.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{tool_id}/activate", response_model=ToolResponse)
async def activate_tool(
    tool_id: UUID,
    db: Session = Depends(get_db)
):
    """Activate a tool"""
    try:
        service = ToolService(db)
        tool = service.activate_tool(tool_id)
        return ToolResponse(**tool.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{tool_id}/pause", response_model=ToolResponse)
async def pause_tool(
    tool_id: UUID,
    db: Session = Depends(get_db)
):
    """Pause a tool"""
    try:
        service = ToolService(db)
        tool = service.pause_tool(tool_id)
        return ToolResponse(**tool.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error pausing tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{tool_id}/deprecate", response_model=ToolResponse)
async def deprecate_tool(
    tool_id: UUID,
    db: Session = Depends(get_db)
):
    """Deprecate a tool"""
    try:
        service = ToolService(db)
        tool = service.deprecate_tool(tool_id)
        return ToolResponse(**tool.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deprecating tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tool_id}/metrics", response_model=ToolMetricsResponse)
async def get_tool_metrics(
    tool_id: UUID,
    db: Session = Depends(get_db)
):
    """Get tool performance metrics"""
    try:
        service = ToolService(db)
        metrics = service.get_tool_metrics(tool_id)
        return ToolMetricsResponse(**metrics)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting tool metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tool_id}/can-use/{agent_id}")
async def can_agent_use_tool(
    tool_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Check if an agent can use a tool"""
    try:
        service = ToolService(db)
        can_use = service.can_agent_use_tool(tool_id, agent_id)
        return {
            "tool_id": str(tool_id),
            "agent_id": str(agent_id),
            "can_use": can_use
        }
    except Exception as e:
        logger.error(f"Error checking tool access: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

