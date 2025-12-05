"""
Integration tests for PlanningService with prompts from database
"""
import pytest
from sqlalchemy.orm import Session

from app.services.planning_service import PlanningService
from app.services.prompt_service import PromptService
from app.models.prompt import PromptType
from app.core.database import SessionLocal, Base, engine


@pytest.fixture
def db():
    """Create test database session"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


class TestPlanningWithPrompts:
    """Integration tests for PlanningService with prompts"""
    
    def test_planning_service_uses_prompts_from_db(self, db: Session):
        """Test that PlanningService loads prompts from database"""
        # Create prompts in database
        prompt_service = PromptService(db)
        
        analysis_prompt = prompt_service.create_prompt(
            name="task_analysis",
            prompt_text="Custom analysis prompt from DB",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        
        decomposition_prompt = prompt_service.create_prompt(
            name="task_decomposition",
            prompt_text="Custom decomposition prompt from DB",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        
        # Create PlanningService
        planning_service = PlanningService(db)
        
        # Test that prompts are loaded
        analysis_loaded = planning_service._get_analysis_prompt()
        decomposition_loaded = planning_service._get_decomposition_prompt()
        
        assert "Custom analysis prompt from DB" in analysis_loaded
        assert "Custom decomposition prompt from DB" in decomposition_loaded
    
    def test_planning_service_fallback_to_default(self, db: Session):
        """Test that PlanningService falls back to default prompts if not in DB"""
        # Create PlanningService without prompts in DB
        planning_service = PlanningService(db)
        
        # Should use fallback prompts
        analysis_loaded = planning_service._get_analysis_prompt()
        decomposition_loaded = planning_service._get_decomposition_prompt()
        
        # Should contain default content
        assert "expert at task analysis" in analysis_loaded.lower()
        assert "breaking down complex tasks" in decomposition_loaded.lower()
    
    def test_prompt_usage_tracking(self, db: Session):
        """Test that prompt usage is tracked in Digital Twin context"""
        from app.models.task import Task, TaskStatus
        from uuid import uuid4
        
        # Create prompts
        prompt_service = PromptService(db)
        
        analysis_prompt = prompt_service.create_prompt(
            name="task_analysis",
            prompt_text="Test analysis prompt",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        
        # Create a task
        task = Task(
            id=uuid4(),
            description="Test task",
            status=TaskStatus.PENDING
        )
        db.add(task)
        db.commit()
        
        # Create PlanningService and use prompt
        planning_service = PlanningService(db)
        planning_service.current_task_id = task.id
        
        # Get prompt (this should save usage to context)
        _ = planning_service._get_analysis_prompt()
        
        # Check that prompt usage was saved
        task = db.query(Task).filter(Task.id == task.id).first()
        context = task.get_context()
        
        assert "prompt_usage" in context
        assert "prompts_used" in context["prompt_usage"]
        assert len(context["prompt_usage"]["prompts_used"]) > 0
        
        # Check that the correct prompt ID was saved
        saved_prompt = context["prompt_usage"]["prompts_used"][0]
        assert saved_prompt["prompt_id"] == str(analysis_prompt.id)
        assert saved_prompt["prompt_name"] == "task_analysis"
        assert saved_prompt["stage"] == "analysis"

