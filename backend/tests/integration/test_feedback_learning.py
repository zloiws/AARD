"""
Integration tests for FeedbackLearningService
"""
from datetime import datetime
from uuid import uuid4

import pytest
from app.models.approval import ApprovalRequest, ApprovalRequestType
from app.models.learning_pattern import LearningPattern, PatternType
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.feedback_learning_service import FeedbackLearningService
from sqlalchemy.orm import Session


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
        steps=[{"step_id": "step_1", "description": "Step 1", "type": "action"}],
        status="draft"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    yield plan
    db.delete(plan)
    db.commit()


@pytest.fixture
def test_approval(db: Session, test_plan: Plan) -> ApprovalRequest:
    """Create a test approval request"""
    approval = ApprovalRequest(
        id=uuid4(),
        request_type="plan_approval",
        plan_id=test_plan.id,
        task_id=test_plan.task_id,
        request_data={
            "plan_id": str(test_plan.id),
            "goal": test_plan.goal,
            "total_steps": 1
        },
        status="pending"
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    yield approval
    db.delete(approval)
    db.commit()


def test_learn_from_approval_feedback_approved(
    db: Session,
    test_approval: ApprovalRequest
):
    """Test learning from approved feedback"""
    service = FeedbackLearningService(db)
    
    test_approval.status = "approved"
    test_approval.human_feedback = "Good plan, well structured"
    db.commit()
    
    pattern = service.learn_from_approval_feedback(test_approval)
    
    assert pattern is not None
    assert pattern.pattern_type == PatternType.STRATEGY.value
    assert pattern.success_rate == 1.0


def test_learn_from_approval_feedback_rejected(
    db: Session,
    test_approval: ApprovalRequest
):
    """Test learning from rejected feedback"""
    service = FeedbackLearningService(db)
    
    test_approval.status = "rejected"
    test_approval.human_feedback = "Too complex, simplify the approach"
    db.commit()
    
    pattern = service.learn_from_approval_feedback(test_approval)
    
    assert pattern is not None
    assert pattern.success_rate == 0.0
    pattern_data = pattern.pattern_data or {}
    assert pattern_data.get("suggestion") == "simplify"


def test_extract_improvements_from_feedback(db: Session):
    """Test extracting improvements from feedback"""
    service = FeedbackLearningService(db)
    
    feedback = "The plan is too complex. Please simplify and add validation steps."
    improvements = service.extract_improvements_from_feedback(feedback)
    
    assert "improvements" in improvements
    assert len(improvements["improvements"]) > 0
    assert "simplify" in improvements["improvements"][0].lower() or "simplify" in str(improvements["improvements"]).lower()


def test_apply_learned_patterns(db: Session):
    """Test applying learned patterns to task"""
    service = FeedbackLearningService(db)
    
    recommendations = service.apply_learned_patterns(
        task_description="Generate code for data processing",
        task_category="code_generation"
    )
    
    assert "task_category" in recommendations
    assert "patterns_found" in recommendations
    assert "recommendations" in recommendations
    assert recommendations["task_category"] == "code_generation"


def test_categorize_task(db: Session):
    """Test task categorization"""
    service = FeedbackLearningService(db)
    
    category1 = service._categorize_task("Write a Python function")
    assert category1 == "code_generation"
    
    category2 = service._categorize_task("Process and analyze data")
    assert category2 == "data_processing"
    
    category3 = service._categorize_task("Test the application")
    assert category3 == "testing"


def test_get_feedback_statistics(db: Session):
    """Test getting feedback statistics"""
    service = FeedbackLearningService(db)
    
    stats = service.get_feedback_statistics()
    
    assert "total_approvals" in stats
    assert "approved" in stats
    assert "rejected" in stats
    assert "with_feedback" in stats
    assert "patterns_extracted" in stats
    assert "feedback_rate" in stats

