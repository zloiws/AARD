"""
Tests for A/B testing of prompt versions
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from app.core.prompt_manager import PromptManager
from app.core.execution_context import ExecutionContext
from app.models.prompt import Prompt, PromptType, PromptStatus


@pytest.mark.asyncio
async def test_get_prompt_with_ab_testing_no_testing_version(db):
    """Test A/B testing when no TESTING version exists"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    # Mock get_prompt_for_stage to return ACTIVE prompt
    mock_active = Mock()
    mock_active.name = "test_prompt"
    mock_active.version = 1
    mock_active.status = PromptStatus.ACTIVE.value.lower()
    mock_active.prompt_type = PromptType.SYSTEM.value.lower()
    
    with patch.object(manager, 'get_prompt_for_stage', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_active
        
        with patch.object(manager.prompt_service, 'list_prompts') as mock_list:
            mock_list.return_value = [mock_active]  # Only ACTIVE version
            
            prompt = await manager.get_prompt_with_ab_testing("planning")
            
            # Should return ACTIVE since no TESTING version
            assert prompt == mock_active


@pytest.mark.asyncio
async def test_get_prompt_with_ab_testing_with_testing_version(db):
    """Test A/B testing when TESTING version exists"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    # Mock prompts
    mock_active = Mock()
    mock_active.name = "test_prompt"
    mock_active.version = 1
    mock_active.status = PromptStatus.ACTIVE.value.lower()
    mock_active.prompt_type = PromptType.SYSTEM.value.lower()
    
    mock_testing = Mock()
    mock_testing.name = "test_prompt"
    mock_testing.version = 2
    mock_testing.status = PromptStatus.TESTING.value.lower()
    mock_testing.prompt_type = PromptType.SYSTEM.value.lower()
    
    with patch.object(manager, 'get_prompt_for_stage', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_active
        
        with patch.object(manager.prompt_service, 'list_prompts') as mock_list:
            mock_list.return_value = [mock_active, mock_testing]
            
            # Mock random to always return testing (for testing)
            with patch('app.core.prompt_manager.random.random', return_value=0.05):  # < 0.1
                prompt = await manager.get_prompt_with_ab_testing("planning")
                
                # Should return TESTING version
                assert prompt == mock_testing
