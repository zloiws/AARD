"""
Quick LLM test for Phase 3 - tests only essential LLM functionality
"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import SessionLocal
from app.services.self_audit_service import SelfAuditService
from app.services.project_metrics_service import ProjectMetricsService, MetricType, MetricPeriod
from app.models.audit_report import AuditType
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


async def test_llm_audit():
    """Test LLM-based audit"""
    print("=" * 70)
    print(" Phase 3: Quick LLM Test")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Create some test metrics
        print("\n[1/3] Creating test metrics...")
        metrics_service = ProjectMetricsService(db)
        now = datetime.utcnow()
        
        for i in range(3):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            metrics_service.record_metric(
                metric_type=MetricType.TASK_SUCCESS,
                metric_name="task_success_rate",
                value=0.7 + (i * 0.05),
                period=MetricPeriod.DAY,
                period_start=day_start,
                period_end=day_end
            )
        
        print("[OK] Created 3 test metrics")
        
        # Test LLM audit
        print("\n[2/3] Running LLM-based audit...")
        audit_service = SelfAuditService(db)
        
        report = await audit_service.generate_report(
            audit_type=AuditType.PERFORMANCE,
            period_start=datetime.utcnow() - timedelta(days=7),
            period_end=datetime.utcnow()
        )
        
        if report:
            print(f"[OK] Report generated: {report.audit_type}")
            print(f"   Status: {report.status}")
            print(f"   Summary: {report.summary[:150] if report.summary else 'None'}...")
            recs = report.recommendations or {}
            if isinstance(recs, dict):
                recs_count = len(recs.get('all_recommendations', []) or recs.get('recommendations', []))
            else:
                recs_count = len(recs) if isinstance(recs, list) else 0
            print(f"   Recommendations: {recs_count} items")
            
            if report.recommendations:
                recs = report.recommendations
                if isinstance(recs, dict):
                    recs_list = recs.get('all_recommendations', []) or recs.get('recommendations', [])
                else:
                    recs_list = recs if isinstance(recs, list) else []
                
                if recs_list:
                    print("\n   Sample recommendations:")
                    for i, rec in enumerate(recs_list[:2], 1):
                        print(f"   {i}. {rec.get('title', 'N/A') if isinstance(rec, dict) else str(rec)}")
        else:
            print("[WARN] Report is None")
        
        # Test enhanced report
        print("\n[3/3] Testing enhanced report with LLM...")
        enhanced = await audit_service.generate_enhanced_report(
            audit_type=AuditType.PERFORMANCE,
            period_start=datetime.utcnow() - timedelta(days=7),
            period_end=datetime.utcnow()
        )
        
        if enhanced:
            print(f"[OK] Enhanced report generated")
            print(f"   Type: {enhanced.audit_type}")
            print(f"   Recommendations: {len(enhanced.recommendations or [])} items")
        else:
            print("[WARN] Enhanced report is None")
        
        print("\n" + "=" * 70)
        print("[SUCCESS] LLM tests completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_llm_audit())

