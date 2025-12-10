"""
Agent Team model for AARD platform
Represents teams of agents that work together on tasks
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List, Any
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, JSON, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class CoordinationStrategy(str, Enum):
    """Coordination strategy for agent teams"""
    SEQUENTIAL = "sequential"  # Agents work one after another
    PARALLEL = "parallel"  # Agents work simultaneously
    HIERARCHICAL = "hierarchical"  # One agent coordinates others
    COLLABORATIVE = "collaborative"  # Agents collaborate and share results
    PIPELINE = "pipeline"  # Agents work in a pipeline fashion


class TeamStatus(str, Enum):
    """Team status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"


# Intermediate table for many-to-many relationship between teams and agents
agent_team_association = Table(
    'agent_team_associations',
    Base.metadata,
    Column('team_id', PGUUID(as_uuid=True), ForeignKey('agent_teams.id'), primary_key=True),
    Column('agent_id', PGUUID(as_uuid=True), ForeignKey('agents.id'), primary_key=True),
    Column('role', String(100), nullable=True),  # Role of agent in this team
            Column('assigned_at', DateTime, default=lambda: datetime.now(timezone.utc), nullable=False),
    Column('is_lead', Boolean, default=False, nullable=False),  # Is this agent the team lead?
)


class AgentTeam(Base):
    """Agent Team model - represents a team of agents working together"""
    __tablename__ = "agent_teams"
    
    # Primary identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Team configuration
    roles = Column(JSONB, nullable=True)  # Dictionary of role_name -> role_description
    coordination_strategy = Column(String(50), nullable=False, default=CoordinationStrategy.COLLABORATIVE.value)
    
    # Status and lifecycle
    status = Column(String(50), nullable=False, default=TeamStatus.DRAFT.value)
    created_by = Column(String(255), nullable=True)  # User who created the team
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Team metadata
    team_metadata = Column(JSONB, nullable=True)  # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name conflict)
    
    # Relationships
    agents = relationship(
        "Agent",
        secondary=agent_team_association,
        backref="teams",
        lazy="dynamic"
    )
    
    def __repr__(self):
        return f"<AgentTeam(id={self.id}, name={self.name}, strategy={self.coordination_strategy})>"
    
    def get_agents_by_role(self, role: str) -> List:
        """Get all agents with a specific role in this team"""
        from app.models.agent import Agent
        return [
            agent for agent in self.agents
            if self._get_agent_role(agent.id) == role
        ]
    
    def get_team_lead(self):
        """Get the team lead agent"""
        from app.models.agent import Agent
        from sqlalchemy.orm import Session
        
        # Query the association table to find the lead
        # This requires a database session, so we'll handle it in the service layer
        return None  # Will be implemented in AgentTeamService
    
    def _get_agent_role(self, agent_id: UUID) -> Optional[str]:
        """Get role of an agent in this team (helper method)"""
        # This will be implemented using the association table
        # For now, return None - will be handled in service layer
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert team to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "roles": self.roles,
            "coordination_strategy": self.coordination_strategy,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "agent_count": self.agents.count() if hasattr(self.agents, 'count') else len(list(self.agents)),
            "metadata": self.team_metadata  # Map to 'metadata' in API response
        }

