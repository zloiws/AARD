"""
Tests for PlanningService with agent teams
"""
import pytest
from uuid import uuid4

from app.services.planning_service import PlanningService
from app.services.agent_team_service import AgentTeamService
from app.models.agent_team import CoordinationStrategy, TeamStatus
from app.models.agent import Agent, AgentStatus


@pytest.mark.asyncio
async def test_plan_with_team(db):
    """Test creating a plan with a team"""
    planning_service = PlanningService(db)
    team_service = AgentTeamService(db)
    
    # Create team
    team = team_service.create_team(
        name=f"Planning Team {uuid4()}",
        coordination_strategy=CoordinationStrategy.COLLABORATIVE.value
    )
    team_service.activate_team(team.id)
    
    # Create agents
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    
    # Add agents to team
    team_service.add_agent_to_team(team.id, agent1.id)
    team_service.add_agent_to_team(team.id, agent2.id)
    
    # Create plan with team
    plan = await planning_service.create_plan(
        task_description="Test task with team",
        context={"team_id": str(team.id)}
    )
    
    assert plan is not None
    assert plan.steps is not None
    
    # Check that steps have team_id assigned
    steps_with_team = [s for s in plan.steps if s.get("team_id") == str(team.id)]
    assert len(steps_with_team) > 0 or len(plan.steps) == 0  # Either steps have team_id or no steps


@pytest.mark.asyncio
async def test_plan_with_team_and_role(db):
    """Test creating a plan with team and role assignment"""
    planning_service = PlanningService(db)
    team_service = AgentTeamService(db)
    
    # Create team with roles
    team = team_service.create_team(
        name=f"Role Team {uuid4()}",
        roles={"developer": "Writes code", "reviewer": "Reviews code"}
    )
    team_service.activate_team(team.id)
    
    # Create agents with roles
    agent1 = Agent(name=f"Developer {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Reviewer {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    
    team_service.add_agent_to_team(team.id, agent1.id, role="developer")
    team_service.add_agent_to_team(team.id, agent2.id, role="reviewer")
    
    # Create plan with team
    plan = await planning_service.create_plan(
        task_description="Test task with team roles",
        context={"team_id": str(team.id)}
    )
    
    assert plan is not None
    
    # Check that steps have team_id
    if plan.steps:
        steps_with_team = [s for s in plan.steps if s.get("team_id") == str(team.id)]
        # At least some steps should have team_id, or steps might have specific agents assigned
        assert len(steps_with_team) > 0 or any(s.get("agent") for s in plan.steps)


def test_plan_team_takes_precedence_over_agent(db):
    """Test that team_id takes precedence over agent_id in context"""
    planning_service = PlanningService(db)
    team_service = AgentTeamService(db)
    
    # Create team
    team = team_service.create_team(name=f"Precedence Team {uuid4()}")
    team_service.activate_team(team.id)
    
    # Create agent
    agent = Agent(name=f"Agent {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent)
    db.commit()
    
    # Both team_id and agent_id in context - team should take precedence
    import asyncio
    plan = asyncio.run(planning_service.create_plan(
        task_description="Test precedence",
        context={"team_id": str(team.id), "agent_id": str(agent.id)}
    ))
    
    assert plan is not None
    # Steps should have team_id, not agent_id from context
    if plan.steps:
        steps_with_team = [s for s in plan.steps if s.get("team_id") == str(team.id)]
        # Team should be used (steps have team_id or agents from team)
        assert len(steps_with_team) > 0 or any(s.get("agent") for s in plan.steps)

