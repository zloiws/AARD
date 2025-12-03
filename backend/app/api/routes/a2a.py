"""
API routes for A2A (Agent-to-Agent) communication
"""
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from app.core.database import get_db
from app.core.a2a_protocol import A2AMessage, A2ARequest, A2AResponse
from app.services.a2a_router import A2ARouter
from app.services.agent_registry import AgentRegistry
from app.core.logging_config import LoggingConfig
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)
router = APIRouter(prefix="/api/a2a", tags=["a2a"])


class SendMessageRequest(BaseModel):
    """Request to send A2A message"""
    message: Dict[str, Any]  # A2AMessage as dict
    wait_for_response: bool = False
    timeout: Optional[int] = None


class SendMessageResponse(BaseModel):
    """Response from sending A2A message"""
    message_id: str
    sent: bool
    response: Optional[Dict[str, Any]] = None


@router.post("/message", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Send A2A message
    
    Accepts A2AMessage in dict format and routes it to recipient(s)
    """
    try:
        # Parse message
        message = A2AMessage.from_dict(request.message)
        
        # Create router
        router_service = A2ARouter(db)
        
        # Send message
        response = await router_service.send_message(
            message=message,
            wait_for_response=request.wait_for_response,
            timeout=request.timeout
        )
        
        return SendMessageResponse(
            message_id=str(message.message_id),
            sent=True,
            response=response.to_dict() if response else None
        )
        
    except Exception as e:
        logger.error(f"Error sending A2A message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/receive")
async def receive_message(
    message: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Receive and handle incoming A2A message
    
    This endpoint is called by agents to receive messages
    """
    try:
        # Parse message
        a2a_message = A2AMessage.from_dict(message)
        
        # Create router
        router_service = A2ARouter(db)
        
        # Handle message (for now, just log it)
        # In the future, this could call agent-specific handlers
        response = await router_service.handle_incoming_message(a2a_message)
        
        if response:
            return response.to_dict()
        else:
            return {"status": "received"}
            
    except Exception as e:
        logger.error(f"Error receiving A2A message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry/stats")
async def get_registry_stats(db: Session = Depends(get_db)):
    """Get Agent Registry statistics"""
    try:
        registry = AgentRegistry(db)
        stats = registry.get_registry_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting registry stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry/agents")
async def find_agents(
    capabilities: Optional[str] = None,
    status: Optional[str] = None,
    health_status: Optional[str] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Find agents in registry
    
    Args:
        capabilities: Comma-separated list of required capabilities
        status: Agent status filter
        health_status: Health status filter
        limit: Maximum number of results
    """
    try:
        from app.models.agent import AgentStatus, AgentHealthStatus
        
        registry = AgentRegistry(db)
        
        # Parse capabilities
        capability_list = None
        if capabilities:
            capability_list = [c.strip() for c in capabilities.split(",")]
        
        # Parse status
        status_enum = None
        if status:
            try:
                status_enum = AgentStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        # Parse health status
        health_enum = None
        if health_status:
            try:
                health_enum = AgentHealthStatus(health_status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid health_status: {health_status}")
        
        agents = registry.find_agents(
            capabilities=capability_list,
            status=status_enum,
            health_status=health_enum,
            limit=limit
        )
        
        return {
            "count": len(agents),
            "agents": [agent.to_dict() for agent in agents]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/registry/{agent_id}/register")
async def register_agent(
    agent_id: UUID,
    endpoint: Optional[str] = None,
    capabilities: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Register agent in registry"""
    try:
        registry = AgentRegistry(db)
        
        capability_list = None
        if capabilities:
            capability_list = [c.strip() for c in capabilities.split(",")]
        
        success = registry.register_agent(
            agent_id=agent_id,
            endpoint=endpoint,
            capabilities=capability_list
        )
        
        if success:
            return {"status": "registered", "agent_id": str(agent_id)}
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/registry/{agent_id}/unregister")
async def unregister_agent(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Unregister agent from registry"""
    try:
        registry = AgentRegistry(db)
        success = registry.unregister_agent(agent_id)
        
        if success:
            return {"status": "unregistered", "agent_id": str(agent_id)}
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

