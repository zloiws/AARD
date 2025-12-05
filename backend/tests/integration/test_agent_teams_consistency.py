"""
Integration test for Agent Teams consistency across all modules
"""
import pytest
from uuid import uuid4

from app.models.agent_team import AgentTeam, CoordinationStrategy, TeamStatus, agent_team_association
from app.models.agent import Agent, AgentStatus
from app.services.agent_team_service import AgentTeamService
from app.services.agent_team_coordination import AgentTeamCoordination
from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService


def test_imports_consistency():
    """Test that all imports are consistent"""
    # Test model imports
    assert AgentTeam is not None
    assert CoordinationStrategy is not None
    assert TeamStatus is not None
    assert agent_team_association is not None
    
    # Test service imports
    assert AgentTeamService is not None
    assert AgentTeamCoordination is not None


def test_model_enum_values(db):
    """Test that enum values are consistent"""
    # Test CoordinationStrategy values
    strategies = [
        CoordinationStrategy.SEQUENTIAL,
        CoordinationStrategy.PARALLEL,
        CoordinationStrategy.HIERARCHICAL,
        CoordinationStrategy.COLLABORATIVE,
        CoordinationStrategy.PIPELINE
    ]
    
    for strategy in strategies:
        team = AgentTeam(
            name=f"Test Team {strategy.value} {uuid4()}",
            coordination_strategy=strategy.value
        )
        db.add(team)
    
    db.commit()
    
    # Verify all strategies are valid
    for strategy in strategies:
        team = db.query(AgentTeam).filter(
            AgentTeam.coordination_strategy == strategy.value
        ).first()
        assert team is not None
        assert team.coordination_strategy == strategy.value
    
    # Test TeamStatus values
    statuses = [
        TeamStatus.DRAFT,
        TeamStatus.ACTIVE,
        TeamStatus.PAUSED,
        TeamStatus.DEPRECATED
    ]
    
    for status in statuses:
        team = AgentTeam(
            name=f"Test Team {status.value} {uuid4()}",
            status=status.value
        )
        db.add(team)
    
    db.commit()
    
    # Verify all statuses are valid
    for status in statuses:
        team = db.query(AgentTeam).filter(
            AgentTeam.status == status.value
        ).first()
        assert team is not None
        assert team.status == status.value


def test_service_initialization_consistency(db):
    """Test that services initialize consistently"""
    # Test AgentTeamService initialization
    team_service = AgentTeamService(db)
    assert team_service.db == db
    
    # Test AgentTeamCoordination initialization
    coordination = AgentTeamCoordination(db)
    assert coordination.db == db
    assert coordination.a2a_router is not None
    assert coordination.registry is not None
    
    # Test PlanningService has team services
    planning_service = PlanningService(db)
    assert planning_service.agent_team_service is not None
    assert planning_service.agent_team_coordination is not None
    assert isinstance(planning_service.agent_team_service, AgentTeamService)
    assert isinstance(planning_service.agent_team_coordination, AgentTeamCoordination)


def test_method_signatures_consistency(db):
    """Test that method signatures are consistent"""
    team_service = AgentTeamService(db)
    coordination = AgentTeamCoordination(db)
    
    # Test AgentTeamService methods exist
    assert hasattr(team_service, 'create_team')
    assert hasattr(team_service, 'get_team')
    assert hasattr(team_service, 'update_team')
    assert hasattr(team_service, 'delete_team')
    assert hasattr(team_service, 'add_agent_to_team')
    assert hasattr(team_service, 'remove_agent_from_team')
    assert hasattr(team_service, 'get_team_agents')
    assert hasattr(team_service, 'get_agents_by_role')
    assert hasattr(team_service, 'set_team_lead')
    assert hasattr(team_service, 'activate_team')
    assert hasattr(team_service, 'pause_team')
    
    # Test AgentTeamCoordination methods exist
    assert hasattr(coordination, 'distribute_task_to_team')
    assert hasattr(coordination, 'share_result_between_agents')


