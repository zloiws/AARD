"""
Unit tests for trend analysis and recommendations in SelfAuditService
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.audit_report import AuditReport, AuditType, AuditStatus
from app.models.project_metric import ProjectMetric, MetricType, MetricPeriod
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
def sample_metrics(db_session_fixture):
    """Create sample metrics for trend analysis"""
    db = db_session_fixture
    now = datetime.utcnow()
    
    # Create metrics with improving trend (0.5 -> 0.9)
    metrics = []
    for i in range(14):  # 14 days
        day = now - timedelta(days=13-i)
        period_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)
        
        # Improving trend: start at 0.5, end at 0.9
        value = 0.5 + (i / 13) * 0.4
        
        metric = ProjectMetric(
            metric_type=MetricType.TASK_SUCCESS,
            metric_name="task_success_rate",
            period=MetricPeriod.DAY,
            period_start=period_start,
            period_end=period_end,
            value=value,
            count=10
        )
        db.add(metric)
        metrics.append(metric)
    
    db.commit()
    return metrics


def test_analyze_trends_improving(audit_service, sample_metrics):
    """Test trend analysis with improving trend"""
    result = audit_service.analyze_trends(
        metric_name="task_success_rate",
        days=14,
        period_days=7
    )
    
    assert result is not None
    assert result["status"] == "analyzed"
    assert result["trend_direction"] == "improving"
    assert result["change_percent"] > 0
    assert "recent_average" in result
    assert "previous_average" in result


def test_analyze_trends_insufficient_data(audit_service):
    """Test trend analysis with insufficient data"""
    result = audit_service.analyze_trends(
        metric_name="nonexistent_metric",
        days=30,
        period_days=7
    )
    
    assert result is not None
    assert result["status"] == "insufficient_data"
    assert "message" in result


def test_detect_improvements_degradations(audit_service):
    """Test detecting improvements and degradations"""
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)
    
    result = audit_service.detect_improvements_degradations(
        period_start=period_start,
        period_end=period_end,
        comparison_period_days=7
    )
    
    assert result is not None
    assert "improvements" in result
    assert "degradations" in result
    assert "summary" in result
    assert isinstance(result["improvements"], list)
    assert isinstance(result["degradations"], list)


def test_generate_smart_recommendations(audit_service):
    """Test generating smart recommendations"""
    audit_results = {
        "performance": {
            "findings": [
                {
                    "severity": "high",
                    "type": "low_success_rate",
                    "message": "Success rate is below 70%"
                }
            ],
            "metrics": {"success_rate": 0.65}
        }
    }
    
    trends = {
        "status": "analyzed",
        "trend_direction": "degrading",
        "trend_severity": "moderate",
        "change_percent": -15.0,
        "metric_name": "task_success_rate"
    }
    
    improvements_degradations = {
        "degradations": [
            {
                "metric": "success_rate",
                "change_percent": -10.0,
                "message": "Success rate degraded by 10.00%"
            }
        ],
        "improvements": []
    }
    
    recommendations = audit_service.generate_smart_recommendations(
        audit_results=audit_results,
        trends=trends,
        improvements_degradations=improvements_degradations
    )
    
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0
    
    # Should have high priority recommendation for low success rate
    high_priority = [r for r in recommendations if r.get("priority") == "high"]
    assert len(high_priority) > 0


def test_generate_smart_recommendations_no_issues(audit_service):
    """Test generating recommendations when no issues"""
    audit_results = {
        "performance": {
            "findings": [],
            "metrics": {"success_rate": 0.95}
        }
    }
    
    trends = {
        "status": "analyzed",
        "trend_direction": "stable",
        "trend_severity": "none",
        "change_percent": 2.0
    }
    
    improvements_degradations = {
        "degradations": [],
        "improvements": []
    }
    
    recommendations = audit_service.generate_smart_recommendations(
        audit_results=audit_results,
        trends=trends,
        improvements_degradations=improvements_degradations
    )
    
    # May have low priority recommendations or be empty
    assert isinstance(recommendations, list)


@pytest.mark.asyncio
async def test_analyze_trends_with_llm_stub(audit_service):
    """Test LLM trend analysis stub (will use fallback)"""
    trends_data = {
        "status": "analyzed",
        "trend_direction": "degrading",
        "trend_severity": "moderate",
        "change_percent": -10.0,
        "metric_name": "task_success_rate"
    }
    
    audit_results = {
        "performance": {"metrics": {"success_rate": 0.8}}
    }
    
    # This will likely fail (no LLM), but should return fallback
    result = await audit_service.analyze_trends_with_llm(
        trends_data=trends_data,
        audit_results=audit_results
    )
    
    assert result is not None
    # Should have either LLM analysis or fallback
    assert "llm_available" in result or "fallback_analysis" in result


@pytest.mark.asyncio
async def test_generate_enhanced_report(audit_service):
    """Test generating enhanced report with trend analysis"""
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)
    
    report = await audit_service.generate_enhanced_report(
        audit_type=AuditType.PERFORMANCE,
        period_start=period_start,
        period_end=period_end,
        use_llm=False  # Don't use LLM
    )
    
    assert report is not None
    assert report.status == AuditStatus.COMPLETED
    assert report.trends is not None
    assert "trend_analysis" in report.trends
    assert "improvements_degradations" in report.trends
    assert report.recommendations is not None
    assert "smart_recommendations" in report.recommendations


def test_generate_fallback_insights(audit_service):
    """Test fallback insights generation"""
    trends_data = {
        "status": "analyzed",
        "trend_direction": "improving",
        "change_percent": 15.0
    }
    
    insights = audit_service._generate_fallback_insights(trends_data)
    
    assert isinstance(insights, str)
    assert "improvement" in insights.lower() or "improving" in insights.lower()


def test_format_trends_for_llm(audit_service):
    """Test formatting trends for LLM"""
    trends_data = {
        "status": "analyzed",
        "metric_name": "test_metric",
        "trend_direction": "improving",
        "trend_severity": "moderate",
        "change_percent": 10.0,
        "recent_average": 0.85,
        "previous_average": 0.75
    }
    
    formatted = audit_service._format_trends_for_llm(trends_data)
    
    assert isinstance(formatted, str)
    assert "test_metric" in formatted
    assert "improving" in formatted

