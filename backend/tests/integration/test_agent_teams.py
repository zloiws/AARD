"""
Integration tests for Agent Teams (Phase 7.1)
"""
import pytest
from uuid import uuid4

from app.services.agent_team_service import AgentTeamService
from app.models.agent_team import AgentTeam, CoordinationStrategy, TeamStatus
from app.models.agent import Agent, AgentStatus


def test_create_team_with_agents(db):
    """Test creating a team and adding multiple agents"""
    service = AgentTeamService(db)
    
    # Create team
    team = service.create_team(
        name=f"Integration Team {uuid4()}",
        description="Integration test team",
        roles={"developer": "Writes code", "reviewer": "Reviews code", "tester": "Tests code"}
    )
    
    # Create agents
    agent1 = Agent(name=f"Developer Agent {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Reviewer Agent {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent3 = Agent(name=f"Tester Agent {uuid4()}", status=AgentStatus.ACTIVE.value)
    
    db.add(agent1)
    db.add(agent2)
    db.add(agent3)
    db.commit()
    
    # Add agents to team with roles
    service.add_agent_to_team(team.id, agent1.id, role="developer")
    service.add_agent_to_team(team.id, agent2.id, role="reviewer")
    service.add_agent_to_team(team.id, agent3.id, role="tester")
    
    # Verify agents are in team
    agents = service.get_team_agents(team.id)
    assert len(agents) == 3
    
    # Verify roles
    developers = service.get_agents_by_role(team.id, "developer")
    assert len(developers) == 1
    assert developers[0].id == agent1.id
    
    reviewers = service.get_agents_by_role(team.id, "reviewer")
    assert len(reviewers) == 1
    assert reviewers[0].id == agent2.id


def test_team_lead_management(db):
    """Test setting and changing team lead"""
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Lead Team {uuid4()}")
    
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    
    db.add(agent1)
    db.add(agent2)
    db.commit()
    
    # Add agents
    service.add_agent_to_team(team.id, agent1.id)
    service.add_agent_to_team(team.id, agent2.id)
    
    # Set agent1 as lead
    service.set_team_lead(team.id, agent1.id)
    lead = service.get_team_lead(team.id)
    assert lead.id == agent1.id
    
    # Change lead to agent2
    service.set_team_lead(team.id, agent2.id)
    lead = service.get_team_lead(team.id)
    assert lead.id == agent2.id
    assert lead.id != agent1.id


def test_team_lifecycle(db):
    """Test team lifecycle: create -> activate -> pause -> activate"""
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Lifecycle Team {uuid4()}")
    assert team.status == TeamStatus.DRAFT.value
    
    # Activate
    service.activate_team(team.id)
    team = service.get_team(team.id)
    assert team.status == TeamStatus.ACTIVE.value
    
    # Pause
    service.pause_team(team.id)
    team = service.get_team(team.id)
    assert team.status == TeamStatus.PAUSED.value
    
    # Activate again
    service.activate_team(team.id)
    team = service.get_team(team.id)
    assert team.status == TeamStatus.ACTIVE.value


def test_team_with_different_strategies(db):
    """Test teams with different coordination strategies"""
    service = AgentTeamService(db)
    
    strategies = [
        CoordinationStrategy.SEQUENTIAL,
        CoordinationStrategy.PARALLEL,
        CoordinationStrategy.HIERARCHICAL,
        CoordinationStrategy.COLLABORATIVE,
        CoordinationStrategy.PIPELINE
    ]
    
    teams = []
    for strategy in strategies:
        team = service.create_team(
            name=f"Strategy Team {strategy.value} {uuid4()}",
            coordination_strategy=strategy.value
        )
        teams.append(team)
    
    # Verify all teams created
    assert len(teams) == len(strategies)
    
    # Verify each team has correct strategy
    for team, strategy in zip(teams, strategies):
        retrieved = service.get_team(team.id)
        assert retrieved.coordination_strategy == strategy.value


def test_remove_agent_and_re_add(db):
    """Test removing agent from team and re-adding"""
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Re-add Team {uuid4()}")
    agent = Agent(name=f"Agent {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent)
    db.commit()
    
    # Add agent
    service.add_agent_to_team(team.id, agent.id, role="developer")
    agents = service.get_team_agents(team.id)
    assert len(agents) == 1
    
    # Remove agent
    service.remove_agent_from_team(team.id, agent.id)
    agents = service.get_team_agents(team.id)
    assert len(agents) == 0
    
    # Re-add agent
    service.add_agent_to_team(team.id, agent.id, role="reviewer")
    agents = service.get_team_agents(team.id)
    assert len(agents) == 1
    assert agents[0]["role"] == "reviewer"


def test_update_agent_role_in_team(db):
    """Test updating agent role in team"""
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Update Role Team {uuid4()}")
    agent = Agent(name=f"Agent {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent)
    db.commit()
    
    # Add with initial role
    service.add_agent_to_team(team.id, agent.id, role="junior")
    
    # Update role
    service.update_agent_role(team.id, agent.id, role="senior")
    
    agents = service.get_team_agents(team.id)
    assert agents[0]["role"] == "senior"


def test_delete_team_with_agents(db):
    """Test deleting team removes agent associations"""
    service = AgentTeamService(db)
    
    team = service.create_team(name=f"Delete Team {uuid4()}")
    
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    
    db.add(agent1)
    db.add(agent2)
    db.commit()
    
    service.add_agent_to_team(team.id, agent1.id)
    service.add_agent_to_team(team.id, agent2.id)
    
    # Verify agents are in team
    agents = service.get_team_agents(team.id)
    assert len(agents) == 2
    
    # Delete team
    service.delete_team(team.id)
    
    # Verify team is deleted
    deleted_team = service.get_team(team.id)
    assert deleted_team is None
    
    # Verify agents still exist (only team association is deleted)
    agent1_check = db.query(Agent).filter(Agent.id == agent1.id).first()
    agent2_check = db.query(Agent).filter(Agent.id == agent2.id).first()
    assert agent1_check is not None
    assert agent2_check is not None