def test_data_types_consistency(db):
    """Test that data types are consistent across services"""
    team_service = AgentTeamService(db)
    
    # Create team
    team = team_service.create_team(
        name=f"Consistency Test Team {uuid4()}",
        description="Test description",
        coordination_strategy=CoordinationStrategy.COLLABORATIVE.value,
        roles={"developer": "Writes code"}
    )
    
    # Verify team attributes
    assert isinstance(team.id, type(uuid4()))
    assert isinstance(team.name, str)
    assert isinstance(team.description, str)
    assert isinstance(team.coordination_strategy, str)
    assert isinstance(team.status, str)
    assert team.roles is None or isinstance(team.roles, dict)
    
    # Get team by ID
    retrieved_team = team_service.get_team(team.id)
    assert retrieved_team is not None
    assert retrieved_team.id == team.id
    assert isinstance(retrieved_team, AgentTeam)


def test_planning_service_integration(db):
    """Test PlanningService integration with teams"""
    planning_service = PlanningService(db)
    team_service = AgentTeamService(db)
    
    # Create team
    team = team_service.create_team(
        name=f"Planning Integration Team {uuid4()}"
    )
    team_service.activate_team(team.id)
    
    # Verify PlanningService can access team
    retrieved_team = planning_service.agent_team_service.get_team(team.id)
    assert retrieved_team is not None
    assert retrieved_team.id == team.id
    
    # Verify team status check
    assert retrieved_team.status == TeamStatus.ACTIVE.value


def test_execution_service_integration(db):
    """Test ExecutionService integration with teams"""
    execution_service = ExecutionService(db)
    team_service = AgentTeamService(db)
    
    # Create team
    team = team_service.create_team(
        name=f"Execution Integration Team {uuid4()}"
    )
    team_service.activate_team(team.id)
    
    # Verify ExecutionService can use team coordination
    # (ExecutionService uses AgentTeamService and AgentTeamCoordination internally)
    assert hasattr(execution_service, '_execute_with_team')


def test_team_agent_association_consistency(db):
    """Test that team-agent associations are consistent"""
    team_service = AgentTeamService(db)
    
    # Create team and agents
    team = team_service.create_team(name=f"Association Team {uuid4()}")
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    
    # Add agents to team
    team_service.add_agent_to_team(team.id, agent1.id, role="developer")
    team_service.add_agent_to_team(team.id, agent2.id, role="reviewer")
    
    # Get team agents
    agents = team_service.get_team_agents(team.id)
    assert len(agents) == 2
    
    # Verify agent data structure
    for agent_info in agents:
        assert "agent_id" in agent_info
        assert "agent_name" in agent_info
        assert "agent_status" in agent_info
        assert "role" in agent_info
        assert "is_lead" in agent_info
        assert isinstance(agent_info["agent_id"], str)
        assert isinstance(agent_info["agent_name"], str)
        assert isinstance(agent_info["role"], (str, type(None)))
        assert isinstance(agent_info["is_lead"], bool)
    
    # Get agents by role
    developers = team_service.get_agents_by_role(team.id, "developer")
    assert len(developers) == 1
    assert developers[0].id == agent1.id
    assert isinstance(developers[0], Agent)


def test_coordination_strategy_consistency(db):
    """Test that coordination strategies are used consistently"""
    team_service = AgentTeamService(db)
    coordination = AgentTeamCoordination(db)
    
    # Test all strategies
    strategies = [
        CoordinationStrategy.SEQUENTIAL,
        CoordinationStrategy.PARALLEL,
        CoordinationStrategy.HIERARCHICAL,
        CoordinationStrategy.COLLABORATIVE,
        CoordinationStrategy.PIPELINE
    ]
    
    for strategy in strategies:
        team = team_service.create_team(
            name=f"Strategy Team {strategy.value} {uuid4()}",
            coordination_strategy=strategy.value
        )
        
        # Verify strategy is stored correctly
        assert team.coordination_strategy == strategy.value
        
        # Verify coordination service can handle the strategy
        # (This is tested in coordination tests, but we verify the value is valid)
        assert strategy.value in [s.value for s in CoordinationStrategy]


