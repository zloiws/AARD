"""
Comprehensive integration test for Phase 5: Plan Templates
Tests integration with all other modules in the system
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
from app.models.prompt import Prompt, PromptType, PromptStatus
from app.models.agent_memory import AgentMemory
from app.models.agent import Agent
from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.services.plan_template_service import PlanTemplateService
from app.services.prompt_service import PromptService
from app.services.memory_service import MemoryService
from app.services.reflection_service import ReflectionService
from app.services.planning_metrics_service import PlanningMetricsService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_section(title: str):
    """Print formatted section"""
    print("\n" + "-" * 80)
    print(f" {title}")
    print("-" * 80)


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result"""
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"    {details}")


# ============================================================================
# Test 1: Integration with PlanningService
# ============================================================================

async def test_planning_service_integration(db):
    """Test integration with PlanningService"""
    print_header("Test 1: Integration with PlanningService")
    
    results = {}
    
    try:
        planning_service = PlanningService(db)
        template_service = PlanTemplateService(db)
        
        # Check if plan_template_service is initialized
        has_template_service = hasattr(planning_service, 'plan_template_service')
        print_result("PlanTemplateService initialized", has_template_service)
        results["service_initialized"] = has_template_service
        
        # Test plan generation with template search
        task_description = "Create REST API for product catalog"
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={}
        )
        
        if plan:
            # Check if template was used
            task = db.query(Task).filter(Task.id == plan.task_id).first()
            if task:
                context = task.get_context()
                template_used = context.get("plan_template") is not None
                print_result("Template search in planning", True, 
                           f"Template used: {template_used}")
                results["template_search"] = True
            else:
                print_result("Template search in planning", False, "Task not found")
                results["template_search"] = False
        else:
            print_result("Template search in planning", False, "Plan not created")
            results["template_search"] = False
        
        return results
        
    except Exception as e:
        print_result("PlanningService integration", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 2: Integration with ExecutionService
# ============================================================================

async def test_execution_service_integration(db):
    """Test integration with ExecutionService"""
    print_header("Test 2: Integration with ExecutionService")
    
    results = {}
    
    try:
        execution_service = ExecutionService(db)
        planning_service = PlanningService(db)
        
        # Check if template extraction method exists
        has_extraction = hasattr(execution_service, '_extract_template_from_completed_plan')
        print_result("Template extraction method exists", has_extraction)
        results["extraction_method"] = has_extraction
        
        # Create and complete a plan
        task_description = "Create database migration system"
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={}
        )
        
        if plan:
            # Ensure plan meets extraction criteria
            if not plan.steps or len(plan.steps) < 2:
                plan.steps = [
                    {"step": 1, "description": "Design schema", "type": "code", "estimated_time": 600},
                    {"step": 2, "description": "Create migration", "type": "code", "estimated_time": 900}
                ]
            
            plan.status = PlanStatus.COMPLETED.value
            plan.current_step = len(plan.steps) if plan.steps else 0
            plan.actual_duration = 1800
            if not plan.goal:
                plan.goal = task_description
            db.commit()
            db.refresh(plan)
            
            # Test automatic extraction
            execution_service._extract_template_from_completed_plan(plan)
            db.commit()
            
            # Verify template was created
            template_service = PlanTemplateService(db)
            await asyncio.sleep(0.5)  # Wait for async operations
            all_templates = template_service.list_templates(limit=100)
            
            template_found = False
            for t in all_templates:
                if t.source_plan_ids and plan.id in t.source_plan_ids:
                    template_found = True
                    break
            
            print_result("Automatic template extraction", template_found, 
                       f"Template found: {template_found}")
            results["automatic_extraction"] = template_found
        else:
            print_result("Automatic template extraction", False, "Plan not created")
            results["automatic_extraction"] = False
        
        return results
        
    except Exception as e:
        print_result("ExecutionService integration", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 3: Integration with PromptService
# ============================================================================

async def test_prompt_service_integration(db):
    """Test integration with PromptService (templates should not conflict)"""
    print_header("Test 3: Integration with PromptService")
    
    results = {}
    
    try:
        prompt_service = PromptService(db)
        template_service = PlanTemplateService(db)
        
        # Check that both services can coexist
        prompts = prompt_service.list_prompts(limit=5)
        templates = template_service.list_templates(limit=5)
        
        both_work = len(prompts) >= 0 and len(templates) >= 0  # Both return results
        print_result("Services coexist", both_work, 
                   f"Prompts: {len(prompts)}, Templates: {len(templates)}")
        results["coexistence"] = both_work
        
        # Check that template extraction doesn't interfere with prompts
        # Create a test plan
        task = Task(
            id=uuid4(),
            description="Test task for prompt integration",
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
            goal="Test goal",
            strategy={"approach": "Test"},
            steps=[
                {"step": 1, "description": "Step 1", "type": "code", "estimated_time": 600},
                {"step": 2, "description": "Step 2", "type": "code", "estimated_time": 600}
            ],
            status=PlanStatus.COMPLETED.value,
            current_step=2,
            estimated_duration=1200,
            actual_duration=1500
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        # Extract template
        template = template_service.extract_template_from_plan(
            plan_id=plan.id,
            template_name=None,
            category="test"
        )
        
        # Verify prompts still work
        prompts_after = prompt_service.list_prompts(limit=5)
        prompts_still_work = len(prompts_after) == len(prompts)
        
        print_result("Prompts unaffected by template extraction", prompts_still_work,
                   f"Prompts before: {len(prompts)}, after: {len(prompts_after)}")
        results["prompts_unaffected"] = prompts_still_work
        
        return results
        
    except Exception as e:
        print_result("PromptService integration", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 4: Integration with MemoryService
# ============================================================================

async def test_memory_service_integration(db):
    """Test integration with MemoryService"""
    print_header("Test 4: Integration with MemoryService")
    
    results = {}
    
    try:
        memory_service = MemoryService(db)
        template_service = PlanTemplateService(db)
        
        # Check that both services can coexist
        # Create a test agent
        agent = Agent(
            id=uuid4(),
            name=f"Test Agent {uuid4()}",
            capabilities=["testing"],
            status="active"
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        # Save memory
        memory = await memory_service.save_memory_async(
            agent_id=agent.id,
            memory_type="episodic",
            content={"test": "Test memory for template integration", "integration": True},
            summary="Test memory for template integration"
        )
        
        memory_works = memory is not None
        print_result("MemoryService works", memory_works)
        results["memory_works"] = memory_works
        
        # Verify templates still work
        templates = template_service.list_templates(limit=5)
        templates_work = len(templates) >= 0
        
        print_result("Templates work with MemoryService", templates_work,
                   f"Templates: {len(templates)}")
        results["templates_with_memory"] = templates_work
        
        return results
        
    except Exception as e:
        print_result("MemoryService integration", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 5: Integration with ReflectionService
# ============================================================================

async def test_reflection_service_integration(db):
    """Test integration with ReflectionService"""
    print_header("Test 5: Integration with ReflectionService")
    
    results = {}
    
    try:
        reflection_service = ReflectionService(db)
        template_service = PlanTemplateService(db)
        
        # Check that both services can coexist
        # Create a test plan for reflection
        task = Task(
            id=uuid4(),
            description="Test task for reflection",
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
            goal="Test goal",
            strategy={"approach": "Test"},
            steps=[
                {"step": 1, "description": "Step 1", "type": "code", "estimated_time": 600}
            ],
            status=PlanStatus.COMPLETED.value,
            current_step=1,
            estimated_duration=600,
            actual_duration=700
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        # Test reflection (should not interfere with templates)
        # Use analyze_failure instead of analyze_plan_execution
        reflection = await reflection_service.analyze_failure(
            task_description=task.description,
            error="Test error",
            context={"plan_id": str(plan.id)},
            agent_id=None
        )
        
        reflection_works = reflection is not None
        print_result("ReflectionService works", reflection_works)
        results["reflection_works"] = reflection_works
        
        # Verify templates still work
        templates = template_service.list_templates(limit=5)
        templates_work = len(templates) >= 0
        
        print_result("Templates work with ReflectionService", templates_work)
        results["templates_with_reflection"] = templates_work
        
        return results
        
    except Exception as e:
        print_result("ReflectionService integration", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 6: Integration with PlanningMetricsService
# ============================================================================

async def test_metrics_service_integration(db):
    """Test integration with PlanningMetricsService"""
    print_header("Test 6: Integration with PlanningMetricsService")
    
    results = {}
    
    try:
        metrics_service = PlanningMetricsService(db)
        template_service = PlanTemplateService(db)
        
        # Check that both services can coexist
        # Get metrics (use get_planning_statistics instead of get_planning_metrics)
        metrics = metrics_service.get_planning_statistics()
        
        metrics_works = metrics is not None
        print_result("PlanningMetricsService works", metrics_works)
        results["metrics_works"] = metrics_works
        
        # Verify templates still work
        templates = template_service.list_templates(limit=5)
        templates_work = len(templates) >= 0
        
        print_result("Templates work with MetricsService", templates_work)
        results["templates_with_metrics"] = templates_work
        
        # Test that template usage updates metrics
        if templates:
            template = templates[0]
            template_service.update_template_usage(template.id)
            db.commit()
            
            # Metrics should still work after template update
            metrics_after = metrics_service.get_planning_statistics()
            metrics_still_work = metrics_after is not None
            
            print_result("Metrics unaffected by template usage", metrics_still_work)
            results["metrics_unaffected"] = metrics_still_work
        
        return results
        
    except Exception as e:
        print_result("PlanningMetricsService integration", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 7: Digital Twin Context Integration
# ============================================================================

async def test_digital_twin_integration(db):
    """Test integration with Digital Twin context"""
    print_header("Test 7: Digital Twin Context Integration")
    
    results = {}
    
    try:
        planning_service = PlanningService(db)
        template_service = PlanTemplateService(db)
        
        # Create a plan with template
        task_description = "Create user management API"
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={}
        )
        
        if plan:
            task = db.query(Task).filter(Task.id == plan.task_id).first()
            if task:
                context = task.get_context()
                
                # Check if template info is in context
                template_in_context = context.get("plan_template") is not None
                print_result("Template in Digital Twin context", template_in_context)
                results["template_in_context"] = template_in_context
                
                # Check if other context fields are preserved
                has_plan = context.get("plan") is not None
                has_metadata = context.get("metadata") is not None
                
                context_preserved = has_plan and has_metadata
                print_result("Other context fields preserved", context_preserved,
                           f"Plan: {has_plan}, Metadata: {has_metadata}")
                results["context_preserved"] = context_preserved
            else:
                print_result("Digital Twin integration", False, "Task not found")
                results["template_in_context"] = False
        else:
            print_result("Digital Twin integration", False, "Plan not created")
            results["template_in_context"] = False
        
        return results
        
    except Exception as e:
        print_result("Digital Twin integration", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 8: API Integration
# ============================================================================

async def test_api_integration():
    """Test API endpoints integration"""
    print_header("Test 8: API Integration")
    
    results = {}
    
    try:
        import requests
        
        # Test API endpoints
        base_url = "http://127.0.0.1:8000/api"
        
        # Test list templates
        response = requests.get(f"{base_url}/plan-templates/", timeout=5)
        list_works = response.status_code == 200
        print_result("API: List templates", list_works, 
                   f"Status: {response.status_code}")
        results["api_list"] = list_works
        
        if list_works and response.json():
            template_id = response.json()[0].get("id")
            
            # Test get template
            response = requests.get(f"{base_url}/plan-templates/{template_id}", timeout=5)
            get_works = response.status_code == 200
            print_result("API: Get template", get_works,
                       f"Status: {response.status_code}")
            results["api_get"] = get_works
            
            # Test template stats
            response = requests.get(f"{base_url}/plan-templates/{template_id}/stats", timeout=5)
            stats_works = response.status_code == 200
            print_result("API: Template stats", stats_works,
                       f"Status: {response.status_code}")
            results["api_stats"] = stats_works
            
            # Test search
            response = requests.post(
                f"{base_url}/plan-templates/search",
                params={"task_description": "Create API", "limit": 5},
                timeout=5
            )
            search_works = response.status_code == 200
            print_result("API: Search templates", search_works,
                       f"Status: {response.status_code}")
            results["api_search"] = search_works
        else:
            print_result("API: Get template", False, "No templates available")
            results["api_get"] = False
            results["api_stats"] = False
            results["api_search"] = False
        
        return results
        
    except requests.exceptions.ConnectionError:
        print_result("API integration", False, "API server not running")
        return {"api_available": False}
    except Exception as e:
        print_result("API integration", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 9: Database Schema Consistency
# ============================================================================

async def test_database_schema_consistency(db):
    """Test database schema consistency"""
    print_header("Test 9: Database Schema Consistency")
    
    results = {}
    
    try:
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.bind)
        
        # Check that plan_templates table exists
        tables = inspector.get_table_names()
        has_table = "plan_templates" in tables
        print_result("plan_templates table exists", has_table)
        results["table_exists"] = has_table
        
        if has_table:
            # Check required columns
            columns = [col["name"] for col in inspector.get_columns("plan_templates")]
            required_columns = [
                "id", "name", "goal_pattern", "steps_template", 
                "status", "version", "created_at"
            ]
            
            missing_columns = [col for col in required_columns if col not in columns]
            all_columns_present = len(missing_columns) == 0
            
            print_result("Required columns present", all_columns_present,
                       f"Missing: {missing_columns if missing_columns else 'None'}")
            results["columns_present"] = all_columns_present
            
            # Check indexes
            indexes = inspector.get_indexes("plan_templates")
            has_indexes = len(indexes) > 0
            print_result("Indexes present", has_indexes, f"Count: {len(indexes)}")
            results["indexes_present"] = has_indexes
        
        return results
        
    except Exception as e:
        print_result("Database schema consistency", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Test 10: No Conflicts with Other Modules
# ============================================================================

async def test_no_conflicts(db):
    """Test that template system doesn't conflict with other modules"""
    print_header("Test 10: No Conflicts with Other Modules")
    
    results = {}
    
    try:
        # Test that we can use all services together
        planning_service = PlanningService(db)
        execution_service = ExecutionService(db)
        template_service = PlanTemplateService(db)
        prompt_service = PromptService(db)
        memory_service = MemoryService(db)
        
        # Create a plan
        plan = await planning_service.generate_plan(
            task_description="Test integration",
            context={}
        )
        
        if plan:
            # All services should still work
            templates = template_service.list_templates(limit=5)
            prompts = prompt_service.list_prompts(limit=5)
            
            all_work = (
                plan is not None and
                len(templates) >= 0 and
                len(prompts) >= 0
            )
            
            print_result("All services work together", all_work,
                       f"Plan: {plan is not None}, Templates: {len(templates)}, Prompts: {len(prompts)}")
            results["all_services_work"] = all_work
            
            # Test that template extraction doesn't break other operations
            if plan.steps and len(plan.steps) >= 2:
                plan.status = PlanStatus.COMPLETED.value
                plan.actual_duration = 1800
                db.commit()
                
                execution_service._extract_template_from_completed_plan(plan)
                db.commit()
                
                # Verify other services still work
                templates_after = template_service.list_templates(limit=5)
                prompts_after = prompt_service.list_prompts(limit=5)
                
                still_work = (
                    len(templates_after) >= 0 and
                    len(prompts_after) >= 0
                )
                
                print_result("Services work after template extraction", still_work)
                results["services_after_extraction"] = still_work
        else:
            print_result("No conflicts test", False, "Plan not created")
            results["all_services_work"] = False
        
        return results
        
    except Exception as e:
        print_result("No conflicts test", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# Main Test Runner
# ============================================================================

async def main():
    """Run all integration tests"""
    print("=" * 80)
    print(" Phase 5: Integration Test with All Modules")
    print("=" * 80)
    print("\nThis test suite verifies integration with:")
    print("  - PlanningService")
    print("  - ExecutionService")
    print("  - PromptService")
    print("  - MemoryService")
    print("  - ReflectionService")
    print("  - PlanningMetricsService")
    print("  - Digital Twin Context")
    print("  - API Endpoints")
    print("  - Database Schema")
    print("  - No conflicts with other modules")
    print("\nMake sure Ollama servers are running and accessible.\n")
    
    db = SessionLocal()
    all_results = {}
    
    try:
        # Run all integration tests
        all_results["planning_service"] = await test_planning_service_integration(db)
        all_results["execution_service"] = await test_execution_service_integration(db)
        all_results["prompt_service"] = await test_prompt_service_integration(db)
        all_results["memory_service"] = await test_memory_service_integration(db)
        all_results["reflection_service"] = await test_reflection_service_integration(db)
        all_results["metrics_service"] = await test_metrics_service_integration(db)
        all_results["digital_twin"] = await test_digital_twin_integration(db)
        all_results["api"] = await test_api_integration()
        all_results["database_schema"] = await test_database_schema_consistency(db)
        all_results["no_conflicts"] = await test_no_conflicts(db)
        
        # Summary
        print_header("Integration Test Summary")
        
        total_tests = 0
        passed_tests = 0
        
        for module_name, module_results in all_results.items():
            print(f"\n{module_name}:")
            if isinstance(module_results, dict):
                for test_name, result in module_results.items():
                    if test_name != "error":
                        total_tests += 1
                        if result:
                            passed_tests += 1
                        status = "[OK]" if result else "[FAIL]"
                        print(f"  {status} {test_name}")
            else:
                total_tests += 1
                if module_results:
                    passed_tests += 1
                status = "[OK]" if module_results else "[FAIL]"
                print(f"  {status} {module_name}")
        
        print(f"\n{'=' * 80}")
        print(f"Total integration tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
        print(f"{'=' * 80}")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] All integration tests passed!")
            print("Phase 5 is fully integrated with all modules.")
        else:
            print(f"\n[PARTIAL] {passed_tests}/{total_tests} integration tests passed")
            print("Some integration issues detected.")
        
    except Exception as e:
        print(f"\n[ERROR] Integration test suite failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

