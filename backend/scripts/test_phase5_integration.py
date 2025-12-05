"""
Real integration test for Phase 5: Plan Templates in PlanningService
Tests template search and usage during plan generation
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
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.models.plan_template import PlanTemplate, TemplateStatus
from app.services.planning_service import PlanningService
from app.services.plan_template_service import PlanTemplateService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def create_test_template(db):
    """Create a test template for API development"""
    template_service = PlanTemplateService(db)
    
    # Check if template already exists
    existing = template_service.list_templates(category="api_development", limit=1)
    if existing:
        print(f"[OK] Using existing template: {existing[0].name}")
        return existing[0]
    
    # Create a test plan and task first
    task = Task(
        id=uuid4(),
        description="Create a REST API for user management",
        status=TaskStatus.COMPLETED.value,
        priority=5
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Create a REST API for user management",
        strategy={
            "approach": "Use FastAPI framework",
            "assumptions": ["PostgreSQL database available"],
            "constraints": ["Must be RESTful"]
        },
        steps=[
            {
                "step": 1,
                "description": "Create database models for User",
                "type": "code",
                "estimated_time": 600
            },
            {
                "step": 2,
                "description": "Create API endpoints for CRUD operations",
                "type": "code",
                "estimated_time": 1200
            },
            {
                "step": 3,
                "description": "Add input validation and error handling",
                "type": "code",
                "estimated_time": 600
            }
        ],
        status=PlanStatus.COMPLETED.value,
        current_step=3,
        estimated_duration=2400,
        actual_duration=2700,
        created_at=datetime.utcnow() - timedelta(hours=2)
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Extract template from plan
    template = template_service.extract_template_from_plan(
        plan_id=plan.id,
        template_name="Test API Template",
        category="api_development",
        tags=["api", "rest", "fastapi"]
    )
    
    if template:
        print(f"[OK] Created test template: {template.name}")
        return template
    else:
        print("[ERROR] Failed to create template")
        return None


async def test_template_search_in_planning(planning_service, task_description):
    """Test 1: Template search during planning"""
    print("\n" + "=" * 70)
    print(" Test 1: Template Search During Planning")
    print("=" * 70)
    
    print(f"\n[INFO] Generating plan for: '{task_description}'")
    print("[INFO] This should trigger template search...")
    
    try:
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={}
        )
        
        print(f"[OK] Plan generated: {plan.id}")
        print(f"     Goal: {plan.goal[:60]}...")
        print(f"     Steps: {len(plan.steps) if plan.steps else 0}")
        print(f"     Status: {plan.status}")
        
        # Check if template was used (via context)
        task = planning_service.db.query(Task).filter(Task.id == plan.task_id).first()
        if task:
            context = task.get_context()
            if context.get("plan_template"):
                template_info = context["plan_template"]
                print(f"\n[OK] Template was found and used!")
                print(f"     Template ID: {template_info.get('template_id')}")
                print(f"     Template Name: {template_info.get('template_name')}")
                print(f"     Category: {template_info.get('category')}")
            else:
                print("\n[INFO] No template was found/used (this is OK if no matching template exists)")
        
        return plan
        
    except Exception as e:
        print(f"[ERROR] Plan generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_template_adaptation(planning_service, template, task_description):
    """Test 2: Template adaptation"""
    print("\n" + "=" * 70)
    print(" Test 2: Template Adaptation")
    print("=" * 70)
    
    print(f"\n[INFO] Testing adaptation of template '{template.name}' to task: '{task_description}'")
    
    strategy = {
        "approach": "Use FastAPI framework",
        "assumptions": ["PostgreSQL database available"],
        "constraints": ["Must be RESTful"]
    }
    
    try:
        adapted_steps = await planning_service._adapt_template_to_task(
            template=template,
            task_description=task_description,
            strategy=strategy,
            context={}
        )
        
        print(f"[OK] Template adapted: {len(adapted_steps)} steps")
        for i, step in enumerate(adapted_steps[:3], 1):
            print(f"     {i}. {step.get('description', 'N/A')[:60]}...")
        
        return adapted_steps
        
    except Exception as e:
        print(f"[ERROR] Template adaptation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main test function"""
    print("=" * 70)
    print(" Phase 5: Plan Templates Integration - Real Tests")
    print("=" * 70)
    print("\nThis will test template integration in PlanningService.")
    print("Make sure Ollama servers are running and accessible.\n")
    
    db = SessionLocal()
    
    try:
        # Create test template
        print("\n[SETUP] Creating test template...")
        template = create_test_template(db)
        
        if not template:
            print("[ERROR] Failed to create template, aborting tests")
            return
        
        # Initialize services
        planning_service = PlanningService(db)
        
        # Test 1: Template search during planning
        task_description = "Create a REST API for product management with authentication"
        plan = await test_template_search_in_planning(planning_service, task_description)
        
        if plan:
            # Test 2: Template adaptation
            await test_template_adaptation(
                planning_service,
                template,
                "Create a REST API for order management"
            )
            
            print("\n" + "=" * 70)
            print(" Test Summary")
            print("=" * 70)
            print("[SUCCESS] Integration tests completed!")
            print(f"\nPlan created: {plan.id}")
            print(f"Steps: {len(plan.steps) if plan.steps else 0}")
        else:
            print("\n[ERROR] Plan generation failed, skipping remaining tests")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

