"""
Agent Heartbeat Service
Manages periodic health checks and heartbeat for agents
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.agent import Agent, AgentStatus, AgentHealthStatus
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes
from app.core.database import get_db

logger = LoggingConfig.get_logger(__name__)


class AgentHeartbeatService:
    """Service for managing agent heartbeats and health checks"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 5  # seconds
        self.unhealthy_threshold = 3  # consecutive missed heartbeats
        self.removal_threshold = 10  # minutes without heartbeat
    
    async def register_heartbeat(
        self,
        agent_id: UUID,
        endpoint: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ) -> bool:
        """
        Register a heartbeat from an agent
        
        Args:
            agent_id: Agent ID
            endpoint: Agent endpoint URL (optional, for first registration)
            response_time_ms: Response time in milliseconds (optional)
            
        Returns:
            True if heartbeat registered successfully
        """
        with self.tracer.start_as_current_span("agent_heartbeat.register") as span:
            add_span_attributes(span, {
                "agent_id": str(agent_id),
                "endpoint": endpoint or "unknown",
                "response_time_ms": response_time_ms or 0
            })
            
            try:
                agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    logger.warning(f"Heartbeat from unknown agent: {agent_id}")
                    return False
                
                # Update heartbeat timestamp
                agent.last_heartbeat = datetime.utcnow()
                
                # Update endpoint if provided (first registration)
                if endpoint:
                    agent.endpoint = endpoint
                
                # Update response time if provided
                if response_time_ms is not None:
                    agent.response_time_ms = response_time_ms
                    agent.last_health_check = datetime.utcnow()
                
                # Update health status based on response time
                if response_time_ms is not None:
                    if response_time_ms < 1000:
                        agent.health_status = AgentHealthStatus.HEALTHY.value
                    elif response_time_ms < 5000:
                        agent.health_status = AgentHealthStatus.DEGRADED.value
                    else:
                        agent.health_status = AgentHealthStatus.UNHEALTHY.value
                else:
                    # If no response time, mark as healthy if heartbeat received
                    if agent.health_status == AgentHealthStatus.UNHEALTHY.value:
                        agent.health_status = AgentHealthStatus.DEGRADED.value
                    elif agent.health_status == AgentHealthStatus.UNKNOWN.value:
                        agent.health_status = AgentHealthStatus.HEALTHY.value
                
                self.db.commit()
                self.db.refresh(agent)
                
                logger.debug(
                    f"Heartbeat registered for agent {agent.name}",
                    extra={
                        "agent_id": str(agent_id),
                        "health_status": agent.health_status,
                        "response_time_ms": response_time_ms
                    }
                )
                
                return True
                
            except Exception as e:
                logger.error(
                    f"Error registering heartbeat for agent {agent_id}: {e}",
                    exc_info=True,
                    extra={"agent_id": str(agent_id)}
                )
                self.db.rollback()
                return False
    
    async def check_agent_health(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Perform health check for an agent
        
        Args:
            agent_id: Agent ID to check
            
        Returns:
            Dictionary with health check results
        """
        with self.tracer.start_as_current_span("agent_heartbeat.health_check") as span:
            add_span_attributes(span, {"agent_id": str(agent_id)})
            
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return {
                    "status": "error",
                    "message": "Agent not found",
                    "health_status": AgentHealthStatus.UNKNOWN.value
                }
            
            # Check if agent is active
            if agent.status != AgentStatus.ACTIVE.value:
                return {
                    "status": "inactive",
                    "message": f"Agent is not active (status: {agent.status})",
                    "health_status": AgentHealthStatus.UNKNOWN.value
                }
            
            # Check last heartbeat
            if not agent.last_heartbeat:
                agent.health_status = AgentHealthStatus.UNKNOWN.value
                self.db.commit()
                return {
                    "status": "unknown",
                    "message": "No heartbeat received yet",
                    "health_status": AgentHealthStatus.UNKNOWN.value
                }
            
            # Calculate time since last heartbeat
            time_since_heartbeat = datetime.utcnow() - agent.last_heartbeat
            
            # Determine health status
            if time_since_heartbeat.total_seconds() > self.removal_threshold * 60:
                agent.health_status = AgentHealthStatus.UNHEALTHY.value
                self.db.commit()
                return {
                    "status": "unhealthy",
                    "message": f"No heartbeat for {int(time_since_heartbeat.total_seconds() / 60)} minutes",
                    "health_status": AgentHealthStatus.UNHEALTHY.value,
                    "time_since_heartbeat_seconds": int(time_since_heartbeat.total_seconds())
                }
            elif time_since_heartbeat.total_seconds() > self.unhealthy_threshold * self.heartbeat_interval:
                agent.health_status = AgentHealthStatus.DEGRADED.value
                self.db.commit()
                return {
                    "status": "degraded",
                    "message": f"Heartbeat delayed by {int(time_since_heartbeat.total_seconds())} seconds",
                    "health_status": AgentHealthStatus.DEGRADED.value,
                    "time_since_heartbeat_seconds": int(time_since_heartbeat.total_seconds())
                }
            else:
                return {
                    "status": "healthy",
                    "message": "Agent is healthy",
                    "health_status": agent.health_status or AgentHealthStatus.HEALTHY.value,
                    "response_time_ms": agent.response_time_ms,
                    "time_since_heartbeat_seconds": int(time_since_heartbeat.total_seconds())
                }
    
    async def check_all_agents_health(self) -> Dict[str, Any]:
        """
        Check health of all active agents
        
        Returns:
            Dictionary with health check results for all agents
        """
        with self.tracer.start_as_current_span("agent_heartbeat.check_all") as span:
            active_agents = self.db.query(Agent).filter(
                Agent.status == AgentStatus.ACTIVE.value
            ).all()
            
            results = {
                "total": len(active_agents),
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
                "unknown": 0,
                "agents": []
            }
            
            for agent in active_agents:
                health_result = await self.check_agent_health(agent.id)
                health_status = health_result.get("health_status", AgentHealthStatus.UNKNOWN.value)
                
                if health_status == AgentHealthStatus.HEALTHY.value:
                    results["healthy"] += 1
                elif health_status == AgentHealthStatus.DEGRADED.value:
                    results["degraded"] += 1
                elif health_status == AgentHealthStatus.UNHEALTHY.value:
                    results["unhealthy"] += 1
                else:
                    results["unknown"] += 1
                
                results["agents"].append({
                    "agent_id": str(agent.id),
                    "name": agent.name,
                    "health_status": health_status,
                    "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                    "response_time_ms": agent.response_time_ms
                })
            
            add_span_attributes(span, {
                "total_agents": results["total"],
                "healthy": results["healthy"],
                "unhealthy": results["unhealthy"]
            })
            
            return results
    
    def get_unhealthy_agents(self) -> List[Agent]:
        """
        Get list of unhealthy agents
        
        Returns:
            List of agents with unhealthy status
        """
        return self.db.query(Agent).filter(
            and_(
                Agent.status == AgentStatus.ACTIVE.value,
                Agent.health_status == AgentHealthStatus.UNHEALTHY.value
            )
        ).all()
    
    def get_agents_without_heartbeat(self, minutes: int = 5) -> List[Agent]:
        """
        Get agents that haven't sent heartbeat for specified minutes
        
        Args:
            minutes: Number of minutes without heartbeat
            
        Returns:
            List of agents without recent heartbeat
        """
        threshold = datetime.utcnow() - timedelta(minutes=minutes)
        
        return self.db.query(Agent).filter(
            and_(
                Agent.status == AgentStatus.ACTIVE.value,
                (
                    (Agent.last_heartbeat == None) |
                    (Agent.last_heartbeat < threshold)
                )
            )
        ).all()

