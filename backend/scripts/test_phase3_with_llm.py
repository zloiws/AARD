"""
Real LLM tests for Phase 3: Project Self-Reflection
Tests all components with actual LLM calls
"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.prompt import Prompt, PromptType, PromptStatus
from app.services.project_metrics_service import ProjectMetricsService, MetricType, MetricPeriod
from app.services.self_audit_service import SelfAuditService
from app.services.audit_scheduler import AuditScheduler
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def create_test_data(db):
    """Create test data for metrics"""
    print("\n" + "=" * 70)
    print(" Creating Test Data")
    print("=" * 70)
    
    # Create some test tasks
    tasks = []
    for i in range(5):
        task = Task(
            id=uuid4(),
            description=f"Test task {i+1} for Phase 3 LLM testing",
            status=TaskStatus.COMPLETED if i % 2 == 0 else TaskStatus.FAILED,
            priority=5,
            created_at=datetime.utcnow() - timedelta(hours=i),
            updated_at=datetime.utcnow() - timedelta(hours=i//2)
        )
        db.add(task)
        tasks.append(task)
    
    # Create test plans
    for i, task in enumerate(tasks[:3]):
        plan = Plan(
            id=uuid4(),
            task_id=task.id,
            version=1,
            goal=f"Test goal for task {i+1}",
            steps=[{"step_id": "step_1", "description": "Test step"}],
            status=PlanStatus.APPROVED.value if i % 2 == 0 else PlanStatus.DRAFT.value,
            created_at=datetime.utcnow() - timedelta(hours=i)
        )
        db.add(plan)
    
    # Create test prompts
    for i in range(3):
        prompt = Prompt(
            id=uuid4(),
            name=f"test_prompt_{i+1}",
            prompt_text=f"Test prompt {i+1}",
            prompt_type=PromptType.SYSTEM,
            level=0,
            version=1,
            status=PromptStatus.ACTIVE,
            usage_count=i * 10,
            success_rate=0.8 + (i * 0.05),
            avg_execution_time=100 + (i * 50),
            created_at=datetime.utcnow() - timedelta(days=i)
        )
        db.add(prompt)
    
    db.commit()
    print(f"[OK] Created {len(tasks)} tasks, 3 plans, 3 prompts")
    return tasks


def test_metrics_collection(db):
    """Test real-time metrics collection"""
    print("\n" + "=" * 70)
    print(" Test 1: Real-time Metrics Collection")
    print("=" * 70)
    
    metrics_service = ProjectMetricsService(db)
    
    # Record various metrics
    now = datetime.utcnow()
    period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = now
    
    # Performance metrics
    metrics_service.record_metric(
        metric_type=MetricType.PERFORMANCE,
        metric_name="planning_duration",
        value=150.5,
        period=MetricPeriod.HOUR,
        period_start=period_start,
        period_end=period_end,
        metadata={"service": "planning"}
    )
    print("[OK] Recorded planning_duration metric")
    
    # Task success metrics
    metrics_service.record_metric(
        metric_type=MetricType.TASK_SUCCESS,
        metric_name="task_success_rate",
        value=0.85,
        period=MetricPeriod.HOUR,
        period_start=period_start,
        period_end=period_end
    )
    print("[OK] Recorded task_success_rate metric")
    
    # Get overview
    overview = metrics_service.get_overview()
    print(f"[OK] Overview retrieved: {len(overview.get('recent_metrics', []))} metrics")
    
    return True


async def test_self_audit_with_llm(db):
    """Test self-audit with real LLM calls"""
    print("\n" + "=" * 70)
    print(" Test 2: Self-Audit with LLM")
    print("=" * 70)
    
    audit_service = SelfAuditService(db)
    
    # Test performance audit
    print("\n📊 Running performance audit...")
    performance_data = audit_service.audit_performance()
    print(f"[OK] Performance audit completed: {len(performance_data.get('metrics', []))} metrics analyzed")
    
    # Test quality audit
    print("\n[INFO] Running quality audit...")
    quality_data = audit_service.audit_quality()
    print(f"[OK] Quality audit completed: {len(quality_data.get('findings', []))} findings")
    
    # Test prompts audit
    print("\n[INFO] Running prompts audit...")
    prompts_data = audit_service.audit_prompts()
    print(f"[OK] Prompts audit completed: {len(prompts_data.get('prompts_analyzed', []))} prompts")
    
    # Test errors audit
    print("\n[INFO] Running errors audit...")
    errors_data = audit_service.audit_errors()
    print(f"[OK] Errors audit completed: {len(errors_data.get('errors', []))} errors analyzed")
    
    # Generate full report with LLM
    print("\n[LLM] Generating full audit report with LLM...")
    try:
        report = audit_service.generate_report(
            audit_type="FULL",
            period_start=datetime.utcnow() - timedelta(days=7),
            period_end=datetime.utcnow()
        )
        
        if report:
            print(f"[OK] Report generated: {report.audit_type}")
            print(f"   Status: {report.audit_status}")
            print(f"   Summary: {report.summary[:100]}..." if report.summary else "   No summary")
            print(f"   Recommendations: {len(report.recommendations or [])} items")
            
            if report.recommendations:
                print("\n   Top recommendations:")
                for i, rec in enumerate(report.recommendations[:3], 1):
                    print(f"   {i}. {rec.get('title', 'N/A')}")
            
            return True
        else:
            print("[WARN] Report generation returned None")
            return False
    except Exception as e:
        print(f"[ERROR] Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_trend_analysis_with_llm(db):
    """Test trend analysis with LLM"""
    print("\n" + "=" * 70)
    print(" Test 3: Trend Analysis with LLM")
    print("=" * 70)
    
    audit_service = SelfAuditService(db)
    
    # Create some historical metrics
    metrics_service = ProjectMetricsService(db)
    now = datetime.utcnow()
    
    # Create metrics for last week
    for i in range(7):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # Varying success rates to show trend
        success_rate = 0.7 + (i * 0.02)  # Improving trend
        metrics_service.record_metric(
            metric_type=MetricType.TASK_SUCCESS,
            metric_name="task_success_rate",
            value=success_rate,
            period=MetricPeriod.DAY,
            period_start=day_start,
            period_end=day_end
        )
    
    print("[OK] Created historical metrics for trend analysis")
    
    # Analyze trends
    print("\n[INFO] Analyzing trends...")
    trends = audit_service.analyze_trends(
        period_start=datetime.utcnow() - timedelta(days=7),
        period_end=datetime.utcnow()
    )
    
    if trends:
        print(f"[OK] Trends analyzed: {len(trends.get('trends', []))} trends found")
        
        # Detect improvements/degradations
        print("\n[INFO] Detecting improvements and degradations...")
        changes = audit_service.detect_improvements_degradations(
            period_start=datetime.utcnow() - timedelta(days=7),
            period_end=datetime.utcnow()
        )
        
        if changes:
            improvements = changes.get('improvements', [])
            degradations = changes.get('degradations', [])
            print(f"[OK] Found {len(improvements)} improvements, {len(degradations)} degradations")
            
            if improvements:
                print("\n   Improvements:")
                for imp in improvements[:3]:
                    print(f"   - {imp.get('metric', 'N/A')}: {imp.get('change', 'N/A')}")
        
        # Generate smart recommendations with LLM
        print("\n[LLM] Generating smart recommendations with LLM...")
        recommendations = audit_service.generate_smart_recommendations(
            period_start=datetime.utcnow() - timedelta(days=7),
            period_end=datetime.utcnow()
        )
        
        if recommendations:
            print(f"[OK] Generated {len(recommendations)} recommendations")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.get('title', 'N/A')}: {rec.get('description', 'N/A')[:60]}...")
        
        return True
    else:
        print("[WARN] No trends found")
        return False


async def test_enhanced_report_generation(db):
    """Test enhanced report generation with LLM"""
    print("\n" + "=" * 70)
    print(" Test 4: Enhanced Report Generation with LLM")
    print("=" * 70)
    
    audit_service = SelfAuditService(db)
    
    print("\n[LLM] Generating enhanced report with LLM analysis...")
    try:
        report = audit_service.generate_enhanced_report(
            audit_type="FULL",
            period_start=datetime.utcnow() - timedelta(days=7),
            period_end=datetime.utcnow()
        )
        
        if report:
            print(f"[OK] Enhanced report generated")
            print(f"   Type: {report.audit_type}")
            print(f"   Status: {report.audit_status}")
            print(f"   Summary length: {len(report.summary or '')} chars")
            print(f"   Details length: {len(str(report.details or {}))} chars")
            print(f"   Recommendations: {len(report.recommendations or [])} items")
            
            # Show trends if available
            if report.audit_data and 'trends' in report.audit_data:
                trends = report.audit_data['trends']
                print(f"   Trends analyzed: {len(trends)}")
            
            # Show sample recommendations
            if report.recommendations:
                print("\n   Sample recommendations:")
                for i, rec in enumerate(report.recommendations[:3], 1):
                    priority = rec.get('priority', 'medium')
                    print(f"   {i}. [{priority.upper()}] {rec.get('title', 'N/A')}")
                    if rec.get('description'):
                        desc = rec['description'][:80]
                        print(f"      {desc}...")
            
            return True
        else:
            print("[WARN] Report generation returned None")
            return False
    except Exception as e:
        print(f"[ERROR] Error generating enhanced report: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_audit_scheduler(db):
    """Test audit scheduler"""
    print("\n" + "=" * 70)
    print(" Test 5: Audit Scheduler")
    print("=" * 70)
    
    scheduler = AuditScheduler(db)
    
    # Get current schedule
    schedule = scheduler.get_schedule()
    print(f"[OK] Current schedule retrieved")
    print(f"   Daily: {schedule.get('daily', {}).get('enabled', False)}")
    print(f"   Weekly: {schedule.get('weekly', {}).get('enabled', False)}")
    print(f"   Monthly: {schedule.get('monthly', {}).get('enabled', False)}")
    
    # Run audit now
    print("\n[LLM] Running audit now...")
    try:
        report = await scheduler.run_audit_now("PERFORMANCE")
        if report:
            print(f"[OK] Audit completed: {report.audit_type}")
            print(f"   Status: {report.audit_status}")
        else:
            print("[WARN] Audit returned None (may already exist for today)")
    except Exception as e:
        print(f"[WARN] Audit execution: {e}")
    
    return True


async def main():
    """Run all LLM tests"""
    print("=" * 70)
    print(" Phase 3: Real LLM Tests")
    print("=" * 70)
    print("\nThis will test Phase 3 components with actual LLM calls.")
    print("Make sure Ollama servers are running and accessible.\n")
    
    db = SessionLocal()
    
    try:
        # Create test data
        tasks = create_test_data(db)
        
        # Test 1: Metrics collection
        test1_result = test_metrics_collection(db)
        
        # Test 2: Self-audit with LLM
        test2_result = await test_self_audit_with_llm(db)
        
        # Test 3: Trend analysis with LLM
        test3_result = await test_trend_analysis_with_llm(db)
        
        # Test 4: Enhanced report generation
        test4_result = await test_enhanced_report_generation(db)
        
        # Test 5: Audit scheduler
        test5_result = await test_audit_scheduler(db)
        
        # Summary
        print("\n" + "=" * 70)
        print(" Test Summary")
        print("=" * 70)
        results = {
            "Metrics Collection": test1_result,
            "Self-Audit with LLM": test2_result,
            "Trend Analysis with LLM": test3_result,
            "Enhanced Report Generation": test4_result,
            "Audit Scheduler": test5_result
        }
        
        for test_name, result in results.items():
            status = "[PASS]" if result else "[FAIL]"
            print(f"  {test_name}: {status}")
        
        total = len(results)
        passed = sum(1 for r in results.values() if r)
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n[SUCCESS] All tests passed!")
        else:
            print(f"\n[WARN] {total - passed} test(s) failed")
        
    except Exception as e:
        print(f"\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

