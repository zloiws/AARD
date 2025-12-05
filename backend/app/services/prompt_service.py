"""
Prompt Service for managing prompts with versioning and metrics
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.prompt import Prompt, PromptType, PromptStatus
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class PromptService:
    """Service for managing prompts with versioning and metrics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_prompt(
        self,
        name: str,
        prompt_text: str,
        prompt_type: PromptType,
        level: int = 0,
        created_by: Optional[str] = None
    ) -> Prompt:
        """Create a new prompt
        
        Args:
            name: Prompt name
            prompt_text: Prompt text content
            prompt_type: Type of prompt (SYSTEM, AGENT, TOOL, META, CONTEXT)
            level: Prompt level (0-4)
            created_by: Creator identifier
            
        Returns:
            Created Prompt object
        """
        try:
            prompt = Prompt(
                name=name,
                prompt_text=prompt_text,
                prompt_type=prompt_type.value.lower() if hasattr(prompt_type, 'value') else str(prompt_type).lower(),
                level=level,
                version=1,
                status=PromptStatus.ACTIVE.value.lower(),
                created_by=created_by or "system"
            )
            
            self.db.add(prompt)
            self.db.commit()
            self.db.refresh(prompt)
            
            logger.info(
                f"Created prompt: {name} (type: {prompt_type}, level: {level})",
                extra={"prompt_id": str(prompt.id), "name": name}
            )
            
            return prompt
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating prompt: {e}", exc_info=True)
            raise
    
    def get_prompt(self, prompt_id: UUID) -> Optional[Prompt]:
        """Get prompt by ID
        
        Args:
            prompt_id: Prompt UUID
            
        Returns:
            Prompt object or None if not found
        """
        return self.db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    def get_active_prompt(
        self,
        name: Optional[str] = None,
        prompt_type: Optional[PromptType] = None,
        level: Optional[int] = None
    ) -> Optional[Prompt]:
        """Get active prompt by name/type/level
        
        Args:
            name: Prompt name (exact match)
            prompt_type: Prompt type
            level: Prompt level
            
        Returns:
            Active prompt or None if not found
        """
        query = self.db.query(Prompt).filter(
            Prompt.status == PromptStatus.ACTIVE.value.lower()
        )
        
        if name:
            query = query.filter(Prompt.name == name)
        if prompt_type:
            prompt_type_str = prompt_type.value.lower() if hasattr(prompt_type, 'value') else str(prompt_type).lower()
            query = query.filter(Prompt.prompt_type == prompt_type_str)
        if level is not None:
            query = query.filter(Prompt.level == level)
        
        # Get the latest version (highest version number)
        prompt = query.order_by(Prompt.version.desc()).first()
        
        return prompt
    
    def list_prompts(
        self,
        prompt_type: Optional[PromptType] = None,
        status: Optional[PromptStatus] = None,
        level: Optional[int] = None,
        name_search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Prompt]:
        """List prompts with filtering
        
        Args:
            prompt_type: Filter by type
            status: Filter by status
            level: Filter by level
            name_search: Search by name (partial match)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of Prompt objects
        """
        query = self.db.query(Prompt)
        
        if prompt_type:
            prompt_type_str = prompt_type.value.lower() if hasattr(prompt_type, 'value') else str(prompt_type).lower()
            query = query.filter(Prompt.prompt_type == prompt_type_str)
        
        if status:
            status_str = status.value.lower() if hasattr(status, 'value') else str(status).lower()
            query = query.filter(Prompt.status == status_str)
        
        if level is not None:
            query = query.filter(Prompt.level == level)
        
        if name_search:
            query = query.filter(Prompt.name.ilike(f"%{name_search}%"))
        
        return query.order_by(Prompt.created_at.desc()).offset(offset).limit(limit).all()
    
    def update_prompt(
        self,
        prompt_id: UUID,
        prompt_text: Optional[str] = None,
        name: Optional[str] = None,
        level: Optional[int] = None
    ) -> Optional[Prompt]:
        """Update prompt
        
        Args:
            prompt_id: Prompt UUID
            prompt_text: New prompt text
            name: New name
            level: New level
            
        Returns:
            Updated Prompt object or None if not found
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        if prompt_text is not None:
            prompt.prompt_text = prompt_text
        if name is not None:
            prompt.name = name
        if level is not None:
            prompt.level = level
        
        # Increment version when content changes
        if prompt_text is not None:
            prompt.version += 1
        
        try:
            self.db.commit()
            self.db.refresh(prompt)
            
            logger.info(f"Updated prompt: {prompt.name} (id: {prompt_id})")
            
            return prompt
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating prompt: {e}", exc_info=True)
            raise
    
    def create_version(
        self,
        parent_prompt_id: UUID,
        prompt_text: str,
        created_by: Optional[str] = None
    ) -> Optional[Prompt]:
        """Create a new version of existing prompt
        
        Args:
            parent_prompt_id: ID of parent prompt
            prompt_text: New prompt text for the version
            created_by: Creator identifier
            
        Returns:
            New Prompt version or None if parent not found
        """
        parent = self.get_prompt(parent_prompt_id)
        if not parent:
            return None
        
        # Get the highest version number for this prompt name
        max_version = self.db.query(Prompt).filter(
            Prompt.name == parent.name
        ).order_by(Prompt.version.desc()).first()
        
        new_version = max_version.version + 1 if max_version else parent.version + 1
        
        try:
            new_prompt = Prompt(
                name=parent.name,
                prompt_text=prompt_text,
                prompt_type=parent.prompt_type,
                level=parent.level,
                version=new_version,
                parent_prompt_id=parent_prompt_id,
                status=PromptStatus.ACTIVE.value.lower(),
                created_by=created_by or "system"
            )
            
            self.db.add(new_prompt)
            self.db.commit()
            self.db.refresh(new_prompt)
            
            logger.info(
                f"Created new version {new_version} of prompt: {parent.name}",
                extra={"parent_id": str(parent_prompt_id), "new_id": str(new_prompt.id)}
            )
            
            return new_prompt
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating prompt version: {e}", exc_info=True)
            raise
    
    def deprecate_prompt(self, prompt_id: UUID) -> Optional[Prompt]:
        """Deprecate (disable) a prompt
        
        Args:
            prompt_id: Prompt UUID
            
        Returns:
            Deprecated Prompt object or None if not found
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        prompt.status = PromptStatus.DEPRECATED.value.lower()
        
        try:
            self.db.commit()
            self.db.refresh(prompt)
            
            logger.info(f"Deprecated prompt: {prompt.name} (id: {prompt_id})")
            
            return prompt
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deprecating prompt: {e}", exc_info=True)
            raise
    
    def get_prompt_versions(self, prompt_id: UUID) -> List[Prompt]:
        """Get all versions of a prompt
        
        Args:
            prompt_id: Prompt UUID (can be any version)
            
        Returns:
            List of all versions ordered by version number
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return []
        
        # Get parent prompt if this is a version
        parent_id = prompt.parent_prompt_id or prompt.id
        
        # Get all versions (parent and all children)
        versions = self.db.query(Prompt).filter(
            or_(
                Prompt.id == parent_id,
                Prompt.parent_prompt_id == parent_id
            )
        ).order_by(Prompt.version.asc()).all()
        
        return versions
    
    def get_latest_version(self, name: str, prompt_type: Optional[PromptType] = None) -> Optional[Prompt]:
        """Get the latest version of a prompt by name
        
        Args:
            name: Prompt name
            prompt_type: Optional prompt type filter
            
        Returns:
            Latest version of the prompt or None
        """
        query = self.db.query(Prompt).filter(Prompt.name == name)
        
        if prompt_type:
            prompt_type_str = prompt_type.value.lower() if hasattr(prompt_type, 'value') else str(prompt_type).lower()
            query = query.filter(Prompt.prompt_type == prompt_type_str)
        
        return query.order_by(Prompt.version.desc()).first()

