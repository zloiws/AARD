"""
Integration tests for AdaptiveApprovalService
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.adaptive_approval_service import AdaptiveApprovalService
from app.models.agent import Agent, AgentStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.trace import ExecutionTrace


@pytest.fixture
def test_task(db: Session) -> Task:
    """Create a test task"""
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.PENDING.value,
        priority=5
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    yield task
    db.delete(task)
    db.commit()


@pytest.fixture
def test_plan(db: Session, test_task: Task) -> Plan:
    """Create a test plan"""
    plan = Plan(
        id=uuid4(),
        task_id=test_task.id,
        version=1,
        goal="Test plan goal",
        steps=[
            {
                "step_id": "step_1",
                "description": "Simple step",
                "type": "action"
            }
        ],
        status="draft"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    yield plan
    db.delete(plan)
    db.commit()


@pytest.fixture
def high_trust_agent(db: Session) -> Agent:
    """Create an agent with high trust score"""
    agent = Agent(
        id=uuid4(),
        name=f"High Trust Agent {uuid4().hex[:8]}",
        status=AgentStatus.ACTIVE.value,
        total_tasks_executed=100,
        successful_tasks=95,
        failed_tasks=5
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    yield agent
    db.delete(agent)
    db.commit()


@pytest.fixture
def low_trust_agent(db: Session) -> Agent:
    """Create an agent with low trust score"""
    agent = Agent(
        id=uuid4(),
        name=f"Low Trust Agent {uuid4().hex[:8]}",
        status=AgentStatus.ACTIVE.value,
        total_tasks_executed=20,
        successful_tasks=8,
        failed_tasks=12
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    yield agent
    db.delete(agent)
    db.commit()


def test_calculate_agent_trust_score_high(db: Session, high_trust_agent: Agent):
    """Test calculating trust score for high-performing agent"""
    service = AdaptiveApprovalService(db)
    trust_score = service.calculate_agent_trust_score(high_trust_agent.id)
    
    assert trust_score > 0.7  # Should be high trust
    assert trust_score <= 1.0


def test_calculate_agent_trust_score_low(db: Session, low_trust_agent: Agent):
    """Test calculating trust score for low-performing agent"""
    service = AdaptiveApprovalService(db)
    trust_score = service.calculate_agent_trust_score(low_trust_agent.id)
    
    assert trust_score < 0.5  # Should be low trust
    assert trust_score >= 0.0


def test_calculate_agent_trust_score_new_agent(db: Session):
    """Test calculating trust score for new agent with no history"""
    agent = Agent(
        id=uuid4(),
        name=f"New Agent {uuid4().hex[:8]}",
        status=AgentStatus.ACTIVE.value,
        total_tasks_executed=2,
        successful_tasks=2,
        failed_tasks=0
    )
    db.add(agent)
    db.commit()
    
    try:
        service = AdaptiveApprovalService(db)
        trust_score = service.calculate_agent_trust_score(agent.id)
        
        # New agent should have low but non-zero trust
        assert trust_score >= 0.1
        assert trust_score < 0.5
    finally:
        db.delete(agent)
        db.commit()


def test_calculate_task_risk_level_simple(db: Session, test_plan: Plan):
    """Test calculating risk level for simple task"""
    service = AdaptiveApprovalService(db)
    risk_level = service.calculate_task_risk_level(
        "Simple task description",
        test_plan.steps if isinstance(test_plan.steps, list) else []
    )
    
    assert 0.0 <= risk_level <= 1.0
    assert risk_level < 0.5  # Simple task should be low risk


def test_calculate_task_risk_level_complex(db: Session, test_plan: Plan):
    """Test calculating risk level for complex task"""
    service = AdaptiveApprovalService(db)
    
    complex_steps = [
        {"step_id": f"step_{i}", "description": f"Step {i}", "type": "action"}
        for i in range(15)  # Many steps
    ]
    # Add high-risk keywords
    risk_level = service.calculate_task_risk_level(
        "Delete all files and drop database tables",
        complex_steps
    )
    
    assert risk_level > 0.5  # Complex task should be higher risk


def test_should_require_approval_high_risk(db: Session, test_plan: Plan):
    """Test that high-risk tasks always require approval"""
    service = AdaptiveApprovalService(db)
    
    # Create high-risk plan
    high_risk_steps = [
        {"step_id": "step_1", "description": "Delete important data", "type": "action"}
    ] * 15
    test_plan.steps = high_risk_steps
    db.commit()
    
    requires_approval, metadata = service.should_require_approval(
        plan=test_plan,
        task_risk_level=0.8  # High risk
    )
    
    assert requires_approval is True
    assert metadata["reason"] == "high_risk"


def test_should_require_approval_low_risk_high_trust(
    db: Session, 
    test_plan: Plan, 
    high_trust_agent: Agent
):
    """Test that low-risk tasks with high-trust agent don't require approval"""
    service = AdaptiveApprovalService(db)
    
    requires_approval, metadata = service.should_require_approval(
        plan=test_plan,
        agent_id=high_trust_agent.id,
        task_risk_level=0.2  # Low risk
    )
    
    assert requires_approval is False
    assert metadata["agent_trust_score"] > 0.7


def test_should_require_approval_medium_risk_low_trust(
    db: Session,
    test_plan: Plan,
    low_trust_agent: Agent
):
    """Test that medium-risk tasks with low-trust agent require approval"""
    service = AdaptiveApprovalService(db)
    
    requires_approval, metadata = service.should_require_approval(
        plan=test_plan,
        agent_id=low_trust_agent.id,
        task_risk_level=0.5  # Medium risk
    )
    
    assert requires_approval is True
    assert metadata["reason"] in ["medium_risk_low_trust", "high_risk"]


def test_should_require_approval_override(db: Session, test_plan: Plan, high_trust_agent: Agent):
    """Test override_risk flag"""
    service = AdaptiveApprovalService(db)
    
    requires_approval, metadata = service.should_require_approval(
        plan=test_plan,
        agent_id=high_trust_agent.id,
        task_risk_level=0.1,  # Very low risk
        override_risk=True
    )
    
    assert requires_approval is True
    assert metadata["reason"] == "override_risk"


def test_get_approval_statistics(db: Session):
    """Test getting approval statistics"""
    service = AdaptiveApprovalService(db)
    stats = service.get_approval_statistics()
    
    assert "total_requests" in stats
    assert "pending" in stats
    assert "approved" in stats
    assert "rejected" in stats
    assert "approval_rate" in stats

