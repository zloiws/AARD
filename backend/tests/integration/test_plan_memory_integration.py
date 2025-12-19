"""
Integration tests for plan-memory integration (Phase 1, Task 6.4)
"""
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.models.plan import Plan
from app.models.agent import Agent
from app.models.agent_memory import MemoryType
from app.services.planning_service import PlanningService
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_save_todo_to_working_memory(db: Session):
    """Test that active ToDo list is saved to working memory"""
    # Create an agent
    agent = Agent(
        id=uuid4(),
        name=f"Test Agent {uuid4()}",
        description="Test agent for memory integration",
        system_prompt="You are a test agent"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task for memory",
        status=TaskStatus.DRAFT,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create a plan with steps
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task for memory",
        steps=[
            {"step_id": "1", "description": "Step 1", "action": "test"},
            {"step_id": "2", "description": "Step 2", "action": "test"},
            {"step_id": "3", "description": "Step 3", "action": "test"}
        ],
        status="draft",
        agent_metadata={"agent_id": str(agent.id)}
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Test saving ToDo to working memory
    planning_service = PlanningService(db)
    await planning_service._save_todo_to_working_memory(
        task_id=task.id,
        plan=plan
    )
    
    # Verify memory was saved
    memory_service = MemoryService(db)
    memories = memory_service.search_memories(
        agent_id=agent.id,
        content_query={"task_id": str(task.id)},
        memory_type=MemoryType.WORKING.value,
        limit=10
    )
    
    assert len(memories) > 0
    todo_memory = memories[0]
    assert todo_memory.memory_type == MemoryType.WORKING.value
    assert "todo_list" in todo_memory.content
    assert len(todo_memory.content["todo_list"]) == len(plan.steps)


@pytest.mark.asyncio
async def test_save_plan_to_episodic_memory(db: Session):
    """Test that plan history is saved to episodic memory"""
    # Create an agent
    agent = Agent(
        id=uuid4(),
        name=f"Test Agent {uuid4()}",
        description="Test agent for memory integration",
        system_prompt="You are a test agent"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task for episodic memory",
        status=TaskStatus.DRAFT,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create a plan
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task for episodic memory",
        steps=[
            {"step_id": "1", "description": "Step 1", "action": "test"}
        ],
        status="draft",
        agent_metadata={"agent_id": str(agent.id)}
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Test saving plan to episodic memory
    planning_service = PlanningService(db)
    await planning_service._save_plan_to_episodic_memory(
        plan=plan,
        task_id=task.id,
        event_type="plan_created",
        context={"source": "test"}
    )
    
    # Verify memory was saved
    memory_service = MemoryService(db)
    memories = memory_service.search_memories(
        agent_id=agent.id,
        content_query={"plan_id": str(plan.id)},
        memory_type=MemoryType.EXPERIENCE.value,
        limit=10
    )
    
    assert len(memories) > 0
    episodic_memory = memories[0]
    assert episodic_memory.memory_type == MemoryType.EXPERIENCE.value
    assert episodic_memory.content["plan_id"] == str(plan.id)
    assert episodic_memory.content["event_type"] == "plan_created"


@pytest.mark.asyncio
async def test_apply_procedural_memory_patterns(db: Session):
    """Test that procedural memory patterns are applied during plan generation"""
    # Create an agent
    agent = Agent(
        id=uuid4(),
        name=f"Test Agent {uuid4()}",
        description="Test agent for memory integration",
        system_prompt="You are a test agent"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Create a procedural memory pattern
    memory_service = MemoryService(db)
    pattern_memory = memory_service.create_memory(
        agent_id=agent.id,
        memory_type=MemoryType.PROCEDURAL.value,
        content={
            "pattern_type": "planning_strategy",
            "task_pattern": "test task",
            "success_rate": 0.9,
            "strategy": {
                "approach": "test approach",
                "steps_template": [
                    {"step_id": "1", "description": "Pattern step 1"}
                ]
            }
        },
        importance=0.8
    )
    db.commit()
    # diagnostic removed
    
    # Test applying procedural memory patterns
    planning_service = PlanningService(db)
    pattern = await planning_service._apply_procedural_memory_patterns(
        task_description="test task for pattern matching",
        agent_id=agent.id
    )
    
    # Verify pattern was found and applied
    assert pattern is not None
    assert "pattern_type" in pattern or "strategy" in pattern


@pytest.mark.asyncio
async def test_plan_creation_saves_to_memory(db: Session):
    """Test that plan creation automatically saves to memory"""
    # Create an agent
    agent = Agent(
        id=uuid4(),
        name=f"Test Agent {uuid4()}",
        description="Test agent for memory integration",
        system_prompt="You are a test agent"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task for automatic memory save",
        status=TaskStatus.DRAFT,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create a plan (simulating plan creation)
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task for automatic memory save",
        steps=[
            {"step_id": "1", "description": "Step 1", "action": "test"}
        ],
        status="draft",
        agent_metadata={"agent_id": str(agent.id)}
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Simulate what PlanningService.generate_plan does
    planning_service = PlanningService(db)
    await planning_service._save_plan_to_episodic_memory(
        plan=plan,
        task_id=task.id,
        event_type="plan_created"
    )
    await planning_service._save_todo_to_working_memory(
        task_id=task.id,
        plan=plan
    )
    
    # Verify both memories were saved
    memory_service = MemoryService(db)
    
    # Check episodic memory
    episodic_memories = memory_service.search_memories(
        agent_id=agent.id,
        content_query={"plan_id": str(plan.id)},
        memory_type=MemoryType.EXPERIENCE.value,
        limit=10
    )
    assert len(episodic_memories) > 0
    
    # Check working memory
    working_memories = memory_service.search_memories(
        agent_id=agent.id,
        content_query={"task_id": str(task.id)},
        memory_type=MemoryType.WORKING.value,
        limit=10
    )
    assert len(working_memories) > 0

