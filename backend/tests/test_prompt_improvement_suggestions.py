"""
Unit tests for prompt improvement suggestions
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


class TestPromptImprovementSuggestions:
    """Test cases for prompt improvement suggestions"""
    
    @pytest.mark.asyncio
    async def test_suggest_improvements_low_success_rate(self, prompt_service: PromptService):
        """Test suggestions for prompt with low success rate"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_low_success",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record multiple failures to lower success rate
        for _ in range(7):
            prompt_service.record_failure(prompt.id)
        for _ in range(3):
            prompt_service.record_success(prompt.id)
        
        # Generate suggestions
        suggestions = await prompt_service.suggest_improvements(prompt.id)
        
        assert suggestions is not None
        assert "suggestions" in suggestions
        assert "priority" in suggestions
        assert suggestions["priority"] in ["high", "medium", "low"]
        assert len(suggestions["suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_suggest_improvements_high_execution_time(self, prompt_service: PromptService):
        """Test suggestions for prompt with high execution time"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_slow",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record usage with high execution time
        for _ in range(5):
            prompt_service.record_usage(prompt.id, execution_time_ms=12000.0)
        
        # Generate suggestions
        suggestions = await prompt_service.suggest_improvements(prompt.id)
        
        assert suggestions is not None
        assert "suggestions" in suggestions
        # Should have suggestions about execution time
        suggestion_texts = [s.get("message", s) if isinstance(s, dict) else s for s in suggestions["suggestions"]]
        assert any("execution time" in str(s).lower() or "slow" in str(s).lower() for s in suggestion_texts)
    
    @pytest.mark.asyncio
    async def test_suggest_improvements_nonexistent(self, prompt_service: PromptService):
        """Test suggestions for nonexistent prompt"""
        fake_id = uuid4()
        
        suggestions = await prompt_service.suggest_improvements(fake_id)
        
        assert suggestions is None
    
    @pytest.mark.asyncio
    async def test_suggestions_saved_to_history(self, prompt_service: PromptService):
        """Test that suggestions are saved to improvement_history"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_history_save",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Generate suggestions
        suggestions = await prompt_service.suggest_improvements(prompt.id)
        
        assert suggestions is not None
        
        # Check that suggestions were saved
        prompt = prompt_service.get_prompt(prompt.id)
        history = prompt.improvement_history or []
        
        suggestion_entries = [h for h in history if h.get("type") == "improvement_suggestions"]
        assert len(suggestion_entries) > 0
        assert suggestion_entries[-1]["suggestions"] == suggestions
    
    def test_analyze_metrics(self, prompt_service: PromptService):
        """Test _analyze_metrics method"""
        # Create prompt with low success rate
        prompt = prompt_service.create_prompt(
            name="test_metrics",
            prompt_text="Test",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record failures
        for _ in range(8):
            prompt_service.record_failure(prompt.id)
        for _ in range(2):
            prompt_service.record_success(prompt.id)
        
        # Refresh prompt
        prompt = prompt_service.get_prompt(prompt.id)
        
        # Analyze metrics
        analysis = prompt_service._analyze_metrics(prompt)
        
        assert "issues" in analysis
        assert "success_rate" in analysis
        assert analysis["success_rate"] < 0.5  # Should be 0.2 (2/10)
        assert len(analysis["issues"]) > 0
    
    def test_analyze_improvement_history(self, prompt_service: PromptService):
        """Test _analyze_improvement_history method"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_history_analysis",
            prompt_text="Test",
            prompt_type=PromptType.SYSTEM
        )
        
        # Add some performance analyses
        import asyncio
        async def add_analyses():
            for i in range(5):
                await prompt_service.analyze_prompt_performance(
                    prompt_id=prompt.id,
                    task_description=f"Task {i}",
                    result={"result": i},
                    success=(i % 2 == 0),  # Alternating success/failure
                    execution_metadata={"error_type": "ValueError"} if i % 2 != 0 else None
                )

        # Run async function
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(add_analyses())
        
        # Refresh prompt
        prompt = prompt_service.get_prompt(prompt.id)
        
        # Analyze history
        analysis = prompt_service._analyze_improvement_history(prompt)
        
        assert "patterns" in analysis
        assert "total_analyses" in analysis
        assert analysis["total_analyses"] == 5

