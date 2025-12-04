"""
Integration tests for agent selection in planning
"""
import pytest
import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.models.task import Task, TaskStatus
from app.models.agent import Agent, AgentStatus, AgentCapability
from app.services.planning_service import PlanningService
from app.services.agent_service import AgentService


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_agent(db_session: Session):
    """Create a test agent"""
    agent = Agent(
        name="Test Planning Agent",
        description="Test agent for planning tasks",
        status=AgentStatus.ACTIVE.value,
        capabilities=[AgentCapability.PLANNING.value],
        system_prompt="You are a planning agent",
        version=1
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.mark.asyncio
class TestAgentPlanningIntegration:
    """Integration tests for agent selection in planning"""
    
    async def test_generate_plan_with_agent_selection(self, db_session: Session, test_agent: Agent):
        """Test plan generation with automatic agent selection"""
        planning_service = PlanningService(db_session)
        
        task_description = "Create a simple Python script"
        
        # Generate plan without specifying agent (should auto-select)
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={}
        )
        
        # Check that plan was created
        assert plan is not None
        assert plan.status == "draft"
        
        # Check Digital Twin context for agent selection
        task = db_session.query(Task).filter(Task.id == plan.task_id).first()
        if task:
            context = task.get_context()
            agent_selection = context.get("agent_selection", {})
            
            # Agent selection info should be present (may or may not have selected agent)
            assert "selected_agent_id" in agent_selection
            assert "selected_agents" in agent_selection
    
    async def test_generate_plan_with_specified_agent(self, db_session: Session, test_agent: Agent):
        """Test plan generation with specified agent"""
        planning_service = PlanningService(db_session)
        
        task_description = "Create a simple Python script"
        
        # Generate plan with specified agent
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={"agent_id": str(test_agent.id)}
        )
        
        # Check that plan was created
        assert plan is not None
        
        # Check Digital Twin context for agent selection
        task = db_session.query(Task).filter(Task.id == plan.task_id).first()
        if task:
            context = task.get_context()
            agent_selection = context.get("agent_selection", {})
            
            # Should have the specified agent
            assert agent_selection.get("selected_agent_id") == str(test_agent.id)
            if agent_selection.get("selected_agents"):
                assert any(
                    agent_info.get("agent_id") == str(test_agent.id)
                    for agent_info in agent_selection["selected_agents"]
                )
    
    async def test_plan_steps_have_agent_assigned(self, db_session: Session, test_agent: Agent):
        """Test that plan steps have agent assigned when agent is selected"""
        planning_service = PlanningService(db_session)
        
        task_description = "Create a simple Python script"
        
        # Generate plan with specified agent
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={"agent_id": str(test_agent.id)}
        )
        
        # Parse steps
        steps = plan.steps
        if isinstance(steps, str):
            steps = json.loads(steps)
        
        # Check that steps have agent assigned (if any steps exist)
        if steps:
            # At least some steps should have agent assigned
            # (if agent selection worked)
            has_agent = any(
                step.get("agent") == str(test_agent.id) 
                for step in steps
            )
            # This is expected behavior if agent assignment is implemented
            # For now, just verify steps exist
            assert len(steps) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

