"""Simple test script for alternative plan generation"""
import sys
import asyncio
from pathlib import Path
from uuid import uuid4

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.services.planning_service import PlanningService

async def main():
    db = SessionLocal()
    try:
        # Create test task
        task = Task(
            id=uuid4(),
            description="Create a REST API for user management",
            status=TaskStatus.PENDING,
            priority=5
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print(f"Created test task: {task.id}")
        
        # Create planning service
        planning_service = PlanningService(db)
        
        # Generate alternative plans
        print("\nGenerating 2 alternative plans...")
        alternative_plans = await planning_service.generate_alternative_plans(
            task_description="Create a REST API for user management",
            task_id=task.id,
            num_alternatives=2
        )
        
        print(f"\nGenerated {len(alternative_plans)} alternative plans:")
        for i, plan in enumerate(alternative_plans, 1):
            print(f"\nPlan {i}:")
            print(f"  ID: {plan.id}")
            print(f"  Status: {plan.status}")
            print(f"  Goal: {plan.goal[:100] if plan.goal else 'None'}...")
            print(f"  Steps: {len(plan.steps) if plan.steps else 0}")
            if isinstance(plan.strategy, dict):
                print(f"  Strategy: {plan.strategy.get('alternative_strategy', 'N/A')}")
            if isinstance(plan.alternatives, dict):
                print(f"  Alternative name: {plan.alternatives.get('alternative_name', 'N/A')}")
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

