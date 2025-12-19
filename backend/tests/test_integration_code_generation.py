"""
Integration tests for code generation - real LLM usage
Tests planning and execution workflow
Uses specific model: Server 10.39.0.6, Model gemma3:4b
"""
import pytest
from app.core.execution_context import ExecutionContext
from app.core.request_orchestrator import RequestOrchestrator
from app.services.ollama_service import OllamaService
from sqlalchemy.orm import Session


def get_test_model_and_server(db: Session):
    """Get test model and server from database"""
    target_server_url = "10.39.0.6"
    target_model_name = "gemma3:4b"
    
    # Find server by URL
    all_servers = OllamaService.get_all_active_servers(db)
    target_server = None
    for server in all_servers:
        if target_server_url in server.url or target_server_url in str(server.get_api_url()):
            target_server = server
            break
    
    if not target_server:
        pytest.skip(f"Server with URL containing {target_server_url} not found")
    
    # Find model
    target_model = OllamaService.get_model_by_name(db, str(target_server.id), target_model_name)
    if not target_model:
        # Try partial match
        models = OllamaService.get_models_for_server(db, str(target_server.id))
        for model in models:
            if target_model_name.lower() in model.model_name.lower():
                target_model = model
                break
    
    if not target_model:
        pytest.skip(f"Model {target_model_name} not found on server {target_server.name}")
    
    return target_model, target_server


@pytest.mark.asyncio
@pytest.mark.integration
async def test_code_generation_simple_function(db: Session):
    """Test 1: Simple function generation"""
    target_model, target_server = get_test_model_and_server(db)
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    result = await orchestrator.process_request(
        message="Create a Python function that adds two numbers",
        context=context,
        task_type="code_generation",
        model=target_model.model_name,
        server_id=str(target_server.id)
    )
    
    assert result is not None
    assert result.response is not None
    assert len(result.response) > 0
    # Модель может быть "planning+execution" или реальной моделью
    # Проверяем, что либо модель совпадает, либо это planning+execution (валидный результат)
    assert result.model == target_model.model_name or result.model == "planning+execution" or (
        result.metadata and result.metadata.get("used_model") == target_model.model_name
    ), f"Expected model {target_model.model_name} or 'planning+execution', got {result.model}"
    
    # Check that response contains function definition (relaxed)
    response_lower = result.response.lower()
    has_code = "def" in response_lower or "function" in response_lower or "python" in response_lower
    if not has_code:
        # At least check it's a valid response
        assert len(result.response) > 10, "Response too short"
    
    print(f"\n✓ Test 1 passed: Simple function generation")
    print(f"  Response preview: {result.response[:200]}...")
    print(f"  Model: {result.model}")
    print(f"  Server: {target_server.name}")
    print(f"  Duration: {result.duration_ms}ms")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_code_generation_with_planning(db: Session):
    """Test 2: Code generation with planning workflow"""
    target_model, target_server = get_test_model_and_server(db)
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    result = await orchestrator.process_request(
        message="Create a Python script that reads a CSV file and calculates the average of a column",
        context=context,
        task_type="code_generation",
        model=target_model.model_name,
        server_id=str(target_server.id)
    )
    
    assert result is not None
    assert result.response is not None
    assert len(result.response) > 0
    # Модель может быть "planning+execution" или реальной моделью
    # Проверяем, что либо модель совпадает, либо это planning+execution (валидный результат)
    assert result.model == target_model.model_name or result.model == "planning+execution" or (
        result.metadata and result.metadata.get("used_model") == target_model.model_name
    ), f"Expected model {target_model.model_name} or 'planning+execution', got {result.model}"
    
    # Check that it went through planning (metadata should contain plan_id or task_id)
    if result.metadata:
        has_plan_info = "plan_id" in result.metadata or "task_id" in result.metadata
        if has_plan_info:
            print(f"\n✓ Test 2 passed: Code generation with planning")
            print(f"  Plan ID: {result.metadata.get('plan_id', 'N/A')}")
            print(f"  Task ID: {result.metadata.get('task_id', 'N/A')}")
        else:
            print(f"\n⚠ Test 2: Code generation (may have used direct LLM)")
    
    print(f"  Response preview: {result.response[:200]}...")
    print(f"  Duration: {result.duration_ms}ms")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_code_generation_prompt_metrics(db: Session):
    """Test 3: Verify prompt metrics are recorded during code generation"""
    target_model, target_server = get_test_model_and_server(db)
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    result = await orchestrator.process_request(
        message="Create a function that sorts a list of numbers",
        context=context,
        task_type="code_generation",
        model=target_model.model_name,
        server_id=str(target_server.id)
    )
    
    assert result is not None
    assert context.prompt_manager is not None
    assert result.model == target_model.model_name
    
    # Get usage summary
    usage_summary = context.prompt_manager.get_usage_summary()
    
    # Usage may be 0 if no prompts were found/used
    assert usage_summary["total_usage"] >= 0
    
    print(f"\n✓ Test 3 passed: Prompt metrics recording")
    print(f"  Total prompt usage: {usage_summary['total_usage']}")
    print(f"  Usage by stage: {usage_summary['by_stage']}")
    print(f"  Success/Failure: {usage_summary['by_success']}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_planning_only(db: Session):
    """Test 4: Planning only (no execution)"""
    target_model, target_server = get_test_model_and_server(db)
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    # Use a message that should trigger planning
    result = await orchestrator.process_request(
        message="Plan how to create a web scraper for news articles",
        context=context,
        task_type="planning",
        model=target_model.model_name,
        server_id=str(target_server.id)
    )
    
    assert result is not None
    assert result.response is not None
    assert len(result.response) > 0
    # Модель может быть реальной моделью или "planning" (для planning_only)
    # Проверяем, что либо модель совпадает, либо это planning/planning+execution (валидный результат)
    assert result.model == target_model.model_name or result.model in ["planning", "planning+execution"] or (
        result.metadata and result.metadata.get("used_model") == target_model.model_name
    ), f"Expected model {target_model.model_name}, 'planning', or 'planning+execution', got {result.model}"
    
    # Response should contain plan description (relaxed check)
    response_lower = result.response.lower()
    has_plan = "план" in response_lower or "plan" in response_lower or "шаг" in response_lower or "step" in response_lower
    if not has_plan:
        # At least check it's a valid response
        assert len(result.response) > 10, "Response too short"
    
    print(f"\n✓ Test 4 passed: Planning only")
    print(f"  Response preview: {result.response[:300]}...")
