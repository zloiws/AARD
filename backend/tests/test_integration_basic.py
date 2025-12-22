"""
Basic integration test - minimal test to verify system works
Uses specific model from database: Server 10.39.0.6, Model gemma3:4b
"""
import pytest
from app.core.execution_context import ExecutionContext
from app.core.request_orchestrator import RequestOrchestrator
from sqlalchemy.orm import Session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_basic_orchestrator_works(db: Session):
    """Minimal test: Check that orchestrator can be created and process a simple request"""
    from app.models.ollama_server import OllamaServer
    from app.services.ollama_service import OllamaService

    # Find specific server by URL/IP
    target_server_url = "10.39.0.6"
    target_model_name = "gemma3:4b"
    
    # Find server by URL
    all_servers = OllamaService.get_all_active_servers(db)
    target_server = None
    for server in all_servers:
        # Check if server URL contains the target IP
        if target_server_url in server.url or target_server_url in str(server.get_api_url()):
            target_server = server
            break
    
    if not target_server:
        pytest.skip(f"Server with URL containing {target_server_url} not found in database")
    
    print(f"Found server: {target_server.name} ({target_server.url})")
    
    # Find specific model
    target_model = OllamaService.get_model_by_name(db, str(target_server.id), target_model_name)
    
    if not target_model:
        # Try to find by partial name match
        models = OllamaService.get_models_for_server(db, str(target_server.id))
        for model in models:
            if target_model_name.lower() in model.model_name.lower():
                target_model = model
                break
    
    if not target_model:
        pytest.skip(f"Model {target_model_name} not found on server {target_server.name}")
    
    print(f"Using model: {target_model.model_name} (ID: {target_model.id})")
    
    # Test orchestrator creation
    orchestrator = RequestOrchestrator()
    assert orchestrator is not None
    
    # Test context creation
    context = ExecutionContext.from_db_session(db)
    assert context is not None
    assert context.db == db
    
    # Test simple request with specific model
    try:
        result = await orchestrator.process_request(
            message="Say hello",
            context=context,
            task_type="general_chat",
            model=target_model.model_name,
            server_id=str(target_server.id)
        )
        
        # Basic assertions
        assert result is not None, "Result should not be None"
        assert hasattr(result, 'response'), "Result should have response attribute"
        assert result.response is not None, "Response should not be None"
        assert len(result.response) > 0, "Response should not be empty"
        assert result.model == target_model.model_name, f"Expected model {target_model.model_name}, got {result.model}"
        
        print(f"\n✓ Basic test passed!")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Model: {result.model}")
        print(f"  Server: {target_server.name}")
        print(f"  Duration: {result.duration_ms}ms")
        
    except Exception as e:
        # Print full error for debugging
        import traceback
        print(f"\n✗ Test failed with error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        raise
