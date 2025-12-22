"""
Agent Registry Service
Service discovery and lifecycle management for agents
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.a2a_protocol import AgentIdentity
from app.core.logging_config import LoggingConfig
from app.core.tracing import add_span_attributes, get_tracer
from app.models.agent import Agent, AgentHealthStatus, AgentStatus
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class AgentRegistry:
    """
    Agent Registry for service discovery and lifecycle management
    
    Based on specification from ТЗ AARD.md section 7.3.3
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 5  # seconds
        self.unhealthy_threshold = 3  # consecutive missed heartbeats
        self.removal_threshold = 5  # minutes without heartbeat
    
    def register_agent(
        self,
        agent_id: UUID,
        endpoint: Optional[str] = None,
        capabilities: Optional[List[str]] = None
    ) -> bool:
        """
        Register an agent in the registry
        
        Args:
            agent_id: Agent ID
            endpoint: Agent endpoint URL (optional)
            capabilities: List of agent capabilities (optional)
            
        Returns:
            True if registration successful
        """
        with self.tracer.start_as_current_span("agent_registry.register") as span:
            add_span_attributes(span, agent_id=str(agent_id), endpoint=endpoint or "unknown")
            
            try:
                agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    logger.warning(f"Attempted to register unknown agent: {agent_id}")
                    return False
                
                # Update endpoint if provided
                if endpoint:
                    agent.endpoint = endpoint
                
                # Update capabilities if provided
                if capabilities:
                    agent.capabilities = capabilities
                
                # Set status to active if not already
                if agent.status != AgentStatus.ACTIVE.value:
                    agent.status = AgentStatus.ACTIVE.value
                    agent.activated_at = datetime.now(timezone.utc)
                
                # Update heartbeat
                agent.last_heartbeat = datetime.now(timezone.utc)
                agent.health_status = AgentHealthStatus.HEALTHY.value
                
                self.db.commit()
                self.db.refresh(agent)
                
                logger.info(
                    f"Agent {agent.name} ({agent_id}) registered in registry",
                    extra={
                        "agent_id": str(agent_id),
                        "endpoint": endpoint,
                        "capabilities": capabilities
                    }
                )
                
                return True
                
            except Exception as e:
                logger.error(
                    f"Error registering agent {agent_id}: {e}",
                    exc_info=True,
                    extra={"agent_id": str(agent_id)}
                )
                self.db.rollback()
                return False
    
    def unregister_agent(self, agent_id: UUID) -> bool:
        """
        Unregister an agent from the registry
        
        Args:
            agent_id: Agent ID to unregister
            
        Returns:
            True if unregistration successful
        """
        with self.tracer.start_as_current_span("agent_registry.unregister") as span:
            add_span_attributes(span, agent_id=str(agent_id))
            
            try:
                agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    return False
                
                # Mark as inactive
                agent.status = AgentStatus.PAUSED.value
                agent.health_status = AgentHealthStatus.UNKNOWN.value
                
                self.db.commit()
                self.db.refresh(agent)
                
                logger.info(f"Agent {agent.name} ({agent_id}) unregistered from registry")
                return True
                
            except Exception as e:
                logger.error(f"Error unregistering agent {agent_id}: {e}", exc_info=True)
                self.db.rollback()
                return False
    
    def find_agents(
        self,
        capabilities: Optional[List[str]] = None,
        status: Optional[AgentStatus] = None,
        health_status: Optional[AgentHealthStatus] = None,
        limit: Optional[int] = None
    ) -> List[Agent]:
        """
        Find agents by criteria
        
        Args:
            capabilities: Required capabilities (all must match)
            status: Agent status filter
            health_status: Health status filter
            limit: Maximum number of results
            
        Returns:
            List of matching agents
        """
        with self.tracer.start_as_current_span("agent_registry.find") as span:
            query = self.db.query(Agent)
            
            # Filter by status
            if status:
                query = query.filter(Agent.status == status.value)
            else:
                # Default: only active agents
                query = query.filter(Agent.status == AgentStatus.ACTIVE.value)
            
            # Filter by health status
            if health_status:
                query = query.filter(Agent.health_status == health_status.value)
            
            # Filter by capabilities
            if capabilities:
                for capability in capabilities:
                    # PostgreSQL JSONB contains operator
                    query = query.filter(Agent.capabilities.contains([capability]))
            
            # Order by health status and last heartbeat
            query = query.order_by(
                Agent.health_status.desc(),
                Agent.last_heartbeat.desc()
            )
            
            if limit:
                query = query.limit(limit)
            
            agents = query.all()
            
            add_span_attributes(
                span=span,
                found_count=len(agents),
                capabilities_filter=str(capabilities) if capabilities else None
            )
            
            return agents
    
    def get_agent_identity(self, agent_id: UUID) -> Optional[AgentIdentity]:
        """
        Get agent identity for A2A communication
        
        Args:
            agent_id: Agent ID
            
        Returns:
            AgentIdentity or None if not found
        """
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent or agent.status != AgentStatus.ACTIVE.value:
            return None
        
        return AgentIdentity(
            agent_id=agent.id,
            spiffe_id=agent.identity_id,
            version=agent.version,
            capabilities=agent.capabilities or []
        )
    
    def get_agent_endpoint(self, agent_id: UUID) -> Optional[str]:
        """
        Get agent endpoint URL
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Endpoint URL or None
        """
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return None
        
        return agent.endpoint
    
    def cleanup_unhealthy_agents(self) -> int:
        """
        Remove agents that haven't sent heartbeat for too long
        
        Returns:
            Number of agents cleaned up
        """
        with self.tracer.start_as_current_span("agent_registry.cleanup") as span:
            threshold = datetime.now(timezone.utc) - timedelta(minutes=self.removal_threshold)
            
            unhealthy_agents = self.db.query(Agent).filter(
                and_(
                    Agent.status == AgentStatus.ACTIVE.value,
                    or_(
                        Agent.last_heartbeat == None,
                        Agent.last_heartbeat < threshold
                    )
                )
            ).all()
            
            cleaned_count = 0
            for agent in unhealthy_agents:
                agent.health_status = AgentHealthStatus.UNHEALTHY.value
                # Optionally pause the agent
                # agent.status = AgentStatus.PAUSED.value
                cleaned_count += 1
            
            if cleaned_count > 0:
                self.db.commit()
                logger.warning(
                    f"Marked {cleaned_count} agents as unhealthy due to missing heartbeats"
                )
            
            add_span_attributes(span, cleaned_count=cleaned_count)
            return cleaned_count
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics
        
        Returns:
            Dictionary with registry statistics
        """
        active_agents = self.db.query(Agent).filter(
            Agent.status == AgentStatus.ACTIVE.value
        ).all()
        
        stats = {
            "total_active": len(active_agents),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "unknown": 0,
            "by_capability": {}
        }
        
        for agent in active_agents:
            health = agent.health_status or AgentHealthStatus.UNKNOWN.value
            if health == AgentHealthStatus.HEALTHY.value:
                stats["healthy"] += 1
            elif health == AgentHealthStatus.DEGRADED.value:
                stats["degraded"] += 1
            elif health == AgentHealthStatus.UNHEALTHY.value:
                stats["unhealthy"] += 1
            else:
                stats["unknown"] += 1
            
            # Count by capability
            if agent.capabilities:
                for capability in agent.capabilities:
                    if capability not in stats["by_capability"]:
                        stats["by_capability"][capability] = 0
                    stats["by_capability"][capability] += 1
        
        return stats

