"""
Tests for ExecutionContext
"""
import pytest
from uuid import uuid4

from app.core.execution_context import ExecutionContext


def test_execution_context_creation(db):
    """Test basic ExecutionContext creation"""
    context = ExecutionContext.from_db_session(db)
    
    assert context.db == db
    assert context.workflow_id is not None
    assert len(context.workflow_id) > 0
    assert context.metadata == {}


def test_execution_context_with_workflow_id(db):
    """Test ExecutionContext with custom workflow_id"""
    workflow_id = str(uuid4())
    context = ExecutionContext.from_db_session(db, workflow_id=workflow_id)
    
    assert context.workflow_id == workflow_id


def test_execution_context_metadata(db):
    """Test ExecutionContext metadata management"""
    context = ExecutionContext.from_db_session(db)
    
    # Update metadata
    context.update_metadata(key1="value1", key2=42)
    
    assert context.get_metadata("key1") == "value1"
    assert context.get_metadata("key2") == 42
    assert context.get_metadata("key3", default="default") == "default"
    
    # Check to_dict
    context_dict = context.to_dict()
    assert "workflow_id" in context_dict
    assert "metadata_keys" in context_dict
    assert "key1" in context_dict["metadata_keys"]
    assert "key2" in context_dict["metadata_keys"]


def test_execution_context_prompt_manager(db):
    """Test ExecutionContext prompt_manager property"""
    context = ExecutionContext.from_db_session(db)
    
    # Initially None
    assert context.prompt_manager is None
    
    # Set prompt manager
    mock_prompt_manager = {"test": "manager"}
    context.set_prompt_manager(mock_prompt_manager)
    
    assert context.prompt_manager == mock_prompt_manager


def test_execution_context_repr(db):
    """Test ExecutionContext string representation"""
    context = ExecutionContext.from_db_session(db)
    
    repr_str = repr(context)
    assert "ExecutionContext" in repr_str
    assert context.workflow_id[:8] in repr_str
