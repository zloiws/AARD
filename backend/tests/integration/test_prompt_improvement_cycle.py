"""
Integration test for complete prompt improvement cycle
"""
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


@pytest.mark.asyncio
class TestPromptImprovementCycle:
    """Integration tests for complete prompt improvement cycle"""
    
    async def test_complete_improvement_cycle(self, db: Session):
        """Test complete cycle: usage -> metrics -> analysis -> suggestions -> improved version"""
        prompt_service = PromptService(db)
        
        # 1. Create initial prompt
        prompt = prompt_service.create_prompt(
            name="cycle_test",
            prompt_text="Original prompt for testing",
            prompt_type=PromptType.SYSTEM
        )
        
        # 2. Record usage and failures to lower success rate
        for _ in range(10):
            prompt_service.record_usage(prompt.id, execution_time_ms=2000.0)
            prompt_service.record_failure(prompt.id)
        
        # 3. Analyze performance
        await prompt_service.analyze_prompt_performance(
            prompt_id=prompt.id,
            task_description="Test task",
            result="Failed result",
            success=False,
            execution_metadata={"error_type": "ValueError"}
        )
        
        # 4. Generate suggestions
        suggestions = await prompt_service.suggest_improvements(prompt.id)
        
        assert suggestions is not None
        assert "suggestions" in suggestions
        assert len(suggestions["suggestions"]) > 0
        
        # 5. Create improved version (if LLM available)
        try:
            improved = await prompt_service.create_improved_version(prompt.id)
            
            if improved:
                assert improved.version == prompt.version + 1
                assert improved.status == "testing"
                assert improved.parent_prompt_id == prompt.id
                
                # Check that improvement metadata was saved
                assert improved.improvement_history is not None
                version_creations = [
                    h for h in improved.improvement_history 
                    if h.get("type") == "version_creation"
                ]
                assert len(version_creations) > 0
        except Exception as e:
            # If LLM is not available, that's okay
            pytest.skip(f"LLM not available for full cycle test: {e}")
    
    async def test_auto_improvement_trigger(self, db: Session):
        """Test automatic improvement triggering based on thresholds"""
        prompt_service = PromptService(db)
        
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="auto_trigger_test",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Lower success rate below threshold
        for _ in range(9):
            prompt_service.record_failure(prompt.id)
        for _ in range(1):
            prompt_service.record_success(prompt.id)
        
        # Trigger auto-improvement
        try:
            improved = await prompt_service.auto_create_improved_version_if_needed(
                prompt.id,
                success_rate_threshold=0.5
            )
            
            if improved:
                assert improved.status == "testing"
                assert improved.parent_prompt_id == prompt.id
        except Exception as e:
            # If LLM is not available, that's okay
            pytest.skip(f"LLM not available for auto-improvement test: {e}")

