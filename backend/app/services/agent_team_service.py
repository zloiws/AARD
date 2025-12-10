"""
Agent Team Service for managing teams of agents
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.agent_team import AgentTeam, CoordinationStrategy, TeamStatus, agent_team_association
from app.models.agent import Agent, AgentStatus
from app.core.logging_config import LoggingConfig
from app.services.a2a_router import A2ARouter
from app.core.a2a_protocol import A2AMessage, A2AMessageType, A2AResponse

logger = LoggingConfig.get_logger(__name__)


class AgentTeamService:
    """Service for managing agent teams"""
    
    def __init__(self, db: Session):
        """
        Initialize Agent Team Service
        
        Args:
            db: Database session
        """
        self.db = db
        self.a2a_router = A2ARouter(db)
    
    def create_team(
        self,
        name: str,
        description: Optional[str] = None,
        coordination_strategy: str = CoordinationStrategy.COLLABORATIVE.value,
        roles: Optional[Dict[str, str]] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentTeam:
        """
        Create a new agent team
        
        Args:
            name: Team name (must be unique)
            description: Team description
            coordination_strategy: Strategy for coordinating agents
            roles: Dictionary of role_name -> role_description
            created_by: User who created the team
            metadata: Additional metadata
            
        Returns:
            Created AgentTeam
            
        Raises:
            ValueError: If team name already exists
        """
        # Check if team with this name already exists
        existing = self.db.query(AgentTeam).filter(AgentTeam.name == name).first()
        if existing:
            raise ValueError(f"Team with name '{name}' already exists")
        
        team = AgentTeam(
            name=name,
            description=description,
            coordination_strategy=coordination_strategy,
            roles=roles or {},
            status=TeamStatus.DRAFT.value,
            created_by=created_by,
            team_metadata=metadata
        )
        
        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)
        
        logger.info(f"Created agent team: {team.id} ({team.name})")
        return team
    
    def get_team(self, team_id: UUID) -> Optional[AgentTeam]:
        """
        Get team by ID
        
        Args:
            team_id: Team ID
            
        Returns:
            AgentTeam or None if not found
        """
        return self.db.query(AgentTeam).filter(AgentTeam.id == team_id).first()
    
    def get_team_by_name(self, name: str) -> Optional[AgentTeam]:
        """
        Get team by name
        
        Args:
            name: Team name
            
        Returns:
            AgentTeam or None if not found
        """
        return self.db.query(AgentTeam).filter(AgentTeam.name == name).first()
    
    def list_teams(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[AgentTeam]:
        """
        List all teams with optional filtering
        
        Args:
            status: Filter by status
            limit: Maximum number of teams to return
            offset: Number of teams to skip
            
        Returns:
            List of AgentTeam
        """
        query = self.db.query(AgentTeam)
        
        if status:
            query = query.filter(AgentTeam.status == status)
        
        query = query.order_by(AgentTeam.created_at.desc())
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def update_team(
        self,
        team_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        coordination_strategy: Optional[str] = None,
        roles: Optional[Dict[str, str]] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[AgentTeam]:
        """
        Update team
        
        Args:
            team_id: Team ID
            name: New team name (must be unique if provided)
            description: New description
            coordination_strategy: New coordination strategy
            roles: New roles dictionary
            status: New status
            metadata: New metadata
            
        Returns:
            Updated AgentTeam or None if not found
            
        Raises:
            ValueError: If new name already exists
        """
        team = self.get_team(team_id)
        if not team:
            return None
        
        if name and name != team.name:
            # Check if new name already exists
            existing = self.db.query(AgentTeam).filter(
                and_(AgentTeam.name == name, AgentTeam.id != team_id)
            ).first()
            if existing:
                raise ValueError(f"Team with name '{name}' already exists")
            team.name = name
        
        if description is not None:
            team.description = description
        
        if coordination_strategy is not None:
            team.coordination_strategy = coordination_strategy
        
        if roles is not None:
            team.roles = roles
        
        if status is not None:
            team.status = status
        
        if metadata is not None:
            team.team_metadata = metadata
        
        team.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(team)
        
        logger.info(f"Updated agent team: {team.id} ({team.name})")
        return team
    
    def delete_team(self, team_id: UUID) -> bool:
        """
        Delete team (and all agent associations)
        
        Args:
            team_id: Team ID
            
        Returns:
            True if deleted, False if not found
        """
        team = self.get_team(team_id)
        if not team:
            return False
        
        # Delete all agent associations (CASCADE should handle this, but explicit is better)
        self.db.execute(
            agent_team_association.delete().where(
                agent_team_association.c.team_id == team_id
            )
        )
        
        self.db.delete(team)
        self.db.commit()
        
        logger.info(f"Deleted agent team: {team_id}")
        return True
    
    def add_agent_to_team(
        self,
        team_id: UUID,
        agent_id: UUID,
        role: Optional[str] = None,
        is_lead: bool = False
    ) -> bool:
        """
        Add agent to team
        
        Args:
            team_id: Team ID
            agent_id: Agent ID
            role: Role of agent in team
            is_lead: Whether agent is team lead
            
        Returns:
            True if added, False if team or agent not found
            
        Raises:
            ValueError: If agent is already in team or if trying to set multiple leads
        """
        team = self.get_team(team_id)
        if not team:
            return False
        
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return False
        
        # Check if agent is already in team
        existing = self.db.execute(
            agent_team_association.select().where(
                and_(
                    agent_team_association.c.team_id == team_id,
                    agent_team_association.c.agent_id == agent_id
                )
            )
        ).first()
        
        if existing:
            raise ValueError(f"Agent {agent_id} is already in team {team_id}")
        
        # If setting as lead, unset other leads
        if is_lead:
            self.db.execute(
                agent_team_association.update().where(
                    and_(
                        agent_team_association.c.team_id == team_id,
                        agent_team_association.c.is_lead == True
                    )
                ).values(is_lead=False)
            )
        
        # Add agent to team
        self.db.execute(
            agent_team_association.insert().values(
                team_id=team_id,
                agent_id=agent_id,
                role=role,
                is_lead=is_lead,
                assigned_at=datetime.now(timezone.utc)
            )
        )
        
        self.db.commit()
        
        logger.info(f"Added agent {agent_id} to team {team_id} with role '{role}'")
        return True
    
    def remove_agent_from_team(self, team_id: UUID, agent_id: UUID) -> bool:
        """
        Remove agent from team
        
        Args:
            team_id: Team ID
            agent_id: Agent ID
            
        Returns:
            True if removed, False if not found
        """
        result = self.db.execute(
            agent_team_association.delete().where(
                and_(
                    agent_team_association.c.team_id == team_id,
                    agent_team_association.c.agent_id == agent_id
                )
            )
        )
        
        self.db.commit()
        
        if result.rowcount > 0:
            logger.info(f"Removed agent {agent_id} from team {team_id}")
            return True
        
        return False
    
    def update_agent_role(
        self,
        team_id: UUID,
        agent_id: UUID,
        role: Optional[str] = None,
        is_lead: Optional[bool] = None
    ) -> bool:
        """
        Update agent's role in team
        
        Args:
            team_id: Team ID
            agent_id: Agent ID
            role: New role
            is_lead: Whether agent is team lead
            
        Returns:
            True if updated, False if not found
        """
        # Check if agent is in team
        existing = self.db.execute(
            agent_team_association.select().where(
                and_(
                    agent_team_association.c.team_id == team_id,
                    agent_team_association.c.agent_id == agent_id
                )
            )
        ).first()
        
        if not existing:
            return False
        
        update_values = {}
        if role is not None:
            update_values['role'] = role
        if is_lead is not None:
            # If setting as lead, unset other leads
            if is_lead:
                self.db.execute(
                    agent_team_association.update().where(
                        and_(
                            agent_team_association.c.team_id == team_id,
                            agent_team_association.c.is_lead == True
                        )
                    ).values(is_lead=False)
                )
            update_values['is_lead'] = is_lead
        
        if update_values:
            self.db.execute(
                agent_team_association.update().where(
                    and_(
                        agent_team_association.c.team_id == team_id,
                        agent_team_association.c.agent_id == agent_id
                    )
                ).values(**update_values)
            )
            self.db.commit()
            
            logger.info(f"Updated agent {agent_id} role in team {team_id}")
            return True
        
        return False
    
    def get_team_agents(self, team_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all agents in team with their roles
        
        Args:
            team_id: Team ID
            
        Returns:
            List of dictionaries with agent info and role
        """
        team = self.get_team(team_id)
        if not team:
            return []
        
        # Query agents with their association data
        results = self.db.execute(
            agent_team_association.select().where(
                agent_team_association.c.team_id == team_id
            )
        ).fetchall()
        
        agents_info = []
        for row in results:
            agent = self.db.query(Agent).filter(Agent.id == row.agent_id).first()
            if agent:
                agents_info.append({
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "agent_status": agent.status,
                    "role": row.role,
                    "is_lead": row.is_lead,
                    "assigned_at": row.assigned_at.isoformat() if row.assigned_at else None
                })
        
        return agents_info
    
    def get_agents_by_role(self, team_id: UUID, role: str) -> List[Agent]:
        """
        Get all agents with a specific role in team
        
        Args:
            team_id: Team ID
            role: Role name
            
        Returns:
            List of Agent
        """
        results = self.db.execute(
            agent_team_association.select().where(
                and_(
                    agent_team_association.c.team_id == team_id,
                    agent_team_association.c.role == role
                )
            )
        ).fetchall()
        
        agent_ids = [row.agent_id for row in results]
        if not agent_ids:
            return []
        
        return self.db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
    
    def get_team_lead(self, team_id: UUID) -> Optional[Agent]:
        """
        Get team lead agent
        
        Args:
            team_id: Team ID
            
        Returns:
            Agent or None if no lead set
        """
        result = self.db.execute(
            agent_team_association.select().where(
                and_(
                    agent_team_association.c.team_id == team_id,
                    agent_team_association.c.is_lead == True
                )
            )
        ).first()
        
        if not result:
            return None
        
        return self.db.query(Agent).filter(Agent.id == result.agent_id).first()
    
    def set_team_lead(self, team_id: UUID, agent_id: UUID) -> bool:
        """
        Set team lead agent
        
        Args:
            team_id: Team ID
            agent_id: Agent ID to set as lead
            
        Returns:
            True if set, False if team or agent not found
        """
        # Check if agent is in team
        existing = self.db.execute(
            agent_team_association.select().where(
                and_(
                    agent_team_association.c.team_id == team_id,
                    agent_team_association.c.agent_id == agent_id
                )
            )
        ).first()
        
        if not existing:
            return False
        
        # Unset other leads
        self.db.execute(
            agent_team_association.update().where(
                and_(
                    agent_team_association.c.team_id == team_id,
                    agent_team_association.c.is_lead == True
                )
            ).values(is_lead=False)
        )
        
        # Set new lead
        self.db.execute(
            agent_team_association.update().where(
                and_(
                    agent_team_association.c.team_id == team_id,
                    agent_team_association.c.agent_id == agent_id
                )
            ).values(is_lead=True)
        )
        
        self.db.commit()
        
        logger.info(f"Set agent {agent_id} as lead for team {team_id}")
        return True
    
    def activate_team(self, team_id: UUID) -> bool:
        """
        Activate team (set status to active)
        
        Args:
            team_id: Team ID
            
        Returns:
            True if activated, False if not found
        """
        team = self.get_team(team_id)
        if not team:
            return False
        
        team.status = TeamStatus.ACTIVE.value
        team.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(team)
        
        logger.info(f"Activated team: {team_id}")
        return True
    
    def pause_team(self, team_id: UUID) -> bool:
        """
        Pause team (set status to paused)
        
        Args:
            team_id: Team ID
            
        Returns:
            True if paused, False if not found
        """
        team = self.get_team(team_id)
        if not team:
            return False
        
        team.status = TeamStatus.PAUSED.value
        team.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(team)
        
        logger.info(f"Paused team: {team_id}")
        return True

