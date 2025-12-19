"""
Tests for RequestOrchestrator
"""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.core.execution_context import ExecutionContext
from app.core.request_orchestrator import (OrchestrationResult,
                                           RequestOrchestrator)
from app.core.request_router import RequestType


def test_orchestration_result_creation():
    """Test OrchestrationResult creation"""
    result = OrchestrationResult(
        response="Test response",
        model="test_model",
        task_type="test_task",
        duration_ms=100
    )
    
    assert result.response == "Test response"
    assert result.model == "test_model"
    assert result.task_type == "test_task"
    assert result.duration_ms == 100
    assert result.metadata == {}


def test_request_orchestrator_initialization():
    """Test RequestOrchestrator initialization"""
    orchestrator = RequestOrchestrator()
    
    assert orchestrator.registry is not None
    assert orchestrator.workflow_tracker is not None


@pytest.mark.asyncio
async def test_request_orchestrator_simple_question(db):
    """Test handling simple question"""
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    # Mock OllamaClient
    with patch('app.core.request_orchestrator.OllamaClient') as mock_ollama:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.response = "Test response"
        mock_client.generate = AsyncMock(return_value=mock_response)
        mock_ollama.return_value = mock_client
        
        # Mock model selection
        with patch.object(orchestrator, '_select_model_and_server') as mock_select:
            mock_server = Mock()
            mock_server.get_api_url = lambda: "http://test"
            mock_select.return_value = ("test_model", mock_server)
            
            # Mock system prompt
            with patch.object(orchestrator, '_get_system_prompt', new_callable=AsyncMock) as mock_prompt:
                mock_prompt.return_value = None
                
                result = await orchestrator.process_request(
                    "Test question",
                    context,
                    task_type="general_chat"
                )
                
                assert result is not None
                assert isinstance(result, OrchestrationResult)
                assert result.response == "Test response"


@pytest.mark.asyncio
async def test_request_orchestrator_extract_plan_results():
    """Test extracting plan results"""
    orchestrator = RequestOrchestrator()
    
    # Mock plan
    mock_plan = Mock()
    mock_plan.steps = [
        {"output": "Step 1 output"},
        {"result": "Step 2 result"},
        {"output": "Step 3 output"}
    ]
    mock_plan.status = "completed"
    
    result = orchestrator._extract_plan_results(mock_plan)
    
    assert "Step 1 output" in result
    assert "Step 2 result" in result
    assert "Step 3 output" in result


def test_request_orchestrator_select_model_and_server(db):
    """Test model and server selection"""
    orchestrator = RequestOrchestrator()
    
    # Mock OllamaService and ModelSelector
    with patch('app.core.request_orchestrator.OllamaService') as mock_ollama_service:
        with patch('app.core.request_orchestrator.ModelSelector') as mock_selector:
            # Setup mocks
            mock_server = Mock()
            mock_server.id = "server1"
            mock_server.get_api_url = lambda: "http://test"
            
            mock_model = Mock()
            mock_model.model_name = "test_model"
            mock_model.is_active = True
            mock_model.capabilities = []
            
            mock_ollama_service.get_all_active_servers.return_value = [mock_server]
            mock_ollama_service.get_models_for_server.return_value = [mock_model]
            
            mock_selector_instance = Mock()
            mock_selector_instance.get_server_for_model.return_value = mock_server
            mock_selector.return_value = mock_selector_instance
            
            model, server = orchestrator._select_model_and_server(db)
            
            assert model is not None
            assert server is not None
