"""
Unit tests for prompt reflection and analysis
"""
from uuid import uuid4

import pytest
from app.core.database import Base, SessionLocal, engine
from app.models.prompt import Prompt, PromptStatus, PromptType
from app.services.prompt_service import PromptService
from sqlalchemy.orm import Session


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


@pytest.fixture
def prompt_service(db: Session):
    """Create PromptService instance"""
    return PromptService(db)


@pytest.mark.asyncio
class TestPromptReflection:
    """Test cases for prompt reflection"""
    
    async def test_analyze_prompt_performance_success(self, prompt_service: PromptService):
        """Test analyzing successful prompt performance"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_reflection",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Analyze successful performance
        result = {
            "strategy": {"approach": "test approach"},
            "steps": ["step1", "step2"]
        }
        
        analysis = await prompt_service.analyze_prompt_performance(
            prompt_id=prompt.id,
            task_description="Test task",
            result=result,
            success=True,
            execution_metadata={"duration_ms": 1000}
        )
        
        assert analysis is not None
        assert analysis["type"] == "success_analysis"
        assert "improvements" in analysis
        
        # Check that analysis was saved to history
        prompt = prompt_service.get_prompt(prompt.id)
        assert prompt.improvement_history is not None
        assert len(prompt.improvement_history) > 0
        
        # Find the analysis entry
        analyses = [h for h in prompt.improvement_history if h.get("type") == "performance_analysis"]
        assert len(analyses) > 0
        assert analyses[-1]["success"] is True
    
    async def test_analyze_prompt_performance_failure(self, prompt_service: PromptService):
        """Test analyzing failed prompt performance"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_reflection_fail",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Analyze failed performance
        error = "Test error message"
        
        analysis = await prompt_service.analyze_prompt_performance(
            prompt_id=prompt.id,
            task_description="Test task",
            result=error,
            success=False,
            execution_metadata={"error_type": "ValueError"}
        )
        
        assert analysis is not None
        assert analysis["type"] == "failure_analysis"
        assert "analysis" in analysis or "suggested_fix" in analysis
        
        # Check that analysis was saved to history
        prompt = prompt_service.get_prompt(prompt.id)
        assert prompt.improvement_history is not None
        
        # Find the analysis entry
        analyses = [h for h in prompt.improvement_history if h.get("type") == "performance_analysis"]
        assert len(analyses) > 0
        assert analyses[-1]["success"] is False
    
    async def test_analyze_prompt_performance_nonexistent(self, prompt_service: PromptService):
        """Test analyzing nonexistent prompt"""
        fake_id = uuid4()
        
        analysis = await prompt_service.analyze_prompt_performance(
            prompt_id=fake_id,
            task_description="Test",
            result="result",
            success=True
        )
        
        assert analysis is None
    
    async def test_analysis_history_limit(self, prompt_service: PromptService):
        """Test that analysis history is limited to 50 entries"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_history_limit",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Create 60 analyses
        for i in range(60):
            await prompt_service.analyze_prompt_performance(
                prompt_id=prompt.id,
                task_description=f"Task {i}",
                result={"result": i},
                success=True
            )
        
        # Check that only 50 analyses are kept
        prompt = prompt_service.get_prompt(prompt.id)
        analyses = [h for h in prompt.improvement_history if h.get("type") == "performance_analysis"]
        assert len(analyses) == 50

