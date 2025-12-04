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
    
    def select_agent_for_task(
        self,
        required_capabilities: Optional[List[str]] = None,
        preferred_agent_id: Optional[UUID] = None
    ) -> Optional[Agent]:
        """
        Select the best agent for a task based on capabilities and performance metrics
        
        Args:
            required_capabilities: List of required capabilities (e.g., ["code_generation", "planning"])
            preferred_agent_id: Optional preferred agent ID to check first
            
        Returns:
            Best matching Agent or None if no suitable agent found
        """
        # If preferred agent is specified, check it first
        if preferred_agent_id:
            agent = self.get_agent(preferred_agent_id)
            if agent and agent.status == AgentStatus.ACTIVE.value:
                # Check if preferred agent has required capabilities
                if required_capabilities:
                    agent_caps = agent.capabilities or []
                    if all(cap in agent_caps for cap in required_capabilities):
                        return agent
                else:
                    return agent
        
        # Find all active agents
        query = self.db.query(Agent).filter(
            Agent.status == AgentStatus.ACTIVE.value
        )
        
        # Filter by capabilities if specified
        if required_capabilities:
            capability_filters = []
            for cap in required_capabilities:
                capability_filters.append(Agent.capabilities.contains([cap]))
            
            if capability_filters:
                query = query.filter(or_(*capability_filters))
        
        candidates = query.all()
        
        if not candidates:
            return None
        
        # Score candidates based on:
        # 1. Number of matching capabilities (more is better)
        # 2. Success rate (higher is better)
        # 3. Average execution time (lower is better)
        def score_agent(agent: Agent) -> float:
            agent_caps = agent.capabilities or []
            
            # Capability score: count matching capabilities
            capability_score = 0.0
            if required_capabilities:
                matching_caps = sum(1 for cap in required_capabilities if cap in agent_caps)
                capability_score = matching_caps / len(required_capabilities)
            else:
                # If no specific capabilities required, prefer agents with more capabilities
                capability_score = min(1.0, len(agent_caps) / 5.0)  # Normalize to 0-1
            
            # Success rate score
            success_score = 0.5  # Default neutral score
            if agent.success_rate:
                try:
                    # Parse percentage string like "85.50%" to float
                    success_rate = float(str(agent.success_rate).rstrip('%')) / 100.0
                    success_score = success_rate
                except (ValueError, AttributeError):
                    pass
            elif agent.total_tasks_executed > 0:
                success_score = agent.successful_tasks / agent.total_tasks_executed
            
            # Execution time score (inverse - faster is better)
            time_score = 1.0
            if agent.average_execution_time and agent.average_execution_time > 0:
                # Normalize: assume 300 seconds is "slow"
                time_score = max(0.1, 1.0 - (agent.average_execution_time / 300.0))
            
            # Weighted combination: capabilities (50%), success (30%), time (20%)
            total_score = (
                capability_score * 0.5 +
                success_score * 0.3 +
                time_score * 0.2
            )
            
            return total_score
        
        # Sort by score (highest first)
        scored_agents = [(agent, score_agent(agent)) for agent in candidates]
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Return best agent
        return scored_agents[0][0] if scored_agents else None
    
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
    
    def create_agent_version(
        self,
        agent_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        model_preference: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """
        Create a new version of an existing agent
        
        Args:
            agent_id: ID of the parent agent
            name: New name (if different from parent)
            description: New description (if different from parent)
            system_prompt: New system prompt (if different from parent)
            capabilities: New capabilities (if different from parent)
            model_preference: New model preference (if different from parent)
            **kwargs: Additional properties to override
            
        Returns:
            New Agent version
        """
        parent_agent = self.get_agent(agent_id)
        if not parent_agent:
            raise ValueError(f"Parent agent {agent_id} not found")
        
        # Find root agent to get the latest version number
        root_agent = parent_agent
        while root_agent.parent_agent_id:
            root_agent = self.get_agent(root_agent.parent_agent_id)
            if not root_agent:
                break
        
        if not root_agent:
            root_agent = parent_agent
        
        # Get the latest version number from all versions
        latest_version = root_agent.version
        child_versions = self.db.query(Agent).filter(
            Agent.parent_agent_id == root_agent.id
        ).all()
        if child_versions:
            latest_version = max(v.version for v in child_versions)
        
        new_version = latest_version + 1
        
        # Generate unique name if not provided
        if not name:
            base_name = root_agent.name
            # Remove version suffix if exists
            if base_name.endswith(f"_v{root_agent.version}"):
                base_name = base_name[:-len(f"_v{root_agent.version}")]
            name = f"{base_name}_v{new_version}"
        
        # Ensure name is unique
        existing = self.db.query(Agent).filter(Agent.name == name).first()
        if existing:
            # Add timestamp to make it unique
            import time
            name = f"{name}_{int(time.time())}"
        
        # Create new agent based on parent
        new_agent = Agent(
            name=name,
            description=description or parent_agent.description,
            system_prompt=system_prompt or parent_agent.system_prompt,
            capabilities=capabilities or parent_agent.capabilities,
            model_preference=model_preference or parent_agent.model_preference,
            temperature=kwargs.get('temperature', parent_agent.temperature),
            parent_agent_id=root_agent.id,
            version=new_version,
            status=AgentStatus.DRAFT.value,
            created_by=kwargs.get('created_by', parent_agent.created_by),
            identity_id=parent_agent.identity_id,
            security_policies=kwargs.get('security_policies', parent_agent.security_policies),
            allowed_actions=kwargs.get('allowed_actions', parent_agent.allowed_actions),
            forbidden_actions=kwargs.get('forbidden_actions', parent_agent.forbidden_actions),
            max_concurrent_tasks=kwargs.get('max_concurrent_tasks', parent_agent.max_concurrent_tasks),
            rate_limit_per_minute=kwargs.get('rate_limit_per_minute', parent_agent.rate_limit_per_minute),
            memory_limit_mb=kwargs.get('memory_limit_mb', parent_agent.memory_limit_mb),
            agent_metadata=kwargs.get('agent_metadata', parent_agent.agent_metadata),
            tags=kwargs.get('tags', parent_agent.tags)
        )
        
        self.db.add(new_agent)
        self.db.commit()
        self.db.refresh(new_agent)
        
        logger.info(
            f"Created new version {new_agent.version} of agent {parent_agent.name}",
            extra={
                "parent_agent_id": str(agent_id),
                "new_agent_id": str(new_agent.id),
                "version": new_agent.version
            }
        )
        
        return new_agent
    
    def get_agent_versions(self, agent_id: UUID) -> List[Agent]:
        """
        Get all versions of an agent (including the agent itself)
        
        Args:
            agent_id: Agent ID (can be any version)
            
        Returns:
            List of agents ordered by version (oldest first)
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return []
        
        # Find root agent (agent without parent)
        root_agent = agent
        while root_agent.parent_agent_id:
            root_agent = self.get_agent(root_agent.parent_agent_id)
            if not root_agent:
                break
        
        if not root_agent:
            root_agent = agent
        
        # Get all versions (root and all children)
        versions = [root_agent]
        
        # Find all child versions
        child_versions = self.db.query(Agent).filter(
            Agent.parent_agent_id == root_agent.id
        ).order_by(Agent.version.asc()).all()
        
        versions.extend(child_versions)
        
        return versions
    
    def rollback_to_version(self, agent_id: UUID, target_version: int) -> Agent:
        """
        Rollback agent to a previous version
        
        This creates a new version based on the target version
        
        Args:
            agent_id: Current agent ID
            target_version: Version to rollback to
            
        Returns:
            New agent version based on target version
        """
        current_agent = self.get_agent(agent_id)
        if not current_agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Get all versions
        all_versions = self.get_agent_versions(agent_id)
        
        # Find target version
        target_agent = None
        for version_agent in all_versions:
            if version_agent.version == target_version:
                target_agent = version_agent
                break
        
        if not target_agent:
            raise ValueError(f"Version {target_version} not found for agent {agent_id}")
        
        # Create new version based on target
        new_version = self.create_agent_version(
            agent_id=current_agent.parent_agent_id or current_agent.id,
            name=target_agent.name,
            description=target_agent.description,
            system_prompt=target_agent.system_prompt,
            capabilities=target_agent.capabilities,
            model_preference=target_agent.model_preference,
            temperature=target_agent.temperature,
            security_policies=target_agent.security_policies,
            allowed_actions=target_agent.allowed_actions,
            forbidden_actions=target_agent.forbidden_actions,
            max_concurrent_tasks=target_agent.max_concurrent_tasks,
            rate_limit_per_minute=target_agent.rate_limit_per_minute,
            memory_limit_mb=target_agent.memory_limit_mb,
            agent_metadata=target_agent.agent_metadata,
            tags=target_agent.tags,
            created_by=f"rollback_from_v{current_agent.version}"
        )
        
        logger.info(
            f"Rolled back agent {current_agent.name} from v{current_agent.version} to v{target_version} (created v{new_version.version})",
            extra={
                "current_agent_id": str(agent_id),
                "target_version": target_version,
                "new_version_id": str(new_version.id),
                "new_version": new_version.version
            }
        )
        
        return new_version
    
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
    
    def find_agent_for_task(
        self,
        required_capabilities: List[str],
        preferred_agent_id: Optional[UUID] = None
    ) -> Optional[Agent]:
        """
        Find the best agent for a task based on capabilities and performance
        
        Args:
            required_capabilities: List of required capabilities (e.g., ["code_generation", "planning"])
            preferred_agent_id: Optional preferred agent ID to check first
            
        Returns:
            Best matching Agent or None if no suitable agent found
        """
        # If preferred agent is specified, check it first
        if preferred_agent_id:
            agent = self.get_agent(preferred_agent_id)
            if agent and agent.status == AgentStatus.ACTIVE.value:
                # Check if preferred agent has required capabilities
                agent_caps = agent.capabilities or []
                if all(cap in agent_caps for cap in required_capabilities):
                    return agent
        
        # Find all active agents with at least one required capability
        query = self.db.query(Agent).filter(
            Agent.status == AgentStatus.ACTIVE.value
        )
        
        # Filter by capabilities (agent must have at least one required capability)
        capability_filters = []
        for cap in required_capabilities:
            capability_filters.append(Agent.capabilities.contains([cap]))
        
        if capability_filters:
            from sqlalchemy import or_
            query = query.filter(or_(*capability_filters))
        
        candidates = query.all()
        
        if not candidates:
            return None
        
        # Score candidates based on:
        # 1. Number of matching capabilities (more is better)
        # 2. Success rate (higher is better)
        # 3. Average execution time (lower is better, if tasks executed)
        def score_agent(agent: Agent) -> float:
            agent_caps = agent.capabilities or []
            
            # Count matching capabilities
            matching_caps = sum(1 for cap in required_capabilities if cap in agent_caps)
            capability_score = matching_caps / len(required_capabilities) if required_capabilities else 0
            
            # Success rate score (convert percentage string to float)
            success_score = 0.0
            if agent.success_rate:
                try:
                    # Parse percentage string like "85.50%" to float
                    success_rate = float(agent.success_rate.rstrip('%')) / 100.0
                    success_score = success_rate
                except (ValueError, AttributeError):
                    pass
            elif agent.total_tasks_executed > 0:
                # Calculate from metrics if available
                success_score = agent.successful_tasks / agent.total_tasks_executed
            
            # Execution time score (inverse - faster is better)
            time_score = 1.0
            if agent.average_execution_time and agent.average_execution_time > 0:
                # Normalize: assume 300 seconds is "slow", 0 is "fast"
                # Score decreases as time increases
                time_score = max(0.1, 1.0 - (agent.average_execution_time / 300.0))
            
            # Weighted combination: capabilities (50%), success (30%), time (20%)
            total_score = (
                capability_score * 0.5 +
                success_score * 0.3 +
                time_score * 0.2
            )
            
            return total_score
        
        # Sort by score (highest first)
        scored_agents = [(agent, score_agent(agent)) for agent in candidates]
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Return best agent
        return scored_agents[0][0] if scored_agents else None
    
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

