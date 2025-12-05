"""
Integration tests for plan template extraction
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.models.plan_template import PlanTemplate, TemplateStatus
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.services.plan_template_service import PlanTemplateService
from app.services.execution_service import ExecutionService


@pytest.fixture
def db_session():
    """Create a mock database session"""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def sample_completed_plan():
    """Create a sample completed plan"""
    plan = Mock(spec=Plan)
    plan.id = uuid4()
    plan.task_id = uuid4()
    plan.status = PlanStatus.COMPLETED.value
    plan.goal = "Create a REST API for user management"
    plan.strategy = {
        "approach": "Use FastAPI framework",
        "assumptions": ["PostgreSQL database available"],
        "constraints": ["Must be RESTful"]
    }
    plan.steps = [
        {"step": 1, "description": "Create database models", "type": "code"},
        {"step": 2, "description": "Create API endpoints", "type": "code"},
        {"step": 3, "description": "Add authentication", "type": "code"}
    ]
    plan.alternatives = None
    plan.actual_duration = 3600
    plan.estimated_duration = 3600
    plan.created_at = datetime.utcnow() - timedelta(hours=1)
    plan.current_step = 3
    return plan


@pytest.fixture
def sample_task():
    """Create a sample task"""
    task = Mock(spec=Task)
    task.id = uuid4()
    task.description = "Create a REST API for user management with authentication"
    return task


class TestPlanTemplateExtraction:
    """Test cases for automatic plan template extraction"""
    
    def test_extract_template_on_plan_completion(self, db_session, sample_completed_plan, sample_task):
        """Test that template is extracted when plan completes"""
        # Setup mocks
        plan_query = Mock()
        plan_query.filter.return_value.first.return_value = sample_completed_plan
        task_query = Mock()
        task_query.filter.return_value.first.return_value = sample_task
        template_query = Mock()
        template_query.limit.return_value.all.return_value = []
        
        db_session.query.side_effect = [plan_query, task_query, template_query]
        
        # Create template service
        template_service = PlanTemplateService(db_session)
        template_service.embedding_service = None  # Disable embedding for tests
        
        # Extract template
        template = template_service.extract_template_from_plan(plan_id=sample_completed_plan.id)
        
        # Assertions
        assert template is not None
        assert template.status == TemplateStatus.ACTIVE.value
        assert template.source_plan_ids == [sample_completed_plan.id]
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
    
    def test_extract_template_quality_criteria_min_steps(self, db_session):
        """Test that plans with too few steps are skipped"""
        plan = Mock(spec=Plan)
        plan.id = uuid4()
        plan.task_id = uuid4()
        plan.status = PlanStatus.COMPLETED.value
        plan.goal = "Simple task"
        plan.steps = [{"step": 1, "description": "Single step"}]
        plan.actual_duration = 100
        plan.created_at = datetime.utcnow() - timedelta(seconds=100)
        
        execution_service = ExecutionService(db_session)
        
        # Mock settings
        with patch('app.services.execution_service.get_settings') as mock_settings:
            settings = Mock()
            settings.enable_plan_template_extraction = True
            settings.plan_template_min_steps = 2
            mock_settings.return_value = settings
            
            # Should skip extraction due to insufficient steps
            execution_service._extract_template_from_completed_plan(plan)
            
            # Should not call template service
            db_session.add.assert_not_called()
    
    def test_extract_template_quality_criteria_duration(self, db_session):
        """Test that plans with invalid duration are skipped"""
        plan = Mock(spec=Plan)
        plan.id = uuid4()
        plan.task_id = uuid4()
        plan.status = PlanStatus.COMPLETED.value
        plan.goal = "Quick task"
        plan.steps = [
            {"step": 1, "description": "Step 1"},
            {"step": 2, "description": "Step 2"}
        ]
        plan.actual_duration = 5  # Too fast
        plan.created_at = datetime.utcnow() - timedelta(seconds=5)
        
        execution_service = ExecutionService(db_session)
        
        # Mock settings
        with patch('app.services.execution_service.get_settings') as mock_settings:
            settings = Mock()
            settings.enable_plan_template_extraction = True
            settings.plan_template_min_steps = 2
            settings.plan_template_min_duration = 10
            settings.plan_template_max_duration = 86400
            mock_settings.return_value = settings
            
            # Should skip extraction due to too short duration
            execution_service._extract_template_from_completed_plan(plan)
            
            # Should not call template service
            db_session.add.assert_not_called()
    
    def test_extract_template_skips_if_already_extracted(self, db_session, sample_completed_plan):
        """Test that template extraction is skipped if template already exists"""
        # Create existing template
        existing_template = Mock(spec=PlanTemplate)
        existing_template.source_plan_ids = [sample_completed_plan.id]
        
        plan_query = Mock()
        plan_query.filter.return_value.first.return_value = sample_completed_plan
        template_query = Mock()
        template_query.limit.return_value.all.return_value = [existing_template]
        
        db_session.query.side_effect = [plan_query, template_query]
        
        execution_service = ExecutionService(db_session)
        
        # Mock settings
        with patch('app.services.execution_service.get_settings') as mock_settings:
            settings = Mock()
            settings.enable_plan_template_extraction = True
            settings.plan_template_min_steps = 2
            settings.plan_template_min_duration = 10
            settings.plan_template_max_duration = 86400
            mock_settings.return_value = settings
            
            # Should skip extraction
            execution_service._extract_template_from_completed_plan(sample_completed_plan)
            
            # Should not create new template
            db_session.add.assert_not_called()
    
    def test_extract_template_disabled(self, db_session, sample_completed_plan):
        """Test that extraction is skipped when disabled"""
        execution_service = ExecutionService(db_session)
        
        # Mock settings
        with patch('app.services.execution_service.get_settings') as mock_settings:
            settings = Mock()
            settings.enable_plan_template_extraction = False
            mock_settings.return_value = settings
            
            # Should skip extraction
            execution_service._extract_template_from_completed_plan(sample_completed_plan)
            
            # Should not call template service
            db_session.add.assert_not_called()