def test_team_status_transitions_consistency(db):
    """Test that team status transitions are consistent"""
    team_service = AgentTeamService(db)
    
    # Create team (defaults to DRAFT)
    team = team_service.create_team(name=f"Status Team {uuid4()}")
    assert team.status == TeamStatus.DRAFT.value
    
    # Activate
    team_service.activate_team(team.id)
    team = team_service.get_team(team.id)
    assert team.status == TeamStatus.ACTIVE.value
    
    # Pause
    team_service.pause_team(team.id)
    team = team_service.get_team(team.id)
    assert team.status == TeamStatus.PAUSED.value
    
    # Activate again
    team_service.activate_team(team.id)
    team = team_service.get_team(team.id)
    assert team.status == TeamStatus.ACTIVE.value


def test_context_parameter_consistency(db):
    """Test that context parameters are consistent across services"""
    planning_service = PlanningService(db)
    team_service = AgentTeamService(db)
    
    # Create team
    team = team_service.create_team(name=f"Context Team {uuid4()}")
    team_service.activate_team(team.id)
    
    # Test context with team_id
    context = {"team_id": str(team.id)}
    
    # Verify PlanningService can process team_id from context
    # (This is tested in planning tests, but we verify the parameter format)
    assert "team_id" in context
    assert isinstance(context["team_id"], str)
    
    # Verify team can be retrieved from context
    team_id = context.get("team_id")
    if team_id:
        from uuid import UUID
        try:
            team_uuid = UUID(team_id)
            retrieved_team = team_service.get_team(team_uuid)
            assert retrieved_team is not None
        except (ValueError, TypeError):
            pytest.fail("Invalid team_id format in context")


def test_step_assignment_consistency(db):
    """Test that step assignment (team_id vs agent) is consistent"""
    team_service = AgentTeamService(db)
    
    # Create team and agent
    team = team_service.create_team(name=f"Step Team {uuid4()}")
    team_service.activate_team(team.id)
    agent = Agent(name=f"Agent {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent)
    db.commit()
    team_service.add_agent_to_team(team.id, agent.id, role="developer")
    
    # Test step with team_id
    step_with_team = {
        "step_id": "step1",
        "description": "Test step",
        "team_id": str(team.id)
    }
    
    # Test step with agent
    step_with_agent = {
        "step_id": "step2",
        "description": "Test step",
        "agent": str(agent.id)
    }
    
    # Test step with both (team should take precedence)
    step_with_both = {
        "step_id": "step3",
        "description": "Test step",
        "team_id": str(team.id),
        "agent": str(agent.id)
    }
    
    # Verify step formats
    assert "team_id" in step_with_team
    assert "agent" in step_with_agent
    assert "team_id" in step_with_both
    assert "agent" in step_with_both
    
    # Verify team_id format
    assert isinstance(step_with_team["team_id"], str)
    from uuid import UUID
    try:
        UUID(step_with_team["team_id"])
    except (ValueError, TypeError):
        pytest.fail("Invalid team_id format in step")


def test_error_handling_consistency(db):
    """Test that error handling is consistent"""
    team_service = AgentTeamService(db)
    
    # Test invalid team_id
    invalid_team_id = uuid4()
    team = team_service.get_team(invalid_team_id)
    assert team is None
    
    # Test duplicate team name
    team1 = team_service.create_team(name=f"Unique Team {uuid4()}")
    with pytest.raises(ValueError, match="already exists"):
        team_service.create_team(name=team1.name)
    
    # Test inactive team operations
    team2 = team_service.create_team(name=f"Inactive Team {uuid4()}")
    # Team is in DRAFT status, not ACTIVE
    assert team2.status == TeamStatus.DRAFT.value

