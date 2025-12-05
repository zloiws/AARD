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
    from uuid import uuid4
    team = AgentTeam(
        name=f"Test Team {uuid4()}",
        description="A test team",
        coordination_strategy=CoordinationStrategy.COLLABORATIVE.value,
        roles={"developer": "Writes code", "reviewer": "Reviews code"},
        status=TeamStatus.ACTIVE.value
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    assert team.id is not None
    assert team.name.startswith("Test Team")
    assert team.description == "A test team"
    assert team.coordination_strategy == CoordinationStrategy.COLLABORATIVE.value
    assert team.status == TeamStatus.ACTIVE.value
    assert team.roles == {"developer": "Writes code", "reviewer": "Reviews code"}


def test_agent_team_unique_name(db):
    """Test that team names must be unique"""
    from uuid import uuid4
    unique_name = f"Unique Team {uuid4()}"
    team1 = AgentTeam(name=unique_name)
    team2 = AgentTeam(name=unique_name)
    
    db.add(team1)
    db.commit()
    
    db.add(team2)
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_agent_team_defaults(db):
    """Test default values for agent team"""
    from uuid import uuid4
    team = AgentTeam(name=f"Default Team {uuid4()}")
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    assert team.coordination_strategy == CoordinationStrategy.COLLABORATIVE.value
    assert team.status == TeamStatus.DRAFT.value
    assert team.created_at is not None
    assert team.updated_at is not None


def test_agent_team_to_dict(db):
    """Test converting team to dictionary"""
    from uuid import uuid4
    team = AgentTeam(
        name=f"Dict Test Team {uuid4()}",
        description="Testing to_dict",
        roles={"role1": "Description 1"},
        coordination_strategy=CoordinationStrategy.PARALLEL.value
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    team_dict = team.to_dict()
    
    assert team_dict["name"].startswith("Dict Test Team")
    assert team_dict["description"] == "Testing to_dict"
    assert team_dict["coordination_strategy"] == CoordinationStrategy.PARALLEL.value
    assert team_dict["roles"] == {"role1": "Description 1"}
    assert "id" in team_dict
    assert "created_at" in team_dict
    assert "agent_count" in team_dict


def test_agent_team_coordination_strategies(db):
    """Test all coordination strategies"""
    from uuid import uuid4
    strategies = [
        CoordinationStrategy.SEQUENTIAL,
        CoordinationStrategy.PARALLEL,
        CoordinationStrategy.HIERARCHICAL,
        CoordinationStrategy.COLLABORATIVE,
        CoordinationStrategy.PIPELINE
    ]
    
    team_ids = []
    for i, strategy in enumerate(strategies):
        team = AgentTeam(
            name=f"Team {strategy.value} {uuid4()}",
            coordination_strategy=strategy.value
        )
        db.add(team)
        db.flush()  # Get ID without committing
        team_ids.append(team.id)
    
    db.commit()
    
    # Verify all teams were created (filter by IDs we created)
    teams = db.query(AgentTeam).filter(AgentTeam.id.in_(team_ids)).all()
    assert len(teams) == len(strategies)


def test_agent_team_status_enum(db):
    """Test team status values"""
    from uuid import uuid4
    statuses = [
        TeamStatus.DRAFT,
        TeamStatus.ACTIVE,
        TeamStatus.PAUSED,
        TeamStatus.DEPRECATED
    ]
    
    team_ids = []
    for i, status in enumerate(statuses):
        team = AgentTeam(
            name=f"Team {status.value} {uuid4()}",
            status=status.value
        )
        db.add(team)
        db.flush()  # Get ID without committing
        team_ids.append(team.id)
    
    db.commit()
    
    # Verify all teams were created (filter by IDs we created)
    teams = db.query(AgentTeam).filter(AgentTeam.id.in_(team_ids)).all()
    assert len(teams) == len(statuses)

