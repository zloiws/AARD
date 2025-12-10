"""
Tests for PromptManager
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.core.prompt_manager import PromptManager, PromptUsage
from app.core.execution_context import ExecutionContext
from app.models.prompt import Prompt, PromptType, PromptStatus


def test_prompt_manager_initialization(db):
    """Test PromptManager initialization"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    assert manager.context == context
    assert manager.prompt_service is not None
    assert manager._usage_tracking == []
    assert manager._ab_testing_enabled is True


@pytest.mark.asyncio
async def test_get_prompt_for_stage(db):
    """Test getting prompt for stage"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    # Mock PromptService
    with patch.object(manager.prompt_service, 'get_active_prompt') as mock_get:
        mock_prompt = Mock()
        mock_prompt.id = uuid4()
        mock_prompt.name = "test_prompt"
        mock_get.return_value = mock_prompt
        
        prompt = await manager.get_prompt_for_stage("planning")
        
        assert prompt is not None
        assert prompt == mock_prompt
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_record_prompt_usage(db):
    """Test recording prompt usage"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    prompt_id = uuid4()
    
    # Mock PromptService methods
    with patch.object(manager.prompt_service, 'record_usage') as mock_record:
        with patch.object(manager.prompt_service, 'record_success') as mock_success:
            await manager.record_prompt_usage(
                prompt_id=prompt_id,
                success=True,
                execution_time_ms=100.0,
                stage="planning"
            )
            
            mock_record.assert_called_once()
            mock_success.assert_called_once()
            assert len(manager._usage_tracking) == 1


def test_prompt_usage_creation():
    """Test PromptUsage creation"""
    usage = PromptUsage(
        prompt_id=uuid4(),
        stage="planning",
        start_time=1000.0,
        success=True,
        execution_time_ms=50.0
    )
    
    assert usage.prompt_id is not None
    assert usage.stage == "planning"
    assert usage.success is True
    assert usage.execution_time_ms == 50.0


def test_get_usage_summary(db):
    """Test getting usage summary"""
    context = ExecutionContext.from_db_session(db)
    manager = PromptManager(context)
    
    # Add some usage tracking
    manager._usage_tracking = [
        PromptUsage(uuid4(), "planning", 1000.0, True, 50.0),
        PromptUsage(uuid4(), "execution", 1001.0, True, 100.0),
        PromptUsage(uuid4(), "planning", 1002.0, False, 75.0)
    ]
    
    summary = manager.get_usage_summary()
    
    assert summary["total_usage"] == 3
    assert "planning" in summary["by_stage"]
    assert summary["by_stage"]["planning"]["count"] == 2
    assert summary["by_success"]["success"] == 2
    assert summary["by_success"]["failure"] == 1
