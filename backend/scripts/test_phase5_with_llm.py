"""
Real LLM tests for Phase 5: Plan Templates System
Tests template extraction and search functionality with actual LLM models
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
from app.services.plan_template_service import PlanTemplateService
from app.services.execution_service import ExecutionService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def create_test_plan_and_task(db):
    """Create a test plan and task for template extraction"""
    # Create task
    task = Task(
        id=uuid4(),
        description="Create a REST API for user management with authentication",
        status=TaskStatus.COMPLETED.value,
        priority=5
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create completed plan
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Create a REST API for user management with authentication",
        strategy={
            "approach": "Use FastAPI framework",
            "assumptions": ["PostgreSQL database available"],
            "constraints": ["Must be RESTful", "Must include authentication"]
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
                "description": "Add JWT authentication",
                "type": "code",
                "estimated_time": 900
            },
            {
                "step": 4,
                "description": "Add input validation and error handling",
                "type": "code",
                "estimated_time": 600
            }
        ],
        status=PlanStatus.COMPLETED.value,
        current_step=4,
        estimated_duration=3300,
        actual_duration=3600,
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    print(f"[OK] Created test plan: {plan.id}")
    print(f"     Task: {task.description[:60]}...")
    print(f"     Steps: {len(plan.steps)}")
    
    return plan, task


async def test_template_extraction(template_service, plan_id):
    """Test 1: Extract template from completed plan"""
    print("\n" + "=" * 70)
    print(" Test 1: Template Extraction from Completed Plan")
    print("=" * 70)
    
    print(f"\n[INFO] Extracting template from plan {plan_id}...")
    
    template = template_service.extract_template_from_plan(
        plan_id=plan_id,
        template_name=None,  # Auto-generate
        category=None,  # Auto-infer
        tags=None  # Auto-infer
    )
    
    if template:
        print(f"[OK] Template extracted: {template.id}")
        print(f"     Name: {template.name}")
        print(f"     Category: {template.category}")
        print(f"     Tags: {template.tags}")
        print(f"     Status: {template.status}")
        print(f"     Goal pattern: {template.goal_pattern[:80]}...")
        print(f"     Steps template: {len(template.steps_template)} steps")
        return template
    else:
        print("[ERROR] Failed to extract template")
        return None


async def test_template_search(template_service, task_description):
    """Test 2: Search for matching templates"""
    print("\n" + "=" * 70)
    print(" Test 2: Template Search")
    print("=" * 70)
    
    print(f"\n[INFO] Searching for templates matching: '{task_description}'")
    
    # Try vector search first
    print("\n[INFO] Using vector search...")
    templates = template_service.find_matching_templates(
        task_description=task_description,
        limit=5,
        min_success_rate=0.5,
        use_vector_search=True
    )
    
    if templates:
        print(f"[OK] Found {len(templates)} templates (vector search)")
        for i, template in enumerate(templates[:3], 1):
            print(f"     {i}. {template.name}")
            print(f"        Category: {template.category}, Success rate: {template.success_rate}")
    else:
        print("[WARN] No templates found with vector search, trying text search...")
        templates = template_service.find_matching_templates(
            task_description=task_description,
            limit=5,
            use_vector_search=False
        )
        if templates:
            print(f"[OK] Found {len(templates)} templates (text search)")
            for i, template in enumerate(templates[:3], 1):
                print(f"     {i}. {template.name}")
    
    return templates


async def test_automatic_extraction(execution_service, plan):
    """Test 3: Automatic template extraction on plan completion"""
    print("\n" + "=" * 70)
    print(" Test 3: Automatic Template Extraction")
    print("=" * 70)
    
    print(f"\n[INFO] Simulating plan completion for plan {plan.id}...")
    
    # The plan is already completed, so we'll call the extraction method directly
    execution_service._extract_template_from_completed_plan(plan)
    
    print("[OK] Automatic extraction completed (check logs for details)")


async def test_template_ranking(template_service):
    """Test 4: Template ranking by relevance"""
    print("\n" + "=" * 70)
    print(" Test 4: Template Ranking")
    print("=" * 70)
    
    # Create mock templates with different scores
    from unittest.mock import Mock
    
    template1 = Mock(spec=PlanTemplate)
    template1.success_rate = 0.8
    template1.usage_count = 5
    template1.name = "API Template 1"
    template1.description = "REST API development"
    template1.goal_pattern = "Create REST API"
    template1.category = "api_development"
    
    template2 = Mock(spec=PlanTemplate)
    template2.success_rate = 0.9
    template2.usage_count = 20
    template2.name = "API Template 2"
    template2.description = "REST API with authentication"
    template2.goal_pattern = "Create REST API with auth"
    template2.category = "api_development"
    
    templates = [template1, template2]
    
    print("\n[INFO] Ranking templates for: 'Create REST API with authentication'")
    ranked = template_service._rank_templates(templates, "Create REST API with authentication")
    
    print(f"[OK] Ranked {len(ranked)} templates")
    for i, template in enumerate(ranked, 1):
        print(f"     {i}. {template.name} (success: {template.success_rate}, usage: {template.usage_count})")


async def main():
    """Main test function"""
    print("=" * 70)
    print(" Phase 5: Plan Templates System - Real LLM Tests")
    print("=" * 70)
    print("\nThis will test Phase 5 components with actual LLM models.")
    print("Make sure Ollama servers are running and accessible.\n")
    
    db = SessionLocal()
    
    try:
        # Create test plan and task
        print("\n[SETUP] Creating test plan and task...")
        plan, task = create_test_plan_and_task(db)
        
        # Initialize services
        template_service = PlanTemplateService(db)
        execution_service = ExecutionService(db)
        
        # Test 1: Template extraction
        template = await test_template_extraction(template_service, plan.id)
        
        if template:
            # Test 2: Template search
            await test_template_search(
                template_service,
                "Create a REST API for product management"
            )
            
            # Test 3: Automatic extraction
            await test_automatic_extraction(execution_service, plan)
            
            # Test 4: Template ranking
            await test_template_ranking(template_service)
            
            print("\n" + "=" * 70)
            print(" Test Summary")
            print("=" * 70)
            print("[SUCCESS] All tests completed!")
            print(f"\nTemplate created: {template.id}")
            print(f"Template name: {template.name}")
            print(f"Category: {template.category}")
            print(f"Tags: {template.tags}")
        else:
            print("\n[ERROR] Template extraction failed, skipping remaining tests")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

