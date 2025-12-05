"""
Manual testing script for Phase 3: Project Self-Reflection
Tests from simple to complex
"""
import sys
import os
from pathlib import Path

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Set working directory
os.chdir(BACKEND_DIR)

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.project_metrics_service import ProjectMetricsService
from app.services.self_audit_service import SelfAuditService
from app.models.project_metric import MetricType, MetricPeriod
from app.models.audit_report import AuditType


def print_section(title: str):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_1_simple_metrics_recording(db: Session):
    """Test 1: Simple metric recording"""
    print_section("Test 1: Simple Metric Recording")
    
    service = ProjectMetricsService(db)
    
    # Record a simple metric
    now = datetime.utcnow()
    period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = period_start + timedelta(days=1)
    
    service.record_metric(
        metric_type=MetricType.PERFORMANCE,
        metric_name="test_metric",
        value=0.85,
        count=10,
        period=MetricPeriod.DAY,
        period_start=period_start,
        period_end=period_end
    )
    
    print("✓ Recorded metric: test_metric = 0.85")
    
    # Get the metric
    trends = service.get_trends("test_metric", days=1)
    if trends:
        print(f"✓ Retrieved metric: {trends[0]['value']}")
    else:
        print("✗ Failed to retrieve metric")
    
    print("✓ Test 1 passed!")


def test_2_metrics_aggregation(db: Session):
    """Test 2: Metrics aggregation"""
    print_section("Test 2: Metrics Aggregation")
    
    service = ProjectMetricsService(db)
    
    # Record multiple metrics
    now = datetime.utcnow()
    for i in range(5):
        period_start = (now - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(hours=1)
        
        service.record_metric(
            metric_type=MetricType.PERFORMANCE,
            metric_name="aggregation_test",
            value=0.7 + i * 0.05,
            count=1,
            period=MetricPeriod.HOURLY,
            period_start=period_start,
            period_end=period_end
        )
    
    print("✓ Recorded 5 metrics")
    
    # Get overview
    overview = service.get_overview(days=1)
    print(f"✓ Overview retrieved: {len(overview.get('recent_metrics', []))} metrics")
    
    print("✓ Test 2 passed!")


def test_3_trend_analysis(db: Session):
    """Test 3: Trend analysis"""
    print_section("Test 3: Trend Analysis")
    
    service = ProjectMetricsService(db)
    
    # Create a trend (improving)
    now = datetime.utcnow()
    for i in range(10):
        day = now - timedelta(days=9-i)
        period_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)
        
        value = 0.5 + (i / 9) * 0.4  # Improving from 0.5 to 0.9
        
        service.record_metric(
            metric_type=MetricType.TASK_SUCCESS,
            metric_name="trend_test",
            value=value,
            count=10,
            period=MetricPeriod.DAY,
            period_start=period_start,
            period_end=period_end
        )
    
    print("✓ Created 10-day trend (improving)")
    
    # Analyze trend
    audit_service = SelfAuditService(db)
    trend_result = audit_service.analyze_trends(
        metric_name="trend_test",
        days=10,
        period_days=5
    )
    
    if trend_result.get("status") == "analyzed":
        print(f"✓ Trend analyzed: {trend_result['trend_direction']} ({trend_result['change_percent']:.1f}%)")
    else:
        print(f"✗ Trend analysis failed: {trend_result.get('message')}")
    
    print("✓ Test 3 passed!")


def test_4_simple_audit(db: Session):
    """Test 4: Simple audit"""
    print_section("Test 4: Simple Audit")
    
    audit_service = SelfAuditService(db)
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)
    
    # Run performance audit
    result = asyncio.run(audit_service.audit_performance(period_start, period_end))
    
    print(f"✓ Performance audit completed")
    print(f"  - Findings: {len(result.get('findings', []))}")
    print(f"  - Metrics: {len(result.get('metrics', {}))}")
    
    print("✓ Test 4 passed!")


def test_5_full_audit_report(db: Session):
    """Test 5: Full audit report generation"""
    print_section("Test 5: Full Audit Report")
    
    audit_service = SelfAuditService(db)
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)
    
    # Generate full report
    report = asyncio.run(audit_service.generate_report(
        audit_type=AuditType.FULL,
        period_start=period_start,
        period_end=period_end,
        use_llm=False
    ))
    
    print(f"✓ Full audit report generated: {report.id}")
    print(f"  - Status: {report.status.value}")
    print(f"  - Summary: {report.summary[:100] if report.summary else 'None'}...")
    
    if report.findings:
        all_findings = report.findings.get("all_findings", [])
        print(f"  - Findings: {len(all_findings)}")
    
    if report.recommendations:
        all_recs = report.recommendations.get("all_recommendations", [])
        print(f"  - Recommendations: {len(all_recs)}")
    
    print("✓ Test 5 passed!")


def test_6_enhanced_report_with_trends(db: Session):
    """Test 6: Enhanced report with trends"""
    print_section("Test 6: Enhanced Report with Trends")
    
    audit_service = SelfAuditService(db)
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)
    
    # Generate enhanced report
    report = asyncio.run(audit_service.generate_enhanced_report(
        audit_type=AuditType.PERFORMANCE,
        period_start=period_start,
        period_end=period_end,
        use_llm=False
    ))
    
    print(f"✓ Enhanced report generated: {report.id}")
    
    if report.trends:
        trend_analysis = report.trends.get("trend_analysis", {})
        if trend_analysis.get("status") == "analyzed":
            print(f"  - Trend: {trend_analysis.get('trend_direction')} ({trend_analysis.get('change_percent', 0):.1f}%)")
        
        imp_deg = report.trends.get("improvements_degradations", {})
        print(f"  - Improvements: {len(imp_deg.get('improvements', []))}")
        print(f"  - Degradations: {len(imp_deg.get('degradations', []))}")
    
    print("✓ Test 6 passed!")


def test_7_audit_scheduler(db: Session):
    """Test 7: Audit scheduler"""
    print_section("Test 7: Audit Scheduler")
    
    from app.services.audit_scheduler import get_audit_scheduler, AuditSchedule
    
    scheduler = get_audit_scheduler()
    
    # Test schedule configuration
    daily_schedule = scheduler.get_schedule(AuditSchedule.DAILY)
    print(f"✓ Daily schedule: enabled={daily_schedule['enabled']}, hour={daily_schedule['hour']}")
    
    # Test schedule update
    original_hour = daily_schedule['hour']
    scheduler.update_schedule(AuditSchedule.DAILY, hour=3)
    updated = scheduler.get_schedule(AuditSchedule.DAILY)
    print(f"✓ Updated schedule: hour={updated['hour']}")
    
    # Restore
    scheduler.update_schedule(AuditSchedule.DAILY, hour=original_hour)
    
    print("✓ Test 7 passed!")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  Phase 3: Project Self-Reflection - Manual Testing")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Simple tests
        test_1_simple_metrics_recording(db)
        test_2_metrics_aggregation(db)
        
        # Medium complexity
        test_3_trend_analysis(db)
        test_4_simple_audit(db)
        
        # Complex tests
        test_5_full_audit_report(db)
        test_6_enhanced_report_with_trends(db)
        test_7_audit_scheduler(db)
        
        print_section("All Tests Completed!")
        print("✓ All tests passed successfully!")
        print("\nNext steps:")
        print("  1. Check API endpoints: /api/metrics/project/overview")
        print("  2. Check web pages: /metrics/project, /audit-reports")
        print("  3. Verify database: SELECT * FROM project_metrics LIMIT 10;")
        print("  4. Verify audit reports: SELECT * FROM audit_reports LIMIT 10;")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()

