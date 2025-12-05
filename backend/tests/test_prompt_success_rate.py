"""
Unit tests for prompt success_rate calculation
"""
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.services.prompt_service import PromptService
from app.models.prompt import Prompt, PromptType, PromptStatus
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


@pytest.fixture
def prompt_service(db: Session):
    """Create PromptService instance"""
    return PromptService(db)


class TestPromptSuccessRate:
    """Test cases for prompt success_rate calculation"""
    
    def test_record_success_updates_rate(self, prompt_service: PromptService):
        """Test that record_success updates success_rate"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_success",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record success
        updated = prompt_service.record_success(prompt.id)
        
        assert updated is not None
        assert updated.success_rate == 1.0  # 1 success / 1 total
    
    def test_record_failure_updates_rate(self, prompt_service: PromptService):
        """Test that record_failure updates success_rate"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_failure",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record failure
        updated = prompt_service.record_failure(prompt.id)
        
        assert updated is not None
        assert updated.success_rate == 0.0  # 0 success / 1 total
    
    def test_success_rate_calculation(self, prompt_service: PromptService):
        """Test success_rate calculation with multiple results"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_rate_calc",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record 3 successes and 2 failures
        prompt = prompt_service.record_success(prompt.id)
        prompt = prompt_service.record_success(prompt.id)
        prompt = prompt_service.record_success(prompt.id)
        prompt = prompt_service.record_failure(prompt.id)
        prompt = prompt_service.record_failure(prompt.id)
        
        # Should be 3/5 = 0.6
        assert prompt.success_rate == pytest.approx(0.6, rel=0.01)
    
    def test_sliding_window(self, prompt_service: PromptService):
        """Test that success_rate uses sliding window (last 100 results)"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_window",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record 50 failures
        for _ in range(50):
            prompt = prompt_service.record_failure(prompt.id)
        
        # Should be 0.0
        assert prompt.success_rate == 0.0
        
        # Record 50 successes
        for _ in range(50):
            prompt = prompt_service.record_success(prompt.id)
        
        # Should be 50/100 = 0.5 (sliding window of 100)
        assert prompt.success_rate == pytest.approx(0.5, rel=0.01)
        
        # Record 10 more successes
        for _ in range(10):
            prompt = prompt_service.record_success(prompt.id)
        
        # Should still be around 0.6 (60/100), not 60/110
        # Because window keeps only last 100
        assert prompt.success_rate == pytest.approx(0.6, rel=0.01)
    
    def test_success_rate_stored_in_history(self, prompt_service: PromptService):
        """Test that results are stored in improvement_history"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_history",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record success
        prompt = prompt_service.record_success(prompt.id)
        
        assert prompt.improvement_history is not None
        assert len(prompt.improvement_history) == 1
        assert prompt.improvement_history[0]["success"] is True
        assert prompt.improvement_history[0]["type"] == "usage_result"
    
    def test_record_result_nonexistent_prompt(self, prompt_service: PromptService):
        """Test that record_success/record_failure return None for nonexistent prompt"""
        fake_id = uuid4()
        
        result = prompt_service.record_success(fake_id)
        assert result is None
        
        result = prompt_service.record_failure(fake_id)
        assert result is None

