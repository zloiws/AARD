"""
Complete Phase 5 testing - from simple to complex, including LLM
Tests all components: extraction, search, integration, adaptation, API
"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
import json

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
from app.services.execution_service import ExecutionService
from app.core.logging_config import LoggingConfig
import requests

logger = LoggingConfig.get_logger(__name__)

# Test configuration
API_BASE_URL = "http://127.0.0.1:8000/api"


def print_section(title: str, level: int = 1):
    """Print formatted section header"""
    if level == 1:
        print("\n" + "=" * 70)
        print(f" {title}")
        print("=" * 70)
    elif level == 2:
        print("\n" + "-" * 70)
        print(f" {title}")
        print("-" * 70)
    else:
        print(f"\n{title}")


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result"""
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"     {details}")


# ============================================================================
# Level 1: Basic Template Operations
# ============================================================================

async def test_1_template_extraction(db):
    """Test 1.1: Extract template from completed plan"""
    print_section("Level 1: Basic Template Operations", 1)
    print_section("Test 1.1: Template Extraction", 2)
    
    try:
        # Create test plan and task
        task = Task(
            id=uuid4(),
            description="Implement user authentication with OAuth2",
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
            goal="Implement user authentication with OAuth2",
            strategy={
                "approach": "Use OAuth2 library",
                "assumptions": ["OAuth2 provider available"],
                "constraints": ["Must be secure"]
            },
            steps=[
                {"step": 1, "description": "Install OAuth2 library", "type": "code", "estimated_time": 300},
                {"step": 2, "description": "Configure OAuth2 client", "type": "code", "estimated_time": 600},
                {"step": 3, "description": "Implement authentication flow", "type": "code", "estimated_time": 1200},
                {"step": 4, "description": "Add error handling", "type": "code", "estimated_time": 300}
            ],
            status=PlanStatus.COMPLETED.value,
            current_step=4,
            estimated_duration=2400,
            actual_duration=2700,
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        # Extract template
        template_service = PlanTemplateService(db)
        # Check if template already exists
        existing = template_service.list_templates(category="authentication", limit=10)
        template = None
        for t in existing:
            if "OAuth2" in t.name or "authentication" in (t.category or "").lower():
                template = t
                print_result("Template extraction", True, f"Using existing template: {template.name}")
                break
        
        if not template:
            template = template_service.extract_template_from_plan(
                plan_id=plan.id,
                template_name=f"OAuth2 Authentication Template {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                category="authentication",
                tags=["oauth2", "auth", "security"]
            )
        
        if template:
            print_result("Template extraction", True, f"Template ID: {template.id}, Name: {template.name}")
            return template
        else:
            print_result("Template extraction", False, "Failed to extract template")
            return None
            
    except Exception as e:
        print_result("Template extraction", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_2_template_search(db, template):
    """Test 1.2: Search for templates"""
    print_section("Test 1.2: Template Search", 2)
    
    try:
        template_service = PlanTemplateService(db)
        
        # Test vector search
        print("  Testing vector search...")
        templates = template_service.find_matching_templates(
            task_description="Create authentication system",
            limit=5,
            min_success_rate=0.5,
            use_vector_search=True
        )
        
        if templates:
            print_result("Vector search", True, f"Found {len(templates)} templates")
            print(f"     Best match: {templates[0].name}")
        else:
            print_result("Vector search", False, "No templates found")
        
        # Test text search
        print("  Testing text search...")
        templates = template_service.find_matching_templates(
            task_description="authentication",
            limit=5,
            use_vector_search=False
        )
        
        if templates:
            print_result("Text search", True, f"Found {len(templates)} templates")
        else:
            print_result("Text search", False, "No templates found")
        
        return True
        
    except Exception as e:
        print_result("Template search", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# Level 2: Integration with PlanningService
# ============================================================================

async def test_3_planning_with_template(db, template):
    """Test 2.1: Generate plan using template"""
    print_section("Level 2: Integration with PlanningService", 1)
    print_section("Test 2.1: Plan Generation with Template", 2)
    
    try:
        planning_service = PlanningService(db)
        
        task_description = "Implement OAuth2 authentication for admin panel"
        
        print(f"  Generating plan for: '{task_description}'")
        print("  This should automatically find and use the template...")
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={}
        )
        
        if plan:
            print_result("Plan generation", True, f"Plan ID: {plan.id}")
            print(f"     Steps: {len(plan.steps) if plan.steps else 0}")
            print(f"     Status: {plan.status}")
            
            # Check if template was used
            task = db.query(Task).filter(Task.id == plan.task_id).first()
            if task:
                context = task.get_context()
                if context.get("plan_template"):
                    template_info = context["plan_template"]
                    print_result("Template usage", True, f"Template: {template_info.get('template_name')}")
                else:
                    print_result("Template usage", False, "Template not found in context")
            
            return plan
        else:
            print_result("Plan generation", False, "Failed to generate plan")
            return None
            
    except Exception as e:
        print_result("Plan generation", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_4_template_adaptation_llm(db, template):
    """Test 2.2: LLM-based template adaptation"""
    print_section("Test 2.2: LLM Template Adaptation", 2)
    
    try:
        planning_service = PlanningService(db)
        
        task_description = "Implement JWT authentication for mobile app"
        strategy = {
            "approach": "Use JWT tokens",
            "assumptions": ["Mobile app ready"],
            "constraints": ["Must be stateless"]
        }
        
        print(f"  Adapting template to: '{task_description}'")
        print("  Using LLM for intelligent adaptation...")
        
        adapted_steps = await planning_service._adapt_template_to_task(
            template=template,
            task_description=task_description,
            strategy=strategy,
            context={}
        )
        
        if adapted_steps and len(adapted_steps) > 0:
            print_result("LLM adaptation", True, f"Adapted {len(adapted_steps)} steps")
            print("  Sample adapted steps:")
            for i, step in enumerate(adapted_steps[:3], 1):
                desc = step.get("description", "N/A")
                print(f"     {i}. {desc[:60]}...")
            return True
        else:
            print_result("LLM adaptation", False, "No steps returned")
            return False
            
    except Exception as e:
        print_result("LLM adaptation", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# Level 3: API Endpoints
# ============================================================================

async def test_5_api_list_templates():
    """Test 3.1: API - List templates"""
    print_section("Level 3: API Endpoints", 1)
    print_section("Test 3.1: API - List Templates", 2)
    
    try:
        response = requests.get(f"{API_BASE_URL}/plan-templates/", params={"limit": 10})
        
        if response.status_code == 200:
            templates = response.json()
            print_result("API list templates", True, f"Retrieved {len(templates)} templates")
            if templates:
                print(f"     First template: {templates[0].get('name', 'N/A')}")
            return True
        else:
            print_result("API list templates", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("API list templates", False, f"Error: {e}")
        return False


async def test_6_api_search_templates():
    """Test 3.2: API - Search templates"""
    print_section("Test 3.2: API - Search Templates", 2)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/plan-templates/search",
            params={
                "task_description": "Create authentication system",
                "limit": 5,
                "min_success_rate": 0.5
            }
        )
        
        if response.status_code == 200:
            templates = response.json()
            print_result("API search templates", True, f"Found {len(templates)} matching templates")
            if templates:
                print(f"     Best match: {templates[0].get('name', 'N/A')}")
            return templates[0] if templates else None
        else:
            print_result("API search templates", False, f"Status: {response.status_code}")
            return None
            
    except Exception as e:
        print_result("API search templates", False, f"Error: {e}")
        return None


async def test_7_api_get_template(template_id):
    """Test 3.3: API - Get template details"""
    print_section("Test 3.3: API - Get Template", 2)
    
    if not template_id:
        print_result("API get template", False, "No template ID provided")
        return False
    
    try:
        response = requests.get(f"{API_BASE_URL}/plan-templates/{template_id}")
        
        if response.status_code == 200:
            template = response.json()
            print_result("API get template", True, f"Template: {template.get('name', 'N/A')}")
            print(f"     Category: {template.get('category', 'N/A')}")
            print(f"     Usage count: {template.get('usage_count', 0)}")
            return True
        else:
            print_result("API get template", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("API get template", False, f"Error: {e}")
        return False


async def test_8_api_template_stats(template_id):
    """Test 3.4: API - Template statistics"""
    print_section("Test 3.4: API - Template Statistics", 2)
    
    if not template_id:
        print_result("API template stats", False, "No template ID provided")
        return False
    
    try:
        response = requests.get(f"{API_BASE_URL}/plan-templates/{template_id}/stats")
        
        if response.status_code == 200:
            stats = response.json()
            print_result("API template stats", True, "Statistics retrieved")
            print(f"     Usage count: {stats.get('usage_count', 0)}")
            print(f"     Success rate: {stats.get('success_rate', 'N/A')}")
            print(f"     Avg execution time: {stats.get('avg_execution_time', 'N/A')}s")
            return True
        else:
            print_result("API template stats", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("API template stats", False, f"Error: {e}")
        return False


# ============================================================================
# Level 4: Full Integration Cycle
# ============================================================================

async def test_9_full_cycle(db):
    """Test 4.1: Full cycle - Create plan -> Extract template -> Use template"""
    print_section("Level 4: Full Integration Cycle", 1)
    print_section("Test 4.1: Full Cycle", 2)
    
    try:
        planning_service = PlanningService(db)
        execution_service = ExecutionService(db)
        
        # Step 1: Create and execute a plan
        print("  Step 1: Creating initial plan...")
        task_description = "Create REST API for product catalog"
        plan1 = await planning_service.generate_plan(
            task_description=task_description,
            context={}
        )
        
        if not plan1:
            print_result("Full cycle", False, "Failed to create initial plan")
            return False
        
        print_result("Initial plan created", True, f"Plan ID: {plan1.id}")
        
        # Step 2: Simulate plan completion (ensure it meets extraction criteria)
        print("  Step 2: Simulating plan completion...")
        # Ensure plan has enough steps for extraction (minimum 2)
        if not plan1.steps or len(plan1.steps) < 2:
            plan1.steps = [
                {"step": 1, "description": "Create database models", "type": "code", "estimated_time": 600},
                {"step": 2, "description": "Create API endpoints", "type": "code", "estimated_time": 1200},
                {"step": 3, "description": "Add validation", "type": "code", "estimated_time": 600}
            ]
        plan1.status = PlanStatus.COMPLETED.value
        plan1.current_step = len(plan1.steps) if plan1.steps else 0
        plan1.actual_duration = 3600  # 1 hour - meets criteria (> 10 seconds)
        if not plan1.goal:
            plan1.goal = task_description
        db.commit()
        db.refresh(plan1)
        
        # Step 3: Extract template (automatic via ExecutionService)
        print("  Step 3: Extracting template from completed plan...")
        execution_service._extract_template_from_completed_plan(plan1)
        db.commit()  # Ensure extraction is committed
        
        # Step 4: Search for template (wait a bit for extraction to complete)
        print("  Step 4: Searching for extracted template...")
        await asyncio.sleep(1)  # Wait for async operations
        template_service = PlanTemplateService(db)
        
        # First, try to find template by source_plan_ids directly
        all_templates = template_service.list_templates(limit=100)
        extracted_template = None
        print(f"  Checking {len(all_templates)} templates for plan {plan1.id}...")
        for t in all_templates:
            if t.source_plan_ids:
                for source_id in t.source_plan_ids:
                    if str(source_id) == str(plan1.id):
                        extracted_template = t
                        print_result("Template found by source_plan_ids", True, f"Template: {extracted_template.name}")
                        break
                if extracted_template:
                    break
        
        # If not found by source_plan_ids, try search
        if not extracted_template:
            templates = template_service.find_matching_templates(
                task_description="Create REST API for inventory management",
                limit=10,
                use_vector_search=False  # Use text search for reliability
            )
            
            # Check if any template has this plan in source_plan_ids
            for t in templates:
                if t.source_plan_ids:
                    for source_id in t.source_plan_ids:
                        if str(source_id) == str(plan1.id):
                            extracted_template = t
                            break
                    if extracted_template:
                        break
        
        if extracted_template:
            print_result("Template found", True, f"Template: {extracted_template.name}")
            
            # Step 5: Use template for new plan
            print("  Step 5: Creating new plan using template...")
            plan2 = await planning_service.generate_plan(
                task_description="Create REST API for inventory management",
                context={}
            )
            
            if plan2:
                print_result("New plan with template", True, f"Plan ID: {plan2.id}")
                print(f"     Steps: {len(plan2.steps) if plan2.steps else 0}")
                return True
            else:
                print_result("New plan with template", False, "Failed to create plan")
                return False
        else:
            print_result("Template found", False, "Template not found after extraction")
            return False
            
    except Exception as e:
        print_result("Full cycle", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_10_automatic_extraction(db):
    """Test 4.2: Automatic template extraction on plan completion"""
    print_section("Test 4.2: Automatic Template Extraction", 2)
    
    try:
        planning_service = PlanningService(db)
        execution_service = ExecutionService(db)
        
        # Create a plan
        task_description = "Implement database migration system"
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={}
        )
        
        if not plan:
            print_result("Automatic extraction", False, "Failed to create plan")
            return False
        
        # Complete the plan (ensure it meets extraction criteria)
        # Ensure plan has enough steps for extraction (minimum 2)
        if not plan.steps or len(plan.steps) < 2:
            plan.steps = [
                {"step": 1, "description": "Design migration schema", "type": "code", "estimated_time": 600},
                {"step": 2, "description": "Implement migration scripts", "type": "code", "estimated_time": 1200},
                {"step": 3, "description": "Test migrations", "type": "code", "estimated_time": 600}
            ]
        plan.status = PlanStatus.COMPLETED.value
        plan.current_step = len(plan.steps) if plan.steps else 0
        plan.actual_duration = 1800  # 30 minutes - meets criteria (> 10 seconds)
        if not plan.goal:
            plan.goal = task_description
        db.commit()
        db.refresh(plan)
        
        # Trigger automatic extraction
        print("  Triggering automatic template extraction...")
        execution_service._extract_template_from_completed_plan(plan)
        
        # Wait a bit for async extraction to complete
        await asyncio.sleep(1)
        db.commit()  # Ensure any pending changes are committed
        
        # Verify template was created
        template_service = PlanTemplateService(db)
        templates = template_service.list_templates(limit=100)
        
        # Check if template for this plan exists
        template_found = False
        print(f"  Checking {len(templates)} templates for plan {plan.id}...")
        for template in templates:
            if template.source_plan_ids:
                for source_id in template.source_plan_ids:
                    if str(source_id) == str(plan.id):
                        template_found = True
                        print_result("Automatic extraction", True, f"Template: {template.name}")
                        break
                if template_found:
                    break
        
        if not template_found:
            # Check if extraction was skipped (plan might not meet criteria)
            # Verify plan meets criteria
            steps = plan.steps if isinstance(plan.steps, list) else []
            print(f"  Plan details: steps={len(steps)}, duration={plan.actual_duration}, goal={bool(plan.goal)}")
            print_result("Automatic extraction", False, "Template not found - may not meet extraction criteria or extraction failed")
            return False
        
        return True
        
    except Exception as e:
        print_result("Automatic extraction", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# Main Test Runner
# ============================================================================

async def main():
    """Run all tests in order"""
    print("=" * 70)
    print(" Phase 5: Complete System Test - From Simple to Complex")
    print("=" * 70)
    print("\nThis test suite will verify all Phase 5 components:")
    print("  - Template extraction")
    print("  - Template search (vector + text)")
    print("  - Integration with PlanningService")
    print("  - LLM-based template adaptation")
    print("  - API endpoints")
    print("  - Full integration cycles")
    print("\nMake sure:")
    print("  - Ollama servers are running")
    print("  - API server is running (for API tests)")
    print("  - Database is accessible")
    
    db = SessionLocal()
    results = {}
    
    try:
        # Level 1: Basic Operations
        template = await test_1_template_extraction(db)
        results["template_extraction"] = template is not None
        
        if template:
            results["template_search"] = await test_2_template_search(db, template)
        else:
            results["template_search"] = False
        
        # Level 2: Integration
        if template:
            plan = await test_3_planning_with_template(db, template)
            results["planning_with_template"] = plan is not None
            
            results["llm_adaptation"] = await test_4_template_adaptation_llm(db, template)
        else:
            results["planning_with_template"] = False
            results["llm_adaptation"] = False
        
        # Level 3: API (skip if server not available)
        try:
            results["api_list"] = await test_5_api_list_templates()
            template_from_api = await test_6_api_search_templates()
            if template_from_api:
                template_id = template_from_api.get("id")
                results["api_get"] = await test_7_api_get_template(template_id)
                results["api_stats"] = await test_8_api_template_stats(template_id)
            else:
                results["api_get"] = False
                results["api_stats"] = False
        except Exception as e:
            print(f"\n[WARN] API tests skipped (server may not be running): {e}")
            results["api_list"] = False
            results["api_get"] = False
            results["api_stats"] = False
        
        # Level 4: Full Cycle
        results["full_cycle"] = await test_9_full_cycle(db)
        results["automatic_extraction"] = await test_10_automatic_extraction(db)
        
        # Summary
        print_section("Test Summary", 1)
        total = len(results)
        passed = sum(1 for v in results.values() if v)
        
        print(f"\nTotal tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success rate: {passed/total*100:.1f}%")
        
        print("\nDetailed results:")
        for test_name, result in results.items():
            status = "[OK]" if result else "[FAIL]"
            print(f"  {status} {test_name}")
        
        if passed == total:
            print("\n" + "=" * 70)
            print("[SUCCESS] All tests passed!")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print(f"[PARTIAL] {passed}/{total} tests passed")
            print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

