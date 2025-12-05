"""
Real LLM Full Workflow Test
Tests all modules with real LLM models and shows all errors
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
import json
import traceback

from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.services.agent_team_service import AgentTeamService
from app.services.ollama_service import OllamaService
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.agent_team import CoordinationStrategy
from app.models.agent import Agent, AgentStatus
from app.core.ollama_client import OllamaClient, TaskType


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 100)
    print(f" {title}")
    print("=" * 100)


def print_section(title: str):
    """Print formatted section"""
    print("\n" + "-" * 100)
    print(f" {title}")
    print("-" * 100)


def print_result(success: bool, message: str, details: dict = None):
    """Print test result"""
    status = "[OK]" if success else "[ERROR]"
    print(f"{status} {message}")
    if details:
        for key, value in details.items():
            print(f"     {key}: {value}")


@pytest.mark.asyncio
async def test_real_llm_full_workflow_with_errors(db):
    """
    Full workflow test with real LLM models
    Shows all errors and problems during execution
    """
    print_header("Real LLM Full Workflow Test - All Errors Visible")
    
    # ========================================================================
    # Step 1: Check Ollama Servers and Models
    # ========================================================================
    print_section("Step 1: Checking Ollama Servers and Models")
    
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No active Ollama servers available")
    
    # Prefer server 10.39.0.6 if available
    server = None
    for s in servers:
        if "10.39.0.6" in s.url:
            server = s
            break
    
    if not server:
        server = servers[0]
    
    print_result(True, f"Found {len(servers)} active server(s)")
    for s in servers:
        marker = " <-- USING" if s.id == server.id else ""
        print(f"     Server: {s.name} ({s.url}){marker}")
        models = OllamaService.get_models_for_server(db, str(s.id))
        print(f"     Models: {len(models)}")
        for model in models:
            print(f"       - {model.name} ({model.model_name})")
    models = OllamaService.get_models_for_server(db, str(server.id))
    if not models:
        pytest.skip(f"No active models on server {server.name}")
    
    model = models[0]
    print_result(True, f"Using server: {server.name}", {
        "url": server.url,
        "model": model.name,
        "model_name": model.model_name
    })
    
    # ========================================================================
    # Step 2: Test Direct LLM Call
    # ========================================================================
    print_section("Step 2: Testing Direct LLM Call")
    
    ollama_client = OllamaClient()
    
    try:
        print("Making direct LLM call...")
        response = await ollama_client.generate(
            prompt="Напиши привет мир на Python",
            task_type=TaskType.CODE_GENERATION,
            model=model.model_name,
            server_url=server.get_api_url()
        )
        
        response_text = response.response if hasattr(response, 'response') else str(response)
        print_result(True, "Direct LLM call successful", {
            "response_length": len(response_text),
            "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text
        })
        
    except Exception as e:
        print_result(False, "Direct LLM call failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        print(f"     Traceback:")
        traceback.print_exc()
    
    # ========================================================================
    # Step 3: Create Task
    # ========================================================================
    print_section("Step 3: Creating Task")
    
    task_description = "Напиши привет мир на Python"
    
    try:
        task = Task(
            description=task_description,
            status=TaskStatus.PENDING,
            created_by_role="user"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print_result(True, "Task created", {
            "task_id": str(task.id),
            "description": task.description,
            "status": task.status.value
        })
        
    except Exception as e:
        print_result(False, "Task creation failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        traceback.print_exc()
        raise
    
    # ========================================================================
    # Step 4: Generate Plan with PlanningService (Real LLM)
    # ========================================================================
    print_section("Step 4: Generating Plan with PlanningService (Real LLM)")
    
    planning_service = PlanningService(db)
    
    try:
        print("Calling PlanningService.generate_plan()...")
        print("This will use ModelSelector to select model from DB")
        print("And make real LLM calls through OllamaClient")
        
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
        
        print_result(True, "Plan generated successfully", {
            "duration": f"{duration:.2f}s",
            "plan_id": str(plan.id),
            "goal": plan.goal,
            "steps_count": len(plan.steps),
            "status": plan.status
        })
        
        print("\n     Plan Steps:")
        for i, step in enumerate(plan.steps, 1):
            step_desc = step.get("description", "N/A")
            step_type = step.get("type", "action")
            print(f"       {i}. [{step_type}] {step_desc}")
        
        if plan.strategy:
            print("\n     Strategy:")
            print(f"       {json.dumps(plan.strategy, indent=8, ensure_ascii=False)}")
        
    except Exception as e:
        print_result(False, "Plan generation failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        print(f"     Traceback:")
        traceback.print_exc()
        raise
    
    # ========================================================================
    # Step 5: Execute Plan with ExecutionService (Real LLM)
    # ========================================================================
    print_section("Step 5: Executing Plan with ExecutionService (Real LLM)")
    
    execution_service = ExecutionService(db)
    
    try:
        print("Calling ExecutionService.execute_plan()...")
        print("This will use ModelSelector to select code model from DB")
        print("And make real LLM calls for code generation")
        
        execution_start = datetime.now()
        
        executed_plan = await execution_service.execute_plan(plan.id)
        
        execution_duration = (datetime.now() - execution_start).total_seconds()
        
        assert executed_plan is not None, "Plan should be executed"
        
        db.refresh(executed_plan)
        
        print_result(True, "Plan execution attempted", {
            "duration": f"{execution_duration:.2f}s",
            "plan_id": str(executed_plan.id),
            "status": executed_plan.status,
            "current_step": executed_plan.current_step
        })
        
        # Show detailed execution results
        if executed_plan.steps:
            print("\n     Execution Results:")
            for i, step in enumerate(executed_plan.steps, 1):
                step_desc = step.get("description", "N/A")
                step_status = step.get("status", "unknown")
                step_output = step.get("output", "")
                step_error = step.get("error", "")
                step_metadata = step.get("metadata", {})
                
                print(f"\n       Step {i}: {step_desc[:60]}...")
                print(f"         Status: {step_status}")
                
                if step_output:
                    output_str = str(step_output)
                    print(f"         Output: {output_str[:200]}..." if len(output_str) > 200 else f"         Output: {output_str}")
                
                if step_error:
                    error_str = str(step_error)
                    print(f"         Error: {error_str[:200]}..." if len(error_str) > 200 else f"         Error: {error_str}")
                
                if step_metadata:
                    print(f"         Metadata: {json.dumps(step_metadata, indent=10, ensure_ascii=False)}")
        
        # Check if execution was successful
        if executed_plan.status == PlanStatus.COMPLETED.value:
            print_result(True, "Plan execution completed successfully")
        elif executed_plan.status == PlanStatus.FAILED.value:
            print_result(False, "Plan execution failed", {
                "reason": "Check step errors above"
            })
        else:
            print_result(True, f"Plan execution status: {executed_plan.status}")
        
    except Exception as e:
        print_result(False, "Plan execution failed with exception", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        print(f"     Traceback:")
        traceback.print_exc()
        # Don't raise - we want to see all errors
    
    # ========================================================================
    # Step 6: Test with Agent Team
    # ========================================================================
    print_section("Step 6: Testing with Agent Team")
    
    team_service = AgentTeamService(db)
    
    try:
        # Create team
        team = team_service.create_team(
            name=f"Test Team {uuid4()}",
            coordination_strategy=CoordinationStrategy.COLLABORATIVE.value,
            description="Team for testing"
        )
        team_service.activate_team(team.id)
        
        # Create agents
        agent1 = Agent(name=f"Test Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
        agent2 = Agent(name=f"Test Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
        db.add(agent1)
        db.add(agent2)
        db.commit()
        
        team_service.add_agent_to_team(team.id, agent1.id, role="planner")
        team_service.add_agent_to_team(team.id, agent2.id, role="executor")
        
        print_result(True, "Team created", {
            "team_id": str(team.id),
            "team_name": team.name,
            "agents_count": 2
        })
        
        # Create plan with team
        print("Creating plan with team...")
        
        team_plan = await planning_service.generate_plan(
            task_description="Создай простую функцию на Python",
            context={"team_id": str(team.id)}
        )
        
        print_result(True, "Plan created with team", {
            "plan_id": str(team_plan.id),
            "steps_count": len(team_plan.steps) if team_plan.steps else 0
        })
        
        # Check if team was used
        steps_with_team = [s for s in team_plan.steps if s.get("team_id") == str(team.id)] if team_plan.steps else []
        steps_with_agents = [s for s in team_plan.steps if s.get("agent")] if team_plan.steps else []
        
        print(f"     Steps with team_id: {len(steps_with_team)}")
        print(f"     Steps with agent: {len(steps_with_agents)}")
        
    except Exception as e:
        print_result(False, "Team test failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        print(f"     Traceback:")
        traceback.print_exc()
        # Don't raise - we want to see all errors
    
    # ========================================================================
    # Step 7: Final Summary
    # ========================================================================
    print_section("Step 7: Final Summary")
    
    print("\nTest completed. All errors and issues are shown above.")
    print("\nSummary:")
    print("  - Direct LLM call: Tested")
    print("  - PlanningService: Tested with real LLM")
    print("  - ExecutionService: Tested with real LLM")
    print("  - Agent Team: Tested")
    print("\nAll errors and problems are visible in the output above.")


@pytest.mark.asyncio
async def test_real_llm_error_detection(db):
    """
    Test error detection and handling with real LLM
    """
    print_header("Real LLM Error Detection Test")
    
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No active Ollama servers available")
    
    server = servers[0]
    models = OllamaService.get_models_for_server(db, str(server.id))
    if not models:
        pytest.skip(f"No active models on server {server.name}")
    
    # Filter out embedding models (they don't support chat API)
    non_embedding_models = [
        m for m in models 
        if m.model_name and not ("embedding" in m.model_name.lower() or "embed" in m.model_name.lower())
    ]
    if not non_embedding_models:
        pytest.skip(f"No non-embedding models on server {server.name}")
    
    model = non_embedding_models[0]
    
    planning_service = PlanningService(db)
    execution_service = ExecutionService(db)
    
    # Test with various task descriptions
    test_tasks = [
        "Напиши привет мир",
        "Создай функцию для вычисления факториала",
        "Напиши тест для функции сложения",
    ]
    
    for task_desc in test_tasks:
        print_section(f"Testing: {task_desc}")
        
        try:
            # Create task
            task = Task(
                description=task_desc,
                status=TaskStatus.PENDING,
                created_by_role="user"
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            
            # Generate plan
            plan = await planning_service.generate_plan(
                task_description=task_desc,
                task_id=task.id,
                context={}
            )
            
            print_result(True, "Plan generated", {
                "plan_id": str(plan.id),
                "steps": len(plan.steps) if plan.steps else 0
            })
            
            # Try to execute
            try:
                executed_plan = await execution_service.execute_plan(plan.id)
                db.refresh(executed_plan)
                
                print_result(
                    executed_plan.status == PlanStatus.COMPLETED.value,
                    f"Execution status: {executed_plan.status}",
                    {
                        "current_step": executed_plan.current_step
                    }
                )
                
            except Exception as e:
                print_result(False, "Execution failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                traceback.print_exc()
        
        except Exception as e:
            print_result(False, "Test failed", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            traceback.print_exc()

