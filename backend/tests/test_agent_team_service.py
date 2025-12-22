"""
Tests for AgentTeamService
"""
from uuid import uuid4

import pytest
from app.models.agent import Agent, AgentStatus
from app.models.agent_team import AgentTeam, CoordinationStrategy, TeamStatus
from app.services.agent_team_service import AgentTeamService


def test_create_team(db):
    """Test creating a team"""
    service = AgentTeamService(db)
    
    team_name = f"Test Team {uuid4()}"
    team = service.create_team(
        name=team_name,
        description="A test team",
        coordination_strategy=CoordinationStrategy.COLLABORATIVE.value,
        roles={"developer": "Writes code", "reviewer": "Reviews code"}
    )
    
    assert team.id is not None
    assert team.name == team_name
    assert team.description == "A test team"
    assert team.coordination_strategy == CoordinationStrategy.COLLABORATIVE.value
    assert team.status == TeamStatus.DRAFT.value


def test_create_team_duplicate_name(db):
    """Test that duplicate team names are rejected"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    unique_name = f"Unique Team {uuid4()}"
    service.create_team(name=unique_name)
    
    with pytest.raises(ValueError, match="already exists"):
        service.create_team(name=unique_name)


def test_get_team(db):
    """Test getting a team by ID"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team_name = f"Get Test Team {uuid4()}"
    created_team = service.create_team(name=team_name)
    retrieved_team = service.get_team(created_team.id)
    
    assert retrieved_team is not None
    assert retrieved_team.id == created_team.id
    assert retrieved_team.name == team_name


def test_get_team_not_found(db):
    """Test getting non-existent team"""
    service = AgentTeamService(db)
    
    team = service.get_team(uuid4())
    assert team is None


def test_list_teams(db):
    """Test listing teams"""
    service = AgentTeamService(db)
    
    # Create multiple teams
    team1 = service.create_team(name=f"Team 1 {uuid4()}")
    team2 = service.create_team(name=f"Team 2 {uuid4()}")
    team3 = service.create_team(name=f"Team 3 {uuid4()}")
    
    teams = service.list_teams()
    
    # Should include our teams (may have others from previous tests)
    team_ids = {t.id for t in teams}
    assert team1.id in team_ids
    assert team2.id in team_ids
    assert team3.id in team_ids


def test_list_teams_by_status(db):
    """Test listing teams filtered by status"""
    service = AgentTeamService(db)
    
    team1 = service.create_team(name=f"Active Team {uuid4()}")
    service.activate_team(team1.id)
    
    team2 = service.create_team(name=f"Draft Team {uuid4()}")
    # team2 stays in draft
    
    active_teams = service.list_teams(status=TeamStatus.ACTIVE.value)
    active_ids = {t.id for t in active_teams}
    assert team1.id in active_ids
    assert team2.id not in active_ids


def test_update_team(db):
    """Test updating a team"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Update Test Team {uuid4()}")
    
    updated = service.update_team(
        team.id,
        description="Updated description",
        coordination_strategy=CoordinationStrategy.PARALLEL.value,
        status=TeamStatus.ACTIVE.value
    )
    
    assert updated is not None
    assert updated.description == "Updated description"
    assert updated.coordination_strategy == CoordinationStrategy.PARALLEL.value
    assert updated.status == TeamStatus.ACTIVE.value


def test_add_agent_to_team(db):
    """Test adding an agent to a team"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    # Create team and agent
    team = service.create_team(name=f"Add Agent Team {uuid4()}")
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    
    # Add agent to team
    result = service.add_agent_to_team(team.id, agent.id, role="developer")
    
    assert result is True
    
    # Verify agent is in team
    agents = service.get_team_agents(team.id)
    assert len(agents) == 1
    assert agents[0]["agent_id"] == str(agent.id)
    assert agents[0]["role"] == "developer"


def test_add_agent_to_team_duplicate(db):
    """Test that adding duplicate agent is rejected"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Duplicate Agent Team {uuid4()}")
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    
    service.add_agent_to_team(team.id, agent.id)
    
    with pytest.raises(ValueError, match="already in team"):
        service.add_agent_to_team(team.id, agent.id)


def test_remove_agent_from_team(db):
    """Test removing an agent from a team"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Remove Agent Team {uuid4()}")
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    
    service.add_agent_to_team(team.id, agent.id)
    
    # Verify agent is in team
    agents = service.get_team_agents(team.id)
    assert len(agents) == 1
    
    # Remove agent
    result = service.remove_agent_from_team(team.id, agent.id)
    assert result is True
    
    # Verify agent is removed
    agents = service.get_team_agents(team.id)
    assert len(agents) == 0


def test_set_team_lead(db):
    """Test setting team lead"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Lead Team {uuid4()}")
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    
    service.add_agent_to_team(team.id, agent1.id)
    service.add_agent_to_team(team.id, agent2.id)
    
    # Set agent1 as lead
    result = service.set_team_lead(team.id, agent1.id)
    assert result is True
    
    lead = service.get_team_lead(team.id)
    assert lead is not None
    assert lead.id == agent1.id
    
    # Set agent2 as lead (should unset agent1)
    service.set_team_lead(team.id, agent2.id)
    lead = service.get_team_lead(team.id)
    assert lead.id == agent2.id


def test_get_agents_by_role(db):
    """Test getting agents by role"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Role Team {uuid4()}")
    agent1 = Agent(name=f"Developer {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Reviewer {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent3 = Agent(name=f"Developer 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    
    db.add(agent1)
    db.add(agent2)
    db.add(agent3)
    db.commit()
    
    service.add_agent_to_team(team.id, agent1.id, role="developer")
    service.add_agent_to_team(team.id, agent2.id, role="reviewer")
    service.add_agent_to_team(team.id, agent3.id, role="developer")
    
    developers = service.get_agents_by_role(team.id, "developer")
    assert len(developers) == 2
    developer_ids = {a.id for a in developers}
    assert agent1.id in developer_ids
    assert agent3.id in developer_ids
    assert agent2.id not in developer_ids


def test_activate_team(db):
    """Test activating a team"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Activate Team {uuid4()}")
    assert team.status == TeamStatus.DRAFT.value
    
    result = service.activate_team(team.id)
    assert result is True
    
    updated_team = service.get_team(team.id)
    assert updated_team.status == TeamStatus.ACTIVE.value


def test_pause_team(db):
    """Test pausing a team"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Pause Team {uuid4()}")
    service.activate_team(team.id)
    
    result = service.pause_team(team.id)
    assert result is True
    
    updated_team = service.get_team(team.id)
    assert updated_team.status == TeamStatus.PAUSED.value


def test_delete_team(db):
    """Test deleting a team"""
    from uuid import uuid4
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Delete Team {uuid4()}")
    agent = Agent(name=f"Agent {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent)
    db.commit()
    
    service.add_agent_to_team(team.id, agent.id)
    
    result = service.delete_team(team.id)
    assert result is True
    
    deleted_team = service.get_team(team.id)
    assert deleted_team is None

