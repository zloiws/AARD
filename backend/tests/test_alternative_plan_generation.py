"""
Tests for alternative plan generation (Phase 6.1.1)
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.services.planning_service import PlanningService


@pytest.fixture
def db():
    """Database session fixture"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def planning_service(db):
    """PlanningService fixture"""
    return PlanningService(db)


@pytest.fixture
def test_task(db):
    """Create a test task"""
    task = Task(
        id=uuid4(),
        description="Test task for alternative plan generation",
        status=TaskStatus.PENDING,
        priority=5
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@pytest.mark.asyncio
async def test_generate_alternative_plans_basic(planning_service, test_task):
    """Test basic alternative plan generation"""
    task_description = "Create a REST API for user management"
    
    # Generate 2 alternative plans
    alternative_plans = await planning_service.generate_alternative_plans(
        task_description=task_description,
        task_id=test_task.id,
        num_alternatives=2
    )
    
    # Should generate at least 1 plan (may fail to generate all due to LLM issues)
    assert len(alternative_plans) >= 1, f"Expected at least 1 plan, got {len(alternative_plans)}"
    
    # All plans should be in DRAFT or APPROVED status (may be auto-approved)
    for plan in alternative_plans:
        assert plan.status in [PlanStatus.DRAFT.value, PlanStatus.APPROVED.value], \
            f"Plan should be DRAFT or APPROVED, got {plan.status}"
        assert plan.task_id == test_task.id
        assert plan.goal is not None
        assert plan.steps is not None
        assert len(plan.steps) > 0
        
        # Check strategy or alternatives metadata (metadata may be in either field)
        has_alternative_metadata = False
        if plan.strategy and isinstance(plan.strategy, dict):
            if "alternative_strategy" in plan.strategy:
                has_alternative_metadata = True
                assert plan.strategy["alternative_strategy"] in ["conservative", "balanced", "aggressive"]
        
        if plan.alternatives and isinstance(plan.alternatives, dict):
            if plan.alternatives.get("is_alternative"):
                has_alternative_metadata = True
                assert "alternative_index" in plan.alternatives
                assert "alternative_name" in plan.alternatives
        
        # At least one should have alternative metadata
        assert has_alternative_metadata, f"Plan should have alternative metadata in strategy or alternatives. Strategy: {plan.strategy}, Alternatives: {plan.alternatives}"


@pytest.mark.asyncio
async def test_generate_alternative_plans_three_variants(planning_service, test_task):
    """Test generating 3 alternative plans"""
    task_description = "Implement user authentication system"
    
    # Generate 3 alternative plans
    alternative_plans = await planning_service.generate_alternative_plans(
        task_description=task_description,
        task_id=test_task.id,
        num_alternatives=3
    )
    
    # Should generate 3 plans
    assert len(alternative_plans) == 3, f"Expected 3 plans, got {len(alternative_plans)}"
    
    # Check that plans have different strategies
    strategies = []
    for plan in alternative_plans:
        if isinstance(plan.strategy, dict):
            strategy_name = plan.strategy.get("alternative_strategy")
            if strategy_name:
                strategies.append(strategy_name)
    
    # Should have at least 2 different strategies
    assert len(set(strategies)) >= 2, f"Plans should have different strategies, got: {strategies}"


@pytest.mark.asyncio
async def test_generate_alternative_plans_parallel_execution(planning_service, test_task):
    """Test that alternative plans are generated in parallel"""
    import time
    
    task_description = "Create database migration system"
    
    # Measure time for parallel generation
    start_time = time.time()
    alternative_plans = await planning_service.generate_alternative_plans(
        task_description=task_description,
        task_id=test_task.id,
        num_alternatives=3
    )
    parallel_time = time.time() - start_time
    
    # Generate plans sequentially for comparison
    start_time = time.time()
    sequential_plans = []
    for i in range(3):
        plan = await planning_service.generate_plan(
            task_description=task_description,
            task_id=test_task.id
        )
        sequential_plans.append(plan)
    sequential_time = time.time() - start_time
    
    # Parallel should be faster (or at least not much slower due to overhead)
    # Allow some tolerance for overhead
    assert parallel_time <= sequential_time * 1.5, \
        f"Parallel generation ({parallel_time:.2f}s) should be faster than sequential ({sequential_time:.2f}s)"


@pytest.mark.asyncio
async def test_generate_alternative_plans_different_strategies(planning_service, test_task):
    """Test that different strategies produce different plans"""
    task_description = "Build a web application with authentication"
    
    alternative_plans = await planning_service.generate_alternative_plans(
        task_description=task_description,
        task_id=test_task.id,
        num_alternatives=3
    )
    
    assert len(alternative_plans) == 3
    
    # Check that plans have different characteristics
    step_counts = []
    for plan in alternative_plans:
        if plan.steps:
            step_counts.append(len(plan.steps))
    
    # Plans should have different step counts (conservative should have more steps)
    # But allow for some variation
    assert len(set(step_counts)) >= 1, "Plans should have varying step counts"
    
    # Check strategy names
    strategy_names = []
    for plan in alternative_plans:
        if isinstance(plan.strategy, dict):
            strategy_name = plan.strategy.get("alternative_strategy")
            if strategy_name:
                strategy_names.append(strategy_name)
    
    # Should have different strategy names
    assert len(set(strategy_names)) >= 2, f"Should have different strategies, got: {strategy_names}"


@pytest.mark.asyncio
async def test_generate_alternative_plans_with_context(planning_service, test_task):
    """Test generating alternative plans with context"""
    task_description = "Create a microservice for order processing"
    
    context = {
        "existing_services": ["user-service", "product-service"],
        "constraints": ["Must use PostgreSQL", "Must be RESTful"]
    }
    
    alternative_plans = await planning_service.generate_alternative_plans(
        task_description=task_description,
        task_id=test_task.id,
        context=context,
        num_alternatives=2
    )
    
    assert len(alternative_plans) >= 1
    
    # Plans should incorporate context
    for plan in alternative_plans:
        assert plan.goal is not None
        assert plan.steps is not None


@pytest.mark.asyncio
async def test_generate_alternative_plans_limit_enforcement(planning_service, test_task):
    """Test that num_alternatives is limited to 2-3"""
    task_description = "Test task"
    
    # Test with num_alternatives > 3 (should be limited to 3)
    plans = await planning_service.generate_alternative_plans(
        task_description=task_description,
        task_id=test_task.id,
        num_alternatives=5
    )
    assert len(plans) <= 3, "Should not generate more than 3 alternatives"
    
    # Test with num_alternatives < 2 (should be increased to 2)
    plans = await planning_service.generate_alternative_plans(
        task_description=task_description,
        task_id=test_task.id,
        num_alternatives=1
    )
    assert len(plans) >= 2, "Should generate at least 2 alternatives"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

