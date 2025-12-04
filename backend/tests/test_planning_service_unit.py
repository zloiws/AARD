"""
Unit tests for PlanningService
Tests individual methods without requiring database or external services
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime

from app.services.planning_service import PlanningService


class TestPlanningServiceUnit:
    """Unit tests for PlanningService methods"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def planning_service(self, mock_db):
        """PlanningService instance with mocked database"""
        return PlanningService(mock_db)
    
    def test_estimate_duration_empty_steps(self, planning_service):
        """Test duration estimation with empty steps"""
        duration = planning_service._estimate_duration([])
        assert duration == 0
    
    def test_estimate_duration_with_default_timeout(self, planning_service):
        """Test duration estimation with default timeout"""
        steps = [
            {"step_id": "step_1", "description": "Step 1"},
            {"step_id": "step_2", "description": "Step 2"}
        ]
        # Default timeout is 300 seconds
        duration = planning_service._estimate_duration(steps)
        assert duration == 600  # 2 steps * 300 seconds
    
    def test_estimate_duration_with_custom_timeout(self, planning_service):
        """Test duration estimation with custom timeout"""
        steps = [
            {"step_id": "step_1", "description": "Step 1", "timeout": 100},
            {"step_id": "step_2", "description": "Step 2", "timeout": 200},
            {"step_id": "step_3", "description": "Step 3", "timeout": 150}
        ]
        duration = planning_service._estimate_duration(steps)
        assert duration == 450  # 100 + 200 + 150
    
    def test_parse_and_validate_json_valid(self, planning_service):
        """Test parsing valid JSON"""
        json_str = '{"key": "value", "number": 123}'
        result = planning_service._parse_and_validate_json(json_str)
        assert result == {"key": "value", "number": 123}
    
    def test_parse_and_validate_json_with_code_block(self, planning_service):
        """Test parsing JSON wrapped in code block"""
        json_str = '''```json
{"key": "value"}
```'''
        result = planning_service._parse_and_validate_json(json_str)
        assert result == {"key": "value"}
    
    def test_parse_and_validate_json_with_markdown(self, planning_service):
        """Test parsing JSON with markdown formatting"""
        json_str = '''Here is the JSON:
```json
{"status": "ok"}
```'''
        result = planning_service._parse_and_validate_json(json_str)
        assert result == {"status": "ok"}
    
    def test_parse_and_validate_json_array(self, planning_service):
        """Test parsing JSON array"""
        json_str = '[{"step_id": "step_1"}, {"step_id": "step_2"}]'
        result = planning_service._parse_and_validate_json(json_str)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["step_id"] == "step_1"
    
    def test_parse_and_validate_json_invalid(self, planning_service):
        """Test parsing invalid JSON raises error"""
        invalid_json = '{"key": value}'  # Missing quotes
        with pytest.raises(ValueError) as exc_info:
            planning_service._parse_and_validate_json(invalid_json)
        assert "Invalid JSON" in str(exc_info.value) or "JSON" in str(exc_info.value)
    
    def test_parse_json_from_response(self, planning_service):
        """Test legacy parse_json_from_response method"""
        json_str = '{"test": "value"}'
        result = planning_service._parse_json_from_response(json_str)
        assert result == {"test": "value"}
    
    @pytest.mark.asyncio
    async def test_get_plan_found(self, planning_service, mock_db):
        """Test getting plan by ID when plan exists"""
        plan_id = uuid4()
        mock_plan = Mock()
        mock_plan.id = plan_id
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_plan
        mock_db.query.return_value = mock_query
        
        result = planning_service.get_plan(plan_id)
        assert result == mock_plan
        mock_db.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_plan_not_found(self, planning_service, mock_db):
        """Test getting plan by ID when plan doesn't exist"""
        plan_id = uuid4()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = planning_service.get_plan(plan_id)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_plans_for_task(self, planning_service, mock_db):
        """Test getting all plans for a task"""
        task_id = uuid4()
        mock_plan1 = Mock()
        mock_plan1.version = 2
        mock_plan2 = Mock()
        mock_plan2.version = 1
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_plan1, mock_plan2]
        mock_db.query.return_value = mock_query
        
        result = planning_service.get_plans_for_task(task_id)
        assert len(result) == 2
        assert result[0] == mock_plan1
        assert result[1] == mock_plan2
    
    @pytest.mark.asyncio
    async def test_approve_plan_success(self, planning_service, mock_db):
        """Test approving a plan"""
        plan_id = uuid4()
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.status = "draft"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_plan
        mock_db.query.return_value = mock_query
        
        result = planning_service.approve_plan(plan_id)
        
        assert result == mock_plan
        assert mock_plan.status == "approved"
        assert mock_plan.approved_at is not None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_plan)
    
    @pytest.mark.asyncio
    async def test_approve_plan_not_found(self, planning_service, mock_db):
        """Test approving a plan that doesn't exist"""
        plan_id = uuid4()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(ValueError) as exc_info:
            planning_service.approve_plan(plan_id)
        assert str(plan_id) in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_start_execution_success(self, planning_service, mock_db):
        """Test starting plan execution"""
        plan_id = uuid4()
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.status = "approved"
        mock_plan.current_step = 0
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_plan
        mock_db.query.return_value = mock_query
        
        result = planning_service.start_execution(plan_id)
        
        assert result == mock_plan
        assert mock_plan.status == "executing"
        assert mock_plan.current_step == 0
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_plan)
    
    @pytest.mark.asyncio
    async def test_start_execution_not_approved(self, planning_service, mock_db):
        """Test starting execution of non-approved plan"""
        plan_id = uuid4()
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.status = "draft"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_plan
        mock_db.query.return_value = mock_query
        
        with pytest.raises(ValueError) as exc_info:
            planning_service.start_execution(plan_id)
        assert "approved" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_start_execution_not_found(self, planning_service, mock_db):
        """Test starting execution of non-existent plan"""
        plan_id = uuid4()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(ValueError) as exc_info:
            planning_service.start_execution(plan_id)
        assert str(plan_id) in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

