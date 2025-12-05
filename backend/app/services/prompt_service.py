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
    
    def record_usage(
        self,
        prompt_id: UUID,
        execution_time_ms: Optional[float] = None
    ) -> Optional[Prompt]:
        """Record prompt usage and update metrics
        
        Args:
            prompt_id: Prompt UUID
            execution_time_ms: Execution time in milliseconds (optional)
            
        Returns:
            Updated Prompt object or None if not found
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        try:
            # Increment usage count
            prompt.usage_count += 1
            
            # Update average execution time if provided
            if execution_time_ms is not None:
                # Calculate moving average (using exponential smoothing)
                # For first usage, set directly; for subsequent, use weighted average
                if prompt.avg_execution_time is None:
                    prompt.avg_execution_time = execution_time_ms
                else:
                    # Exponential moving average with alpha=0.1 (gives more weight to recent values)
                    alpha = 0.1
                    prompt.avg_execution_time = (
                        alpha * execution_time_ms + 
                        (1 - alpha) * prompt.avg_execution_time
                    )
            
            self.db.commit()
            self.db.refresh(prompt)
            
            logger.debug(
                f"Recorded usage for prompt: {prompt.name} (id: {prompt_id})",
                extra={
                    "prompt_id": str(prompt_id),
                    "usage_count": prompt.usage_count,
                    "avg_execution_time": prompt.avg_execution_time
                }
            )
            
            return prompt
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording prompt usage: {e}", exc_info=True)
            raise
    
    def record_success(self, prompt_id: UUID) -> Optional[Prompt]:
        """Record successful prompt usage
        
        Args:
            prompt_id: Prompt UUID
            
        Returns:
            Updated Prompt object or None if not found
        """
        return self._record_result(prompt_id, success=True)
    
    def record_failure(self, prompt_id: UUID) -> Optional[Prompt]:
        """Record failed prompt usage
        
        Args:
            prompt_id: Prompt UUID
            
        Returns:
            Updated Prompt object or None if not found
        """
        return self._record_result(prompt_id, success=False)
    
    def _record_result(self, prompt_id: UUID, success: bool) -> Optional[Prompt]:
        """Record success or failure and update success_rate
        
        Uses a sliding window approach (last 100 results) to calculate success_rate.
        Stores results in improvement_history for tracking.
        
        Args:
            prompt_id: Prompt UUID
            success: True for success, False for failure
            
        Returns:
            Updated Prompt object or None if not found
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        try:
            # Get or initialize improvement_history
            history = prompt.improvement_history or []
            
            # Add new result
            history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "success": success,
                "type": "usage_result"
            })
            
            # Keep only last 100 results for sliding window
            window_size = 100
            if len(history) > window_size:
                # Keep only usage results from last window_size entries
                usage_results = [h for h in history if h.get("type") == "usage_result"]
                if len(usage_results) > window_size:
                    # Keep only last window_size results
                    history = [h for h in history if h.get("type") != "usage_result"]
                    history.extend(usage_results[-window_size:])
            
            prompt.improvement_history = history
            
            # Calculate success_rate from last 100 results
            usage_results = [h for h in history if h.get("type") == "usage_result"]
            if usage_results:
                successful = sum(1 for h in usage_results if h.get("success", False))
                total = len(usage_results)
                prompt.success_rate = successful / total if total > 0 else None
            else:
                prompt.success_rate = None
            
            self.db.commit()
            self.db.refresh(prompt)
            
            logger.debug(
                f"Recorded {'success' if success else 'failure'} for prompt: {prompt.name} (id: {prompt_id})",
                extra={
                    "prompt_id": str(prompt_id),
                    "success": success,
                    "success_rate": prompt.success_rate
                }
            )
            
            return prompt
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording prompt result: {e}", exc_info=True)
            raise

