"""
Unit tests for PromptService
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


class TestPromptService:
    """Test cases for PromptService"""
    
    def test_create_prompt(self, prompt_service: PromptService):
        """Test creating a new prompt"""
        prompt = prompt_service.create_prompt(
            name="test_prompt",
            prompt_text="Test prompt text",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        
        assert prompt is not None
        assert prompt.name == "test_prompt"
        assert prompt.prompt_text == "Test prompt text"
        assert prompt.prompt_type == "system"
        assert prompt.level == 0
        assert prompt.version == 1
        assert prompt.status == "active"
    
    def test_get_prompt(self, prompt_service: PromptService):
        """Test getting prompt by ID"""
        # Create a prompt
        created = prompt_service.create_prompt(
            name="test_get",
            prompt_text="Test",
            prompt_type=PromptType.SYSTEM
        )
        
        # Get it back
        retrieved = prompt_service.get_prompt(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "test_get"
    
    def test_get_prompt_not_found(self, prompt_service: PromptService):
        """Test getting non-existent prompt"""
        fake_id = uuid4()
        result = prompt_service.get_prompt(fake_id)
        
        assert result is None
    
    def test_get_active_prompt(self, prompt_service: PromptService):
        """Test getting active prompt by name and type"""
        # Create active prompt
        prompt_service.create_prompt(
            name="analysis_prompt",
            prompt_text="Analysis prompt",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        
        # Get active prompt
        active = prompt_service.get_active_prompt(
            name="analysis_prompt",
            prompt_type=PromptType.SYSTEM
        )
        
        assert active is not None
        assert active.name == "analysis_prompt"
        assert active.status == "active"
    
    def test_get_active_prompt_with_level(self, prompt_service: PromptService):
        """Test getting active prompt with level filter"""
        # Create prompts with different levels
        prompt_service.create_prompt(
            name="level_test",
            prompt_text="Level 0",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        prompt_service.create_prompt(
            name="level_test",
            prompt_text="Level 1",
            prompt_type=PromptType.SYSTEM,
            level=1
        )
        
        # Get level 1
        result = prompt_service.get_active_prompt(
            name="level_test",
            prompt_type=PromptType.SYSTEM,
            level=1
        )
        
        assert result is not None
        assert result.level == 1
    
    def test_list_prompts(self, prompt_service: PromptService):
        """Test listing prompts with filters"""
        # Create multiple prompts
        prompt_service.create_prompt(
            name="system_prompt_1",
            prompt_text="System 1",
            prompt_type=PromptType.SYSTEM
        )
        prompt_service.create_prompt(
            name="agent_prompt_1",
            prompt_text="Agent 1",
            prompt_type=PromptType.AGENT
        )
        prompt_service.create_prompt(
            name="system_prompt_2",
            prompt_text="System 2",
            prompt_type=PromptType.SYSTEM
        )
        
        # List all
        all_prompts = prompt_service.list_prompts()
        assert len(all_prompts) >= 3
        
        # Filter by type
        system_prompts = prompt_service.list_prompts(prompt_type=PromptType.SYSTEM)
        assert len(system_prompts) >= 2
        assert all(p.prompt_type == "system" for p in system_prompts)
        
        # Search by name
        searched = prompt_service.list_prompts(name_search="system")
        assert len(searched) >= 2
    
    def test_update_prompt(self, prompt_service: PromptService):
        """Test updating a prompt (in-place update, version doesn't change)"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="update_test",
            prompt_text="Original",
            prompt_type=PromptType.SYSTEM
        )
        original_version = prompt.version
        
        # Update (in-place, version stays the same)
        updated = prompt_service.update_prompt(
            prompt.id,
            prompt_text="Updated text"
        )
        
        assert updated is not None
        assert updated.prompt_text == "Updated text"
        assert updated.version == original_version  # Version doesn't change on update
    
    def test_create_version(self, prompt_service: PromptService):
        """Test creating a new version of a prompt"""
        # Create parent prompt
        parent = prompt_service.create_prompt(
            name="versioned_prompt",
            prompt_text="Version 1",
            prompt_type=PromptType.SYSTEM
        )
        
        # Create version
        version = prompt_service.create_version(
            parent.id,
            "Version 2 text"
        )
        
        assert version is not None
        assert version.name == parent.name
        assert version.version == 2
        assert version.parent_prompt_id == parent.id
        assert version.prompt_text == "Version 2 text"
    
    def test_get_prompt_versions(self, prompt_service: PromptService):
        """Test getting all versions of a prompt"""
        # Create parent
        parent = prompt_service.create_prompt(
            name="multi_version",
            prompt_text="V1",
            prompt_type=PromptType.SYSTEM
        )
        
        # Create versions
        v2 = prompt_service.create_version(parent.id, "V2")
        v3 = prompt_service.create_version(parent.id, "V3")
        
        # Get all versions
        versions = prompt_service.get_prompt_versions(parent.id)
        
        assert len(versions) == 3
        assert versions[0].version == 1
        assert versions[1].version == 2
        assert versions[2].version == 3
    
    def test_deprecate_prompt(self, prompt_service: PromptService):
        """Test deprecating a prompt"""
        # Create prompt
        prompt = prompt_service.create_prompt(
            name="deprecate_test",
            prompt_text="Test",
            prompt_type=PromptType.SYSTEM
        )
        
        # Deprecate
        deprecated = prompt_service.deprecate_prompt(prompt.id)
        
        assert deprecated is not None
        assert deprecated.status == "deprecated"
        
        # Should not be returned by get_active_prompt
        active = prompt_service.get_active_prompt(name="deprecate_test")
        assert active is None
    
    def test_get_latest_version(self, prompt_service: PromptService):
        """Test getting latest version by name"""
        # Create parent
        parent = prompt_service.create_prompt(
            name="latest_test",
            prompt_text="V1",
            prompt_type=PromptType.SYSTEM
        )
        
        # Create versions
        prompt_service.create_version(parent.id, "V2")
        prompt_service.create_version(parent.id, "V3")
        
        # Get latest
        latest = prompt_service.get_latest_version("latest_test")
        
        assert latest is not None
        assert latest.version == 3
        assert latest.prompt_text == "V3"

