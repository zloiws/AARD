"""
Integration tests for PromptManager with PromptService
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.core.prompt_manager import PromptManager
from app.core.execution_context import ExecutionContext
from app.models.prompt import Prompt, PromptType, PromptStatus


@pytest.mark.asyncio
async def test_prompt_manager_with_real_prompt_service(db):
    """Test PromptManager with real PromptService"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    # Try to get prompt (may return None if no prompts in DB)
    prompt = await manager.get_prompt_for_stage("planning")
    
    # Should not raise exception
    assert True


@pytest.mark.asyncio
async def test_record_prompt_usage_integration(db):
    """Test recording prompt usage with real PromptService"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    # Create a test prompt
    from app.services.prompt_service import PromptService
    from app.models.prompt import PromptType
    
    prompt_service = PromptService(db)
    test_prompt = prompt_service.create_prompt(
        name="test_prompt_manager",
        prompt_text="Test prompt",
        prompt_type=PromptType.SYSTEM,
        level=0
    )
    
    # Record usage
    await manager.record_prompt_usage(
        prompt_id=test_prompt.id,
        success=True,
        execution_time_ms=100.0,
        stage="planning"
    )
    
    # Verify usage was tracked
    assert len(manager._usage_tracking) == 1
    
    # Cleanup
    db.delete(test_prompt)
    db.commit()
