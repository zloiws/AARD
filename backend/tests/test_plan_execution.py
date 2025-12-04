"""
Unit tests for plan execution functionality
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.execution_service import ExecutionService, StepExecutor
from app.models.plan import Plan
from app.models.task import Task, TaskStatus


class TestStepExecutor:
    """Tests for StepExecutor class"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def step_executor(self, mock_db):
        """StepExecutor instance"""
        return StepExecutor(mock_db)
    
    @pytest.fixture
    def sample_step(self):
        """Sample step definition"""
        return {
            "step_id": "step_1",
            "type": "action",
            "description": "Create a new file",
            "inputs": {"filename": "test.txt"}
        }
    
    @pytest.fixture
    def sample_plan(self):
        """Sample plan"""
        plan = Mock(spec=Plan)
        plan.id = uuid4()
        plan.task_id = uuid4()
        plan.status = "approved"
        plan.steps = []
        return plan
    
    @pytest.mark.asyncio
    async def test_execute_step_success(self, step_executor, sample_step, sample_plan):
        """Test successful step execution"""
        with patch.object(step_executor, '_execute_action_step', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "step_id": "step_1",
                "status": "completed",
                "output": "File created successfully",
                "started_at": datetime.utcnow(),
                "completed_at": datetime.utcnow(),
                "duration": 1.5
            }
            
            result = await step_executor.execute_step(
                step=sample_step,
                plan=sample_plan,
                context={}
            )
            
            assert result["status"] == "completed"
            assert result["step_id"] == "step_1"
            assert "output" in result
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_step_failure(self, step_executor, sample_step, sample_plan):
        """Test step execution failure"""
        with patch.object(step_executor, '_execute_action_step', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Execution failed")
            
            result = await step_executor.execute_step(
                step=sample_step,
                plan=sample_plan,
                context={}
            )
            
            assert result["status"] == "failed"
            assert "error" in result
            assert "Execution failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_step_approval_required(self, step_executor, sample_step, sample_plan):
        """Test step requiring approval"""
        sample_step["approval_required"] = True
        
        with patch('app.services.approval_service.ApprovalService') as mock_approval_class:
            mock_approval = Mock()
            mock_approval.id = uuid4()
            mock_approval_instance = Mock()
            mock_approval_instance.create_approval_request.return_value = mock_approval
            mock_approval_class.return_value = mock_approval_instance
            
            result = await step_executor.execute_step(
                step=sample_step,
                plan=sample_plan,
                context={}
            )
            
            assert result["status"] == "waiting_approval"
            assert "approval_id" in result
    
    @pytest.mark.asyncio
    async def test_execute_step_unknown_type(self, step_executor, sample_plan):
        """Test step with unknown type"""
        step = {
            "step_id": "step_1",
            "type": "unknown_type",
            "description": "Unknown step"
        }
        
        result = await step_executor.execute_step(
            step=step,
            plan=sample_plan,
            context={}
        )
        
        assert result["status"] == "skipped"
        assert "Unknown step type" in result["message"]


class TestExecutionService:
    """Tests for ExecutionService class"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = Mock()
        return db
    
    @pytest.fixture
    def execution_service(self, mock_db):
        """ExecutionService instance"""
        return ExecutionService(mock_db)
    
    @pytest.fixture
    def sample_plan(self):
        """Sample approved plan"""
        plan = Mock(spec=Plan)
        plan.id = uuid4()
        plan.task_id = uuid4()
        plan.status = "approved"
        plan.version = 1
        plan.current_step = 0
        plan.created_at = datetime.utcnow()
        plan.estimated_duration = 300
        plan.actual_duration = None
        
        steps = [
            {
                "step_id": "step_1",
                "type": "action",
                "description": "First step"
            },
            {
                "step_id": "step_2",
                "type": "action",
                "description": "Second step",
                "dependencies": ["step_1"]
            }
        ]
        plan.steps = json.dumps(steps)
        return plan
    
    @pytest.mark.asyncio
    async def test_execute_plan_not_found(self, execution_service):
        """Test execution of non-existent plan"""
        with patch('app.services.planning_service.PlanningService') as mock_planning_class:
            mock_planning_instance = Mock()
            mock_planning_instance.get_plan.return_value = None
            mock_planning_class.return_value = mock_planning_instance
            
            with pytest.raises(ValueError, match="not found"):
                await execution_service.execute_plan(uuid4())
    
    @pytest.mark.asyncio
    async def test_execute_plan_not_approved(self, execution_service, sample_plan):
        """Test execution of non-approved plan"""
        sample_plan.status = "draft"
        
        with patch('app.services.planning_service.PlanningService') as mock_planning_class:
            mock_planning_instance = Mock()
            mock_planning_instance.get_plan.return_value = sample_plan
            mock_planning_class.return_value = mock_planning_instance
            
            with pytest.raises(ValueError, match="must be approved"):
                await execution_service.execute_plan(sample_plan.id)
    
    @pytest.mark.asyncio
    async def test_execute_plan_no_steps(self, execution_service, sample_plan):
        """Test execution of plan with no steps"""
        sample_plan.steps = []
        
        with patch('app.services.planning_service.PlanningService') as mock_planning_class:
            mock_planning_instance = Mock()
            mock_planning_instance.get_plan.return_value = sample_plan
            mock_planning_class.return_value = mock_planning_instance
            
            result = await execution_service.execute_plan(sample_plan.id)
            
            assert result.status == "failed"
    
    @pytest.mark.asyncio
    async def test_execute_plan_success(self, execution_service, sample_plan, mock_db):
        """Test successful plan execution"""
        with patch('app.services.planning_service.PlanningService') as mock_planning_class:
            mock_planning_instance = Mock()
            mock_planning_instance.get_plan.return_value = sample_plan
            mock_planning_class.return_value = mock_planning_instance
            
            with patch.object(execution_service.step_executor, 'execute_step', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = {
                    "step_id": "step_1",
                    "status": "completed",
                    "output": "Step completed",
                    "started_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow()
                }
                
                with patch.object(execution_service.checkpoint_service, 'create_plan_checkpoint') as mock_checkpoint:
                    mock_checkpoint.return_value = Mock(id=uuid4())
                    
                    result = await execution_service.execute_plan(sample_plan.id)
                    
                    assert result.status in ["executing", "completed"]
                    assert mock_execute.called
    
    @pytest.mark.asyncio
    async def test_execute_plan_dependency_error(self, execution_service, sample_plan):
        """Test plan execution with dependency error"""
        steps = [
            {
                "step_id": "step_2",
                "type": "action",
                "description": "Second step",
                "dependencies": ["step_1"]  # step_1 not in context
            }
        ]
        sample_plan.steps = json.dumps(steps)
        
        with patch('app.services.planning_service.PlanningService') as mock_planning_class:
            mock_planning_instance = Mock()
            mock_planning_instance.get_plan.return_value = sample_plan
            mock_planning_class.return_value = mock_planning_instance
            
            with patch.object(execution_service.checkpoint_service, 'create_plan_checkpoint') as mock_checkpoint:
                mock_checkpoint.return_value = Mock(id=uuid4())
                
                result = await execution_service.execute_plan(sample_plan.id)
                
                assert result.status == "failed"
    
    @pytest.mark.asyncio
    async def test_execute_plan_step_failure(self, execution_service, sample_plan):
        """Test plan execution when step fails"""
        with patch('app.services.planning_service.PlanningService') as mock_planning_class:
            mock_planning_instance = Mock()
            mock_planning_instance.get_plan.return_value = sample_plan
            mock_planning_class.return_value = mock_planning_instance
            
            with patch.object(execution_service.step_executor, 'execute_step', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = {
                    "step_id": "step_1",
                    "status": "failed",
                    "error": "Step execution failed",
                    "started_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow()
                }
                
                with patch.object(execution_service.checkpoint_service, 'create_plan_checkpoint') as mock_checkpoint:
                    mock_checkpoint.return_value = Mock(id=uuid4())
                    
                    with patch.object(execution_service.checkpoint_service, 'get_latest_checkpoint', return_value=None):
                        result = await execution_service.execute_plan(sample_plan.id)
                        
                        assert result.status == "failed"
    
    def test_get_execution_status(self, execution_service, sample_plan):
        """Test getting execution status"""
        with patch('app.services.planning_service.PlanningService') as mock_planning_class:
            mock_planning_instance = Mock()
            mock_planning_instance.get_plan.return_value = sample_plan
            mock_planning_class.return_value = mock_planning_instance
            sample_plan.current_step = 1
            
            status = execution_service.get_execution_status(sample_plan.id)
            
            assert status["plan_id"] == str(sample_plan.id)
            assert status["status"] == sample_plan.status
            assert status["current_step"] == 1
            assert "total_steps" in status
            assert "progress" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

