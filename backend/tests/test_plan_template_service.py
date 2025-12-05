"""
Unit tests for PlanTemplateService
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.models.plan_template import PlanTemplate, TemplateStatus
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.services.plan_template_service import PlanTemplateService


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
def template_service(db_session):
    """Create PlanTemplateService instance"""
    with patch('app.services.plan_template_service.EmbeddingService'):
        service = PlanTemplateService(db_session)
        service.embedding_service = None  # Disable embedding for unit tests
        return service


@pytest.fixture
def sample_plan():
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
    return plan


@pytest.fixture
def sample_task():
    """Create a sample task"""
    task = Mock(spec=Task)
    task.id = uuid4()
    task.description = "Create a REST API for user management with authentication"
    return task


class TestPlanTemplateService:
    """Test cases for PlanTemplateService"""
    
    def test_extract_template_from_plan_success(self, template_service, db_session, sample_plan, sample_task):
        """Test successful template extraction"""
        # Setup mocks
        db_session.query.return_value.filter.return_value.first.side_effect = [sample_plan, sample_task]
        db_session.query.return_value.filter.return_value.first.return_value = sample_plan
        
        # Mock query chain
        plan_query = Mock()
        plan_query.filter.return_value.first.return_value = sample_plan
        task_query = Mock()
        task_query.filter.return_value.first.return_value = sample_task
        db_session.query.side_effect = [plan_query, task_query]
        
        # Extract template
        template = template_service.extract_template_from_plan(
            plan_id=sample_plan.id,
            template_name="Test Template"
        )
        
        # Assertions
        assert template is not None
        assert template.name == "Test Template"
        assert template.goal_pattern is not None
        assert template.steps_template is not None
        assert template.status == TemplateStatus.ACTIVE.value
        assert template.source_plan_ids == [sample_plan.id]
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
    
    def test_extract_template_from_non_completed_plan(self, template_service, db_session, sample_plan):
        """Test that non-completed plans are skipped"""
        sample_plan.status = PlanStatus.DRAFT.value
        
        plan_query = Mock()
        plan_query.filter.return_value.first.return_value = sample_plan
        db_session.query.return_value = plan_query
        
        template = template_service.extract_template_from_plan(plan_id=sample_plan.id)
        
        assert template is None
        db_session.add.assert_not_called()
    
    def test_extract_template_plan_not_found(self, template_service, db_session):
        """Test handling when plan is not found"""
        plan_query = Mock()
        plan_query.filter.return_value.first.return_value = None
        db_session.query.return_value = plan_query
        
        template = template_service.extract_template_from_plan(plan_id=uuid4())
        
        assert template is None
        db_session.add.assert_not_called()
    
    def test_abstract_text(self, template_service):
        """Test text abstraction"""
        text = "Create API at https://example.com/api/users"
        abstracted = template_service._abstract_text(text)
        
        assert "{url}" in abstracted
        assert "https://example.com" not in abstracted
    
    def test_infer_category(self, template_service):
        """Test category inference"""
        category = template_service._infer_category(
            "Create a REST API endpoint",
            "Build API for user management"
        )
        
        assert category == "api_development"
    
    def test_infer_tags(self, template_service):
        """Test tag inference"""
        tags = template_service._infer_tags(
            "Create Python API with PostgreSQL database",
            "Build REST API"
        )
        
        assert "python" in tags
        assert "api" in tags
        assert "database" in tags
    
    def test_find_matching_templates_text_search(self, template_service, db_session):
        """Test finding templates using text search"""
        # Create mock templates
        template1 = Mock(spec=PlanTemplate)
        template1.id = uuid4()
        template1.name = "API Development Template"
        template1.description = "Template for REST API development"
        template1.goal_pattern = "Create REST API"
        template1.category = "api_development"
        template1.status = TemplateStatus.ACTIVE.value
        template1.success_rate = 0.9
        template1.usage_count = 10
        
        template2 = Mock(spec=PlanTemplate)
        template2.id = uuid4()
        template2.name = "Database Template"
        template2.description = "Template for database operations"
        template2.goal_pattern = "Create database"
        template2.category = "data_processing"
        template2.status = TemplateStatus.ACTIVE.value
        template2.success_rate = 0.8
        template2.usage_count = 5
        
        # Mock query chain
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value.limit.return_value.all.return_value = [template1, template2]
        db_session.query.return_value = query_mock
        
        templates = template_service.find_matching_templates(
            task_description="Create REST API",
            use_vector_search=False
        )
        
        assert len(templates) == 2
        # Should be ranked by score (template1 should be first due to better match)
        assert templates[0].name == "API Development Template"
    
    def test_find_matching_templates_with_category_filter(self, template_service, db_session):
        """Test finding templates with category filter"""
        template1 = Mock(spec=PlanTemplate)
        template1.id = uuid4()
        template1.name = "API Template"
        template1.category = "api_development"
        template1.status = TemplateStatus.ACTIVE.value
        template1.success_rate = 0.9
        template1.usage_count = 10
        template1.description = None
        template1.goal_pattern = ""
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value.limit.return_value.all.return_value = [template1]
        db_session.query.return_value = query_mock
        
        templates = template_service.find_matching_templates(
            task_description="Create API",
            category="api_development",
            use_vector_search=False
        )
        
        assert len(templates) == 1
        assert templates[0].category == "api_development"
    
    def test_rank_templates(self, template_service):
        """Test template ranking by combined score"""
        template1 = Mock(spec=PlanTemplate)
        template1.success_rate = 0.8
        template1.usage_count = 5
        template1.name = "Template 1"
        template1.description = "API development"
        template1.goal_pattern = "Create API"
        template1.category = "api_development"
        
        template2 = Mock(spec=PlanTemplate)
        template2.success_rate = 0.9
        template2.usage_count = 20
        template2.name = "Template 2"
        template2.description = "API development"
        template2.goal_pattern = "Create REST API"
        template2.category = "api_development"
        
        templates = [template1, template2]
        ranked = template_service._rank_templates(templates, "Create REST API")
        
        # Template2 should be ranked higher due to better success rate and usage
        assert len(ranked) == 2
        assert ranked[0].success_rate >= ranked[1].success_rate
    
    def test_get_template(self, template_service, db_session):
        """Test getting template by ID"""
        template_id = uuid4()
        template = Mock(spec=PlanTemplate)
        template.id = template_id
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = template
        db_session.query.return_value = query_mock
        
        result = template_service.get_template(template_id)
        
        assert result == template
    
    def test_list_templates(self, template_service, db_session):
        """Test listing templates"""
        template1 = Mock(spec=PlanTemplate)
        template2 = Mock(spec=PlanTemplate)
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value.limit.return_value.all.return_value = [template1, template2]
        db_session.query.return_value = query_mock
        
        templates = template_service.list_templates(category="api_development")
        
        assert len(templates) == 2
    
    def test_update_template_usage(self, template_service, db_session):
        """Test updating template usage statistics"""
        template_id = uuid4()
        template = Mock(spec=PlanTemplate)
        template.id = template_id
        template.usage_count = 5
        template.last_used_at = None
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = template
        db_session.query.return_value = query_mock
        
        template_service.update_template_usage(template_id)
        
        assert template.usage_count == 6
        assert template.last_used_at is not None
        db_session.commit.assert_called_once()

