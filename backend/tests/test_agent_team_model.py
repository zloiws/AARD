"""
Tests for AgentTeam model
"""
import pytest
from uuid import uuid4
from datetime import datetime

from app.models.agent_team import AgentTeam, CoordinationStrategy, TeamStatus
from app.models.agent import Agent, AgentStatus


def test_agent_team_creation(db):
    """Test creating an agent team"""
    team = AgentTeam(
        name="Test Team",
        description="A test team",
        coordination_strategy=CoordinationStrategy.COLLABORATIVE.value,
        roles={"developer": "Writes code", "reviewer": "Reviews code"},
        status=TeamStatus.ACTIVE.value
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    assert team.id is not None
    assert team.name == "Test Team"
    assert team.description == "A test team"
    assert team.coordination_strategy == CoordinationStrategy.COLLABORATIVE.value
    assert team.status == TeamStatus.ACTIVE.value
    assert team.roles == {"developer": "Writes code", "reviewer": "Reviews code"}


def test_agent_team_unique_name(db_session):
    """Test that team names must be unique"""
    team1 = AgentTeam(name="Unique Team")
    team2 = AgentTeam(name="Unique Team")
    
    db.add(team1)
    db.commit()
    
    db.add(team2)
    with pytest.raises(Exception):  # IntegrityError or similar
        db.commit()


def test_agent_team_defaults(db_session):
    """Test default values for agent team"""
    team = AgentTeam(name="Default Team")
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    assert team.coordination_strategy == CoordinationStrategy.COLLABORATIVE.value
    assert team.status == TeamStatus.DRAFT.value
    assert team.created_at is not None
    assert team.updated_at is not None


def test_agent_team_to_dict(db_session):
    """Test converting team to dictionary"""
    team = AgentTeam(
        name="Dict Test Team",
        description="Testing to_dict",
        roles={"role1": "Description 1"},
        coordination_strategy=CoordinationStrategy.PARALLEL.value
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    team_dict = team.to_dict()
    
    assert team_dict["name"] == "Dict Test Team"
    assert team_dict["description"] == "Testing to_dict"
    assert team_dict["coordination_strategy"] == CoordinationStrategy.PARALLEL.value
    assert team_dict["roles"] == {"role1": "Description 1"}
    assert "id" in team_dict
    assert "created_at" in team_dict
    assert "agent_count" in team_dict


def test_agent_team_coordination_strategies(db_session):
    """Test all coordination strategies"""
    strategies = [
        CoordinationStrategy.SEQUENTIAL,
        CoordinationStrategy.PARALLEL,
        CoordinationStrategy.HIERARCHICAL,
        CoordinationStrategy.COLLABORATIVE,
        CoordinationStrategy.PIPELINE
    ]
    
    for i, strategy in enumerate(strategies):
        team = AgentTeam(
            name=f"Team {strategy.value}",
            coordination_strategy=strategy.value
        )
        db.add(team)
    
    db.commit()
    
    # Verify all teams were created
    teams = db.query(AgentTeam).all()
    assert len(teams) == len(strategies)


def test_agent_team_status_enum(db_session):
    """Test team status values"""
    statuses = [
        TeamStatus.DRAFT,
        TeamStatus.ACTIVE,
        TeamStatus.PAUSED,
        TeamStatus.DEPRECATED
    ]
    
    for i, status in enumerate(statuses):
        team = AgentTeam(
            name=f"Team {status.value}",
            status=status.value
        )
        db.add(team)
    
    db.commit()
    
    # Verify all teams were created
    teams = db.query(AgentTeam).all()
    assert len(teams) == len(statuses)

