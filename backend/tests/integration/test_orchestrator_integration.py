"""
Integration tests for RequestOrchestrator
"""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.core.execution_context import ExecutionContext
from app.core.request_orchestrator import RequestOrchestrator
from app.core.request_router import RequestType


@pytest.mark.asyncio
async def test_orchestrator_full_workflow_simple_question(db):
    """Test full workflow for simple question"""
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    # Mock dependencies
    with patch('app.core.request_orchestrator.OllamaClient') as mock_ollama:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.response = "Answer to simple question"
        mock_client.generate = AsyncMock(return_value=mock_response)
        mock_ollama.return_value = mock_client
        
        with patch.object(orchestrator, '_select_model_and_server') as mock_select:
            mock_server = Mock()
            mock_server.get_api_url = lambda: "http://test"
            mock_select.return_value = ("test_model", mock_server)
            
            with patch.object(orchestrator, '_get_system_prompt', new_callable=AsyncMock) as mock_prompt:
                mock_prompt.return_value = None
                
                result = await orchestrator.process_request(
                    "What is 2+2?",
                    context
                )
                
                assert result is not None
                assert result.response == "Answer to simple question"
                assert result.duration_ms is not None


@pytest.mark.asyncio
async def test_orchestrator_error_handling(db):
    """Test error handling and fallback"""
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    # Mock to raise error initially, then succeed on fallback
    call_count = 0
    
    async def mock_handle_simple(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Test error")
        else:
            from app.core.request_orchestrator import OrchestrationResult
            return OrchestrationResult(response="Fallback response", model="test")
    
    with patch.object(orchestrator, '_handle_simple_question', side_effect=mock_handle_simple):
        result = await orchestrator.process_request(
            "Test message",
            context
        )
        
        # Should return result (either error or fallback)
        assert result is not None
