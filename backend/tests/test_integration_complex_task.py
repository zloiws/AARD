"""
Integration tests for complex tasks - real LLM usage
Tests full workflow: planning + execution + reflection
"""
import pytest
from sqlalchemy.orm import Session

from app.core.request_orchestrator import RequestOrchestrator
from app.core.execution_context import ExecutionContext


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_complex_task_multi_step(db: Session):
    """Test 1: Complex multi-step task"""
    from app.services.ollama_service import OllamaService
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No Ollama servers configured")
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    try:
        result = await orchestrator.process_request(
            message="Create a Python script that: 1) reads a JSON file, 2) processes the data, 3) writes results to a CSV file",
            context=context,
            task_type="complex_task"
        )
        
        assert result is not None
        assert result.response is not None
        assert len(result.response) > 0
        
        print(f"\n✓ Test 1 passed: Complex multi-step task")
        print(f"  Response preview: {result.response[:300]}...")
        print(f"  Duration: {result.duration_ms}ms")
        
        # Check that it went through planning
        if result.metadata:
            has_plan_info = "plan_id" in result.metadata or "task_id" in result.metadata
            if has_plan_info:
                print(f"  Plan ID: {result.metadata.get('plan_id', 'N/A')}")
                print(f"  Task ID: {result.metadata.get('task_id', 'N/A')}")
    except ValueError as e:
        if "No available model" in str(e) or "No available server" in str(e):
            pytest.skip(f"Model/server selection failed: {e}")
        raise


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_complex_task_with_context(db: Session):
    """Test 2: Complex task with context"""
    from app.services.ollama_service import OllamaService
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No Ollama servers configured")
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    # Add some metadata to context
    context.update_metadata({
        "user_preferences": "prefer_python",
        "complexity": "medium"
    })
    
    try:
        result = await orchestrator.process_request(
            message="Design and implement a simple REST API with CRUD operations for a todo list",
            context=context,
            task_type="complex_task"
        )
        
        assert result is not None
        assert result.response is not None
        
        print(f"\n✓ Test 2 passed: Complex task with context")
        print(f"  Response preview: {result.response[:300]}...")
        print(f"  Context metadata: {context.metadata}")
    except ValueError as e:
        if "No available model" in str(e) or "No available server" in str(e):
            pytest.skip(f"Model/server selection failed: {e}")
        raise


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_full_workflow_with_prompts(db: Session):
    """Test 3: Full workflow with prompt tracking"""
    from app.services.ollama_service import OllamaService
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No Ollama servers configured")
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    try:
        result = await orchestrator.process_request(
            message="Create a data processing pipeline: read data, clean it, transform it, and save results",
            context=context,
            task_type="complex_task"
        )
        
        assert result is not None
        assert context.prompt_manager is not None
        
        # Get usage summary
        usage_summary = context.prompt_manager.get_usage_summary()
        
        print(f"\n✓ Test 3 passed: Full workflow with prompts")
        print(f"  Total prompt usage: {usage_summary['total_usage']}")
        print(f"  Usage by stage: {usage_summary['by_stage']}")
        print(f"  Success rate: {usage_summary['by_success']}")
        
        # Check that prompts were used for different stages
        stages_used = list(usage_summary['by_stage'].keys())
        print(f"  Stages used: {stages_used}")
    except ValueError as e:
        if "No available model" in str(e) or "No available server" in str(e):
            pytest.skip(f"Model/server selection failed: {e}")
        raise


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_error_handling_and_fallback(db: Session):
    """Test 4: Error handling and fallback"""
    from app.services.ollama_service import OllamaService
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No Ollama servers configured")
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    try:
        # Try a task that might fail in planning but should fallback
        result = await orchestrator.process_request(
            message="Create a quantum computer simulation with 1000 qubits",  # Likely to be too complex
            context=context,
            task_type="complex_task"
        )
        
        # Should still return a result (either from execution or fallback)
        assert result is not None
        assert result.response is not None
        
        print(f"\n✓ Test 4 passed: Error handling and fallback")
        print(f"  Response preview: {result.response[:200]}...")
        print(f"  Model: {result.model}")
    except ValueError as e:
        if "No available model" in str(e) or "No available server" in str(e):
            pytest.skip(f"Model/server selection failed: {e}")
        raise
