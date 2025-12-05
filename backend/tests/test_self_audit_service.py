"""
Unit tests for SelfAuditService
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.audit_report import AuditReport, AuditType, AuditStatus
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.prompt import Prompt, PromptType, PromptStatus
from app.services.self_audit_service import SelfAuditService
from app.core.database import SessionLocal, engine, Base


@pytest.fixture(scope="module")
def db_session_fixture():
    """Create a test database session for the module."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clear_db_before_each_test(db_session_fixture):
    """Clear the database before each test to ensure isolation."""
    db = db_session_fixture
    for table in reversed(Base.metadata.sorted_tables):
        if table.name != 'alembic_version':
            db.execute(table.delete())
    db.commit()
    yield
    for table in reversed(Base.metadata.sorted_tables):
        if table.name != 'alembic_version':
            db.execute(table.delete())
    db.commit()


@pytest.fixture
def audit_service(db_session_fixture):
    """Create SelfAuditService instance"""
    return SelfAuditService(db_session_fixture)


@pytest.fixture
def sample_period():
    """Create sample audit period"""
    now = datetime.utcnow()
    return now - timedelta(days=7), now


@pytest.mark.asyncio
async def test_audit_performance(audit_service, sample_period):
    """Test performance audit"""
    period_start, period_end = sample_period
    
    # Create sample tasks
    db = audit_service.db
    task1 = Task(
        description="Test task 1",
        status=TaskStatus.COMPLETED
    )
    task2 = Task(
        description="Test task 2",
        status=TaskStatus.FAILED
    )
    db.add(task1)
    db.add(task2)
    db.commit()
    
    # Run audit
    result = await audit_service.audit_performance(period_start, period_end)
    
    assert result is not None
    assert "period_start" in result
    assert "period_end" in result
    assert "metrics" in result
    assert "findings" in result
    assert "recommendations" in result


@pytest.mark.asyncio
async def test_audit_quality(audit_service, sample_period):
    """Test quality audit"""
    period_start, period_end = sample_period
    
    # Create sample plans
    db = audit_service.db
    task = Task(description="Test task", status=TaskStatus.PENDING)
    db.add(task)
    db.commit()
    
    plan1 = Plan(
        task_id=task.id,
        goal="Test goal",
        steps=[],
        status=PlanStatus.COMPLETED,
        estimated_duration=100,
        actual_duration=90
    )
    plan2 = Plan(
        task_id=task.id,
        goal="Test goal 2",
        steps=[],
        status=PlanStatus.FAILED
    )
    db.add(plan1)
    db.add(plan2)
    db.commit()
    
    # Run audit
    result = await audit_service.audit_quality(period_start, period_end)
    
    assert result is not None
    assert "period_start" in result
    assert "period_end" in result
    assert "metrics" in result
    assert "findings" in result
    assert "recommendations" in result


@pytest.mark.asyncio
async def test_audit_prompts(audit_service, sample_period):
    """Test prompt audit"""
    period_start, period_end = sample_period
    
    # Create sample prompts
    db = audit_service.db
    prompt = Prompt(
        name="test_prompt",
        prompt_text="Test prompt text",
        prompt_type=PromptType.SYSTEM.value,
        level=0,
        version=1,
        status=PromptStatus.ACTIVE.value,
        usage_count=10,
        success_rate=0.8,
        avg_execution_time=1000.0
    )
    db.add(prompt)
    db.commit()
    
    # Run audit
    result = await audit_service.audit_prompts(period_start, period_end)
    
    assert result is not None
    assert "period_start" in result
    assert "period_end" in result
    assert "metrics" in result
    assert "prompt_analysis" in result
    assert "findings" in result
    assert "recommendations" in result


@pytest.mark.asyncio
async def test_audit_errors(audit_service, sample_period):
    """Test error audit"""
    period_start, period_end = sample_period
    
    # Create sample failed tasks
    db = audit_service.db
    task = Task(
        description="Failed task",
        status=TaskStatus.FAILED
    )
    task.update_context({
        "execution_logs": [
            {"type": "error", "message": "Timeout error occurred"}
        ]
    })
    db.add(task)
    db.commit()
    
    # Run audit
    result = await audit_service.audit_errors(period_start, period_end)
    
    assert result is not None
    assert "period_start" in result
    assert "period_end" in result
    assert "metrics" in result
    assert "findings" in result
    assert "recommendations" in result


@pytest.mark.asyncio
async def test_generate_report_performance(audit_service, sample_period):
    """Test generating performance audit report"""
    period_start, period_end = sample_period
    
    report = await audit_service.generate_report(
        audit_type=AuditType.PERFORMANCE,
        period_start=period_start,
        period_end=period_end,
        use_llm=False
    )
    
    assert report is not None
    assert report.audit_type == AuditType.PERFORMANCE
    assert report.status == AuditStatus.COMPLETED
    assert report.period_start == period_start
    assert report.period_end == period_end
    assert report.summary is not None
    assert report.findings is not None
    assert report.recommendations is not None


@pytest.mark.asyncio
async def test_generate_report_full(audit_service, sample_period):
    """Test generating full audit report"""
    period_start, period_end = sample_period
    
    report = await audit_service.generate_report(
        audit_type=AuditType.FULL,
        period_start=period_start,
        period_end=period_end,
        use_llm=False
    )
    
    assert report is not None
    assert report.audit_type == AuditType.FULL
    assert report.status == AuditStatus.COMPLETED
    assert report.findings is not None
    # Full audit should have all sections
    findings = report.findings
    if isinstance(findings, dict) and "sections" in findings:
        sections = findings["sections"]
        assert "performance" in sections or "quality" in sections or "prompts" in sections or "errors" in sections


def test_classify_error(audit_service):
    """Test error classification"""
    assert audit_service._classify_error("Timeout error") == "timeout"
    assert audit_service._classify_error("Permission denied") == "permission"
    assert audit_service._classify_error("File not found") == "not_found"
    assert audit_service._classify_error("Invalid input") == "invalid_input"
    assert audit_service._classify_error("Connection error") == "connection"
    assert audit_service._classify_error("Syntax error") == "syntax_error"
    assert audit_service._classify_error("Unknown error") == "other"

