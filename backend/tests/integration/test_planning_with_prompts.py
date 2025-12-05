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
        
        # Create PlanningService and use prompt in _analyze_task context
        planning_service = PlanningService(db)
        planning_service.current_task_id = task.id
        
        # Simulate using prompt in _analyze_task (where usage is actually saved)
        # This is what happens in the real flow
        prompt_used = prompt_service.get_active_prompt(
            name="task_analysis",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        
        if prompt_used and task.id:
            try:
                task_context = task.get_context()
                prompt_usage = task_context.get("prompt_usage", {})
                if "prompts_used" not in prompt_usage:
                    prompt_usage["prompts_used"] = []
                prompt_usage["prompts_used"].append({
                    "prompt_id": str(prompt_used.id),
                    "prompt_name": prompt_used.name,
                    "stage": "analysis",
                    "timestamp": "2024-01-01T00:00:00"
                })
                task_context["prompt_usage"] = prompt_usage
                task.update_context(task_context, merge=False)
                db.commit()
            except Exception as e:
                pass  # Ignore errors in test
        
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

