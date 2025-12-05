"""
Unit tests for prompt metrics collection
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


class TestPromptMetrics:
    """Test cases for prompt metrics"""
    
    def test_record_usage_increments_count(self, prompt_service: PromptService):
        """Test that record_usage increments usage_count"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_metrics",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        initial_count = prompt.usage_count
        
        # Record usage
        updated = prompt_service.record_usage(prompt.id)
        
        assert updated is not None
        assert updated.usage_count == initial_count + 1
    
    def test_record_usage_with_execution_time(self, prompt_service: PromptService):
        """Test that record_usage updates avg_execution_time"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_time_metrics",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record usage with execution time
        updated = prompt_service.record_usage(
            prompt.id,
            execution_time_ms=1000.0
        )
        
        assert updated is not None
        assert updated.avg_execution_time == 1000.0
    
    def test_record_usage_calculates_moving_average(self, prompt_service: PromptService):
        """Test that record_usage calculates moving average correctly"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_moving_avg",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # First usage
        prompt = prompt_service.record_usage(prompt.id, execution_time_ms=1000.0)
        assert prompt.avg_execution_time == 1000.0
        
        # Second usage - should calculate moving average
        prompt = prompt_service.record_usage(prompt.id, execution_time_ms=2000.0)
        # With alpha=0.1: 0.1 * 2000 + 0.9 * 1000 = 200 + 900 = 1100
        assert prompt.avg_execution_time == pytest.approx(1100.0, rel=0.01)
        
        # Third usage
        prompt = prompt_service.record_usage(prompt.id, execution_time_ms=1500.0)
        # With alpha=0.1: 0.1 * 1500 + 0.9 * 1100 = 150 + 990 = 1140
        assert prompt.avg_execution_time == pytest.approx(1140.0, rel=0.01)
    
    def test_record_usage_without_execution_time(self, prompt_service: PromptService):
        """Test that record_usage works without execution time"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_no_time",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        initial_avg = prompt.avg_execution_time
        
        # Record usage without time
        updated = prompt_service.record_usage(prompt.id)
        
        assert updated is not None
        assert updated.usage_count == 1
        assert updated.avg_execution_time == initial_avg  # Should remain None
    
    def test_record_usage_nonexistent_prompt(self, prompt_service: PromptService):
        """Test that record_usage returns None for nonexistent prompt"""
        fake_id = uuid4()
        result = prompt_service.record_usage(fake_id)
        
        assert result is None
    
    def test_multiple_usage_records(self, prompt_service: PromptService):
        """Test recording multiple usages"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="test_multiple",
            prompt_text="Test prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        # Record multiple usages
        for i in range(5):
            prompt = prompt_service.record_usage(
                prompt.id,
                execution_time_ms=1000.0 + i * 100
            )
        
        assert prompt.usage_count == 5
        assert prompt.avg_execution_time is not None
        # Average should be weighted towards recent values
        assert prompt.avg_execution_time > 1000.0

