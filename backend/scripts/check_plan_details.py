"""
Check details of the latest plan
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.plan import Plan
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

def check_latest_plan():
    """Check the latest plan details"""
    db = SessionLocal()
    
    try:
        # Get latest plan (created in last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        plan = db.query(Plan).filter(
            Plan.created_at >= one_hour_ago
        ).order_by(Plan.created_at.desc()).first()
        
        if not plan:
            print("❌ No plans found in the last hour")
            return
        
        print(f"✅ Found plan: {plan.id}")
        print(f"   Goal: {plan.goal[:80]}...")
        print(f"   Status: {plan.status}")
        print(f"   Version: {plan.version}")
        print(f"   Created: {plan.created_at}")
        print(f"   Steps count: {len(plan.steps) if plan.steps else 0}")
        
        if plan.steps:
            print(f"\n📋 Steps ({len(plan.steps)}):")
            for i, step in enumerate(plan.steps, 1):
                step_id = step.get("step_id", "N/A")
                desc = step.get("description", "N/A")
                step_type = step.get("type", "N/A")
                print(f"   {i}. [{step_type}] {step_id}: {desc[:60]}...")
        else:
            print("\n❌ No steps in plan")
        
        if plan.strategy:
            print(f"\n📊 Strategy:")
            if isinstance(plan.strategy, dict):
                print(f"   Approach: {plan.strategy.get('approach', 'N/A')[:60]}...")
                print(f"   Assumptions: {len(plan.strategy.get('assumptions', []))}")
                print(f"   Constraints: {len(plan.strategy.get('constraints', []))}")
            else:
                print(f"   Strategy type: {type(plan.strategy)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" CHECKING LATEST PLAN DETAILS")
    print("=" * 70 + "\n")
    
    check_latest_plan()

