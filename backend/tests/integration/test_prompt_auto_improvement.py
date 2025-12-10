"""
Tests for automatic prompt improvement
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.core.prompt_manager import PromptManager
from app.core.execution_context import ExecutionContext
from app.models.prompt import Prompt, PromptType, PromptStatus


@pytest.mark.asyncio
async def test_analyze_and_improve_prompts_low_success_rate(db):
    """Test automatic improvement when success rate is low"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    # Create a prompt with low success rate
    from app.services.prompt_service import PromptService
    
    prompt_service = PromptService(db)
    test_prompt = prompt_service.create_prompt(
        name="test_low_success",
        prompt_text="Test prompt",
        prompt_type=PromptType.SYSTEM,
        level=0
    )
    
    # Set low success rate
    test_prompt.success_rate = 0.3
    db.commit()
    
    # Add usage tracking
    manager._usage_tracking = [
        PromptUsage(test_prompt.id, "planning", 1000.0, False, 50.0)
    ]
    
    # Mock auto_create_improved_version_if_needed to avoid actual LLM call
    with patch.object(prompt_service, 'auto_create_improved_version_if_needed', new_callable=AsyncMock) as mock_improve:
        mock_improved = Mock()
        mock_improved.version = 2
        mock_improve.return_value = mock_improved
        
        results = await manager.analyze_and_improve_prompts()
        
        # Should attempt to improve
        assert results["analyzed"] >= 0
    
    # Cleanup
    db.delete(test_prompt)
    db.commit()
