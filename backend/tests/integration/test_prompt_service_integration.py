"""
Integration tests for PromptService with database
"""
import pytest
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


class TestPromptServiceIntegration:
    """Integration tests for PromptService"""
    
    def test_full_lifecycle(self, db: Session):
        """Test complete lifecycle: create, update, version, deprecate"""
        service = PromptService(db)
        
        # Create initial prompt
        prompt = service.create_prompt(
            name="lifecycle_test",
            prompt_text="Initial version",
            prompt_type=PromptType.SYSTEM,
            level=0,
            created_by="test_user"
        )
        
        assert prompt.version == 1
        assert prompt.status == "active"
        
        # Update prompt
        updated = service.update_prompt(
            prompt.id,
            prompt_text="Updated version"
        )
        assert updated.version == 2
        
        # Create new version
        v3 = service.create_version(
            prompt.id,
            "Version 3 text",
            created_by="test_user"
        )
        assert v3.version == 3
        assert v3.parent_prompt_id == prompt.id
        
        # Get all versions
        versions = service.get_prompt_versions(prompt.id)
        assert len(versions) == 3
        
        # Deprecate old version
        deprecated = service.deprecate_prompt(prompt.id)
        assert deprecated.status == "deprecated"
        
        # Latest active version should be v3
        latest = service.get_latest_version("lifecycle_test")
        assert latest.version == 3
        assert latest.status == "active"
    
    def test_version_chain(self, db: Session):
        """Test creating multiple versions in a chain"""
        service = PromptService(db)
        
        # Create parent
        parent = service.create_prompt(
            name="chain_test",
            prompt_text="V1",
            prompt_type=PromptType.SYSTEM
        )
        
        # Create chain of versions
        v2 = service.create_version(parent.id, "V2")
        v3 = service.create_version(v2.id, "V3")
        v4 = service.create_version(v3.id, "V4")
        
        # All should have same parent
        assert v2.parent_prompt_id == parent.id
        assert v3.parent_prompt_id == parent.id
        assert v4.parent_prompt_id == parent.id
        
        # Versions should be sequential
        versions = service.get_prompt_versions(parent.id)
        assert len(versions) == 4
        assert versions[0].version == 1
        assert versions[-1].version == 4
    
    def test_filtering_and_search(self, db: Session):
        """Test filtering and searching prompts"""
        service = PromptService(db)
        
        # Create prompts with different attributes
        service.create_prompt(
            name="system_analysis",
            prompt_text="System analysis prompt",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        service.create_prompt(
            name="agent_planning",
            prompt_text="Agent planning prompt",
            prompt_type=PromptType.AGENT,
            level=1
        )
        service.create_prompt(
            name="system_decomposition",
            prompt_text="System decomposition prompt",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        
        # Filter by type
        system_prompts = service.list_prompts(prompt_type=PromptType.SYSTEM)
        assert len(system_prompts) >= 2
        assert all(p.prompt_type == "system" for p in system_prompts)
        
        # Filter by level
        level_0 = service.list_prompts(level=0)
        assert len(level_0) >= 2
        
        # Search by name
        analysis = service.list_prompts(name_search="analysis")
        assert len(analysis) >= 1
        assert any("analysis" in p.name.lower() for p in analysis)
    
    def test_active_prompt_selection(self, db: Session):
        """Test getting active prompt when multiple versions exist"""
        service = PromptService(db)
        
        # Create parent
        parent = service.create_prompt(
            name="active_test",
            prompt_text="V1",
            prompt_type=PromptType.SYSTEM
        )
        
        # Create active version
        active = service.create_version(parent.id, "V2 Active")
        
        # Deprecate parent
        service.deprecate_prompt(parent.id)
        
        # Get active should return latest active version
        result = service.get_active_prompt(name="active_test")
        assert result is not None
        assert result.id == active.id
        assert result.status == "active"
    
    def test_concurrent_versions(self, db: Session):
        """Test handling multiple concurrent versions"""
        service = PromptService(db)
        
        # Create base
        base = service.create_prompt(
            name="concurrent_test",
            prompt_text="Base",
            prompt_type=PromptType.SYSTEM
        )
        
        # Create multiple versions
        v2 = service.create_version(base.id, "Version 2")
        v3 = service.create_version(base.id, "Version 3")
        
        # All should be retrievable
        versions = service.get_prompt_versions(base.id)
        assert len(versions) == 3
        
        # Latest should be v3
        latest = service.get_latest_version("concurrent_test")
        assert latest.version == 3

