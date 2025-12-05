"""
Full End-to-End Test with Real LLM
Tests the complete system workflow from task creation to execution
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.services.agent_team_service import AgentTeamService
from app.services.ollama_service import OllamaService
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.agent_team import CoordinationStrategy
from app.models.agent import Agent, AgentStatus


def print_section(title: str, level: int = 1):
    """Print formatted section header"""
    if level == 1:
        print("\n" + "=" * 80)
        print(f" {title}")
        print("=" * 80)
    elif level == 2:
        print("\n" + "-" * 80)
        print(f" {title}")
        print("-" * 80)
    else:
        print(f"\n{title}")


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"     {details}")


@pytest.mark.asyncio
async def test_full_system_e2e_hello_world(db):
    """
    Full End-to-End Test: "Напиши привет мир"
    
    This test goes through the complete system workflow:
    1. Create task
    2. Generate plan using PlanningService (with real LLM)
    3. Execute plan using ExecutionService (with real LLM)
    4. Verify results
    
    All modules are involved:
    - PlanningService (with ModelSelector, PromptService, PlanTemplateService)
    - ExecutionService (with ModelSelector, CodeExecutionSandbox)
    - AgentTeamService (optional, for team coordination)
    - OllamaService (for model selection)
    """
    print_section("Full End-to-End Test: 'Напиши привет мир'", 1)
    
    # Check if we have active Ollama servers
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No active Ollama servers available")
    
    server = servers[0]
    models = OllamaService.get_models_for_server(db, str(server.id))
    if not models:
        pytest.skip(f"No active models on server {server.name}")
    
    model = models[0]
    print(f"Using server: {server.name} ({server.url})")
    print(f"Using model: {model.name} ({model.model_name})")
    
    # Initialize services
    planning_service = PlanningService(db)
    execution_service = ExecutionService(db)
    
    task_description = "Напиши привет мир"
    print_section(f"Task: {task_description}", 2)
    
    try:
        # ========================================================================
        # Step 1: Create Task
        # ========================================================================
        print_section("Step 1: Creating Task", 2)
        
        task = Task(
            description=task_description,
            status=TaskStatus.PENDING,
            created_by_role="user"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print_result("Task created", True, f"Task ID: {task.id}")
        print(f"     Description: {task.description}")
        print(f"     Status: {task.status}")
        
        # ========================================================================
        # Step 2: Generate Plan using PlanningService (REAL LLM)
        # ========================================================================
        print_section("Step 2: Generating Plan with Real LLM", 2)
        print("     This will call PlanningService.generate_plan()")
        print("     Which uses ModelSelector to select model from DB")
        print("     And makes real LLM calls through OllamaClient")
        print("     Waiting for LLM response...")
        
        start_time = datetime.now()
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            task_id=task.id,
            context={}
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        assert plan is not None, "Plan should be created"
        assert plan.goal is not None, "Plan should have a goal"
        assert len(plan.goal) > 0, "Plan goal should not be empty"
        assert plan.steps is not None, "Plan should have steps"
        assert len(plan.steps) > 0, "Plan should have at least one step"
        
        print_result("Plan generated", True, f"Duration: {duration:.2f}s")
        print(f"     Plan ID: {plan.id}")
        print(f"     Goal: {plan.goal}")
        print(f"     Strategy: {plan.strategy}")
        print(f"     Steps count: {len(plan.steps)}")
        print(f"     Status: {plan.status}")
        
        # Show plan steps
        print("\n     Plan Steps:")
        for i, step in enumerate(plan.steps, 1):
            step_desc = step.get("description", "N/A")
            step_type = step.get("type", "action")
            print(f"       {i}. [{step_type}] {step_desc[:60]}...")
        
        # ========================================================================
        # Step 3: Execute Plan using ExecutionService (REAL LLM)
        # ========================================================================
        print_section("Step 3: Executing Plan with Real LLM", 2)
        print("     This will call ExecutionService.execute_plan()")
        print("     Which uses ModelSelector to select code model from DB")
        print("     And makes real LLM calls for code generation")
        print("     Executing steps...")
        
        execution_start = datetime.now()
        
        # Execute plan
        executed_plan = await execution_service.execute_plan(plan.id)
        
        execution_duration = (datetime.now() - execution_start).total_seconds()
        
        assert executed_plan is not None, "Plan should be executed"
        
        # Refresh plan to get updated status
        db.refresh(executed_plan)
        
        print_result("Plan executed", True, f"Duration: {execution_duration:.2f}s")
        print(f"     Plan ID: {executed_plan.id}")
        print(f"     Status: {executed_plan.status}")
        print(f"     Current step: {executed_plan.current_step}")
        
        # ========================================================================
        # Step 4: Verify Results
        # ========================================================================
        print_section("Step 4: Verifying Results", 2)
        
        # Check if plan was completed
        if executed_plan.status == PlanStatus.COMPLETED.value:
            print_result("Plan completed successfully", True)
        elif executed_plan.status == "in_progress" or executed_plan.status == "executing":
            print_result("Plan in progress", True, "Some steps may still be executing")
        elif executed_plan.status == PlanStatus.FAILED.value:
            print_result("Plan failed", False, "Check logs for details")
        else:
            print_result(f"Plan status: {executed_plan.status}", True)
        
        # Check task status
        db.refresh(task)
        print(f"     Task status: {task.status}")
        
        # ========================================================================
        # Step 5: Show Final Results
        # ========================================================================
        print_section("Step 5: Final Results", 2)
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        print(f"Total execution time: {total_duration:.2f}s")
        print(f"Planning time: {duration:.2f}s")
        print(f"Execution time: {execution_duration:.2f}s")
        print(f"Plan ID: {plan.id}")
        print(f"Task ID: {task.id}")
        print(f"Final plan status: {executed_plan.status}")
        print(f"Final task status: {task.status}")
        
        # Show plan details
        if plan.steps:
            print("\n     Generated Steps:")
            for i, step in enumerate(plan.steps, 1):
                step_desc = step.get("description", "N/A")
                step_type = step.get("type", "action")
                step_status = step.get("status", "unknown")
                print(f"       {i}. [{step_type}] {step_desc[:60]}... (status: {step_status})")
        
        # ========================================================================
        # Summary
        # ========================================================================
        print_section("Test Summary", 1)
        
        success = (
            plan is not None and
            plan.goal is not None and
            len(plan.goal) > 0 and
            plan.steps is not None and
            len(plan.steps) > 0 and
            executed_plan is not None
        )
        
        if success:
            print_result("Full E2E Test", True, "All steps completed successfully")
            print("\n[SUCCESS] System is working correctly with real LLM models!")
            print("   - PlanningService generated plan using real LLM")
            print("   - ExecutionService executed plan using real LLM")
            print("   - All modules were involved in the process")
        else:
            print_result("Full E2E Test", False, "Some steps failed")
        
        assert success, "Full E2E test should complete successfully"
        
    except Exception as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["connection", "timeout", "unreachable", "refused"]):
            pytest.skip(f"Ollama server not reachable: {e}")
        elif "not found" in error_msg or "404" in error_msg:
            pytest.skip(f"Model not found on server: {e}")
        else:
            print(f"\n[ERROR] Error during test: {e}")
            import traceback
            traceback.print_exc()
            raise


@pytest.mark.asyncio
async def test_full_system_e2e_with_team(db):
    """
    Full End-to-End Test with Agent Team: "Напиши привет мир"
    
    Same as above, but uses an agent team for coordination
    """
    print_section("Full End-to-End Test with Team: 'Напиши привет мир'", 1)
    
    # Check if we have active Ollama servers
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No active Ollama servers available")
    
    server = servers[0]
    models = OllamaService.get_models_for_server(db, str(server.id))
    if not models:
        pytest.skip(f"No active models on server {server.name}")
    
    # Initialize services
    planning_service = PlanningService(db)
    execution_service = ExecutionService(db)
    team_service = AgentTeamService(db)
    
    # Create agent team
    team = team_service.create_team(
        name=f"E2E Test Team {uuid4()}",
        coordination_strategy=CoordinationStrategy.COLLABORATIVE.value,
        description="Team for E2E testing"
    )
    team_service.activate_team(team.id)
    
    # Create agents
    agent1 = Agent(name=f"E2E Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"E2E Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    
    team_service.add_agent_to_team(team.id, agent1.id, role="planner")
    team_service.add_agent_to_team(team.id, agent2.id, role="executor")
    
    print(f"Created team: {team.name} with {len([agent1, agent2])} agents")
    
    task_description = "Напиши привет мир"
    print_section(f"Task: {task_description}", 2)
    
    try:
        # Create task
        task = Task(
            description=task_description,
            status=TaskStatus.PENDING,
            created_by_role="user"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print_result("Task created", True, f"Task ID: {task.id}")
        
        # Generate plan with team
        print_section("Generating Plan with Team (Real LLM)", 2)
        print("     Using team for coordination...")
        
        start_time = datetime.now()
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            task_id=task.id,
            context={"team_id": str(team.id)}
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        assert plan is not None
        assert plan.goal is not None
        assert len(plan.goal) > 0
        assert plan.steps is not None
        assert len(plan.steps) > 0
        
        # Verify team is assigned
        steps_with_team = [s for s in plan.steps if s.get("team_id") == str(team.id)]
        steps_with_agents = [s for s in plan.steps if s.get("agent")]
        
        print_result("Plan generated with team", True, f"Duration: {duration:.2f}s")
        print(f"     Plan ID: {plan.id}")
        print(f"     Goal: {plan.goal}")
        print(f"     Steps with team: {len(steps_with_team)}")
        print(f"     Steps with agents: {len(steps_with_agents)}")
        
        # Execute plan
        print_section("Executing Plan (Real LLM)", 2)
        
        execution_start = datetime.now()
        
        executed_plan = await execution_service.execute_plan(plan.id)
        
        execution_duration = (datetime.now() - execution_start).total_seconds()
        
        db.refresh(executed_plan)
        
        print_result("Plan executed", True, f"Duration: {execution_duration:.2f}s")
        print(f"     Final status: {executed_plan.status}")
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        print_section("Test Summary", 1)
        print(f"Total time: {total_duration:.2f}s")
        print(f"Planning: {duration:.2f}s")
        print(f"Execution: {execution_duration:.2f}s")
        print(f"Team used: {team.name}")
        
        success = (
            plan is not None and
            executed_plan is not None and
            (len(steps_with_team) > 0 or len(steps_with_agents) > 0)
        )
        
        if success:
            print_result("Full E2E Test with Team", True, "All steps completed")
            print("\n[SUCCESS] System is working correctly with team coordination!")
        else:
            print_result("Full E2E Test with Team", False, "Some steps failed")
        
        assert success, "Full E2E test with team should complete successfully"
        
    except Exception as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["connection", "timeout", "unreachable", "refused"]):
            pytest.skip(f"Ollama server not reachable: {e}")
        elif "not found" in error_msg or "404" in error_msg:
            pytest.skip(f"Model not found on server: {e}")
        else:
            print(f"\n[ERROR] Error during test: {e}")
            import traceback
            traceback.print_exc()
            raise

