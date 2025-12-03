"""
Agent Service for managing agents lifecycle
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.agent import Agent, AgentStatus, AgentCapability
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes

logger = LoggingConfig.get_logger(__name__)


class AgentService:
    """Service for managing agents lifecycle"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
    
    def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        model_preference: Optional[str] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """
        Create a new agent
        
        Args:
            name: Agent name (must be unique)
            description: Agent description
            system_prompt: System prompt for the agent
            capabilities: List of agent capabilities
            model_preference: Preferred LLM model
            created_by: User who created the agent
            **kwargs: Additional agent properties
            
        Returns:
            Created Agent
        """
        # Check if agent with same name exists
        existing = self.db.query(Agent).filter(Agent.name == name).first()
        if existing:
            raise ValueError(f"Agent with name '{name}' already exists")
        
        agent = Agent(
            name=name,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or [],
            model_preference=model_preference,
            created_by=created_by,
            status=AgentStatus.DRAFT.value,
            **kwargs
        )
        
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(
            f"Created agent: {name}",
            extra={
                "agent_id": str(agent.id),
                "agent_name": name,
                "created_by": created_by,
            }
        )
        
        return agent
    
    def get_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent by ID"""
        return self.db.query(Agent).filter(Agent.id == agent_id).first()
    
    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name"""
        return self.db.query(Agent).filter(Agent.name == name).first()
    
    def list_agents(
        self,
        status: Optional[str] = None,
        capability: Optional[str] = None,
        active_only: bool = False
    ) -> List[Agent]:
        """
        List agents with optional filters
        
        Args:
            status: Filter by status
            capability: Filter by capability
            active_only: Only return active agents
            
        Returns:
            List of agents
        """
        query = self.db.query(Agent)
        
        if active_only:
            query = query.filter(Agent.status == AgentStatus.ACTIVE.value)
        elif status:
            query = query.filter(Agent.status == status)
        
        if capability:
            # Filter by capability (JSONB contains)
            query = query.filter(Agent.capabilities.contains([capability]))
        
        return query.order_by(desc(Agent.created_at)).all()
    
    def update_agent(
        self,
        agent_id: UUID,
        **kwargs
    ) -> Agent:
        """
        Update agent properties
        
        Args:
            agent_id: Agent ID
            **kwargs: Properties to update
            
        Returns:
            Updated Agent
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Update allowed fields
        allowed_fields = [
            'description', 'system_prompt', 'capabilities', 'model_preference',
            'temperature', 'security_policies', 'allowed_actions', 'forbidden_actions',
            'max_concurrent_tasks', 'rate_limit_per_minute', 'memory_limit_mb',
            'agent_metadata', 'tags'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(agent, field, value)
        
        agent.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(
            f"Updated agent: {agent.name}",
            extra={
                "agent_id": str(agent.id),
                "updated_fields": list(kwargs.keys()),
            }
        )
        
        return agent
    
    def activate_agent(self, agent_id: UUID) -> Agent:
        """
        Activate an agent (change status to active)
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Activated Agent
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent.status != AgentStatus.WAITING_APPROVAL.value:
            raise ValueError(f"Agent must be in 'waiting_approval' status to activate (current: {agent.status})")
        
        agent.status = AgentStatus.ACTIVE.value
        agent.activated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(
            f"Activated agent: {agent.name}",
            extra={"agent_id": str(agent.id)}
        )
        
        return agent
    
    def pause_agent(self, agent_id: UUID) -> Agent:
        """Pause an agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent.status = AgentStatus.PAUSED.value
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(f"Paused agent: {agent.name}", extra={"agent_id": str(agent.id)})
        
        return agent
    
    def deprecate_agent(self, agent_id: UUID) -> Agent:
        """Deprecate an agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent.status = AgentStatus.DEPRECATED.value
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(f"Deprecated agent: {agent.name}", extra={"agent_id": str(agent.id)})
        
        return agent
    
    def record_task_execution(
        self,
        agent_id: UUID,
        success: bool,
        execution_time: Optional[int] = None
    ):
        """
        Record task execution for metrics
        
        Args:
            agent_id: Agent ID
            success: Whether task was successful
            execution_time: Execution time in seconds
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return
        
        agent.total_tasks_executed += 1
        if success:
            agent.successful_tasks += 1
        else:
            agent.failed_tasks += 1
        
        # Update average execution time
        if execution_time is not None:
            if agent.average_execution_time is None:
                agent.average_execution_time = execution_time
            else:
                # Simple moving average
                agent.average_execution_time = int(
                    (agent.average_execution_time + execution_time) / 2
                )
        
        # Calculate success rate
        if agent.total_tasks_executed > 0:
            rate = agent.successful_tasks / agent.total_tasks_executed
            agent.success_rate = f"{rate:.2%}"
        
        agent.last_used_at = datetime.utcnow()
        self.db.commit()
    
    def get_agent_metrics(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Get agent performance metrics
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dictionary with metrics
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        return {
            "total_tasks_executed": agent.total_tasks_executed,
            "successful_tasks": agent.successful_tasks,
            "failed_tasks": agent.failed_tasks,
            "success_rate": agent.success_rate,
            "average_execution_time": agent.average_execution_time,
            "last_used_at": agent.last_used_at.isoformat() if agent.last_used_at else None,
        }

