"""
Prompt Service for managing prompts with versioning and metrics
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.prompt import Prompt, PromptType, PromptStatus
from app.services.project_metrics_service import ProjectMetricsService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class PromptService:
    """Service for managing prompts with versioning and metrics"""
    
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = ProjectMetricsService(db)
    
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
        """Update prompt (in-place update, does not create new version)
        
        Args:
            prompt_id: Prompt UUID
            prompt_text: New prompt text
            name: New name
            level: New level
            
        Returns:
            Updated Prompt object or None if not found
            
        Note:
            This method updates the prompt in place. To create a new version,
            use create_version() instead.
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
        
        # Do NOT increment version - this is an in-place update
        # Use create_version() if you want to create a new version
        
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
            parent_prompt_id: ID of parent prompt (can be any version)
            prompt_text: New prompt text for the version
            created_by: Creator identifier
            
        Returns:
            New Prompt version or None if parent not found
            
        Note:
            All versions share the same root parent. If parent_prompt_id is
            a version, we find the root parent and use it.
        """
        parent = self.get_prompt(parent_prompt_id)
        if not parent:
            return None
        
        # Find root parent (original prompt)
        root_parent_id = parent_prompt_id
        if parent.parent_prompt_id:
            # This is a version, find the root
            root_parent = self.get_prompt(parent.parent_prompt_id)
            while root_parent and root_parent.parent_prompt_id:
                root_parent = self.get_prompt(root_parent.parent_prompt_id)
            if root_parent:
                root_parent_id = root_parent.id
            else:
                root_parent_id = parent.parent_prompt_id
        
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
                parent_prompt_id=root_parent_id,  # Always use root parent
                status=PromptStatus.ACTIVE.value.lower(),
                created_by=created_by or "system"
            )
            
            self.db.add(new_prompt)
            self.db.commit()
            self.db.refresh(new_prompt)
            
            logger.info(
                f"Created new version {new_version} of prompt: {parent.name}",
                extra={"parent_id": str(parent_prompt_id), "root_parent_id": str(root_parent_id), "new_id": str(new_prompt.id)}
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
            
            # Record project metrics for prompt usage
            try:
                from datetime import timedelta
                from app.models.project_metric import MetricType, MetricPeriod
                
                now = datetime.now(timezone.utc)
                # Round to hour for consistent period boundaries
                period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                period_end = now.replace(minute=0, second=0, microsecond=0)
                
                if execution_time_ms is not None:
                    self.metrics_service.record_metric(
                        metric_type=MetricType.EXECUTION_TIME,
                        metric_name="prompt_execution_time",
                        value=execution_time_ms / 1000.0,  # Convert to seconds
                        period=MetricPeriod.HOUR,
                        period_start=period_start,
                        period_end=period_end,
                        count=1,
                        min_value=execution_time_ms / 1000.0,
                        max_value=execution_time_ms / 1000.0,
                        sum_value=execution_time_ms / 1000.0,
                        metric_metadata={
                            "prompt_id": str(prompt_id),
                            "prompt_name": prompt.name,
                            "prompt_type": prompt.prompt_type
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to record prompt usage metrics: {e}", exc_info=True)
            
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
        from datetime import datetime
        
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        try:
            # Get or initialize improvement_history (create a copy to avoid mutation issues)
            import copy
            history = copy.deepcopy(prompt.improvement_history) if prompt.improvement_history else []
            
            # Add new result
            history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": success,
                "type": "usage_result"
            })
            
            # Extract all usage results and keep only last 100 for sliding window
            window_size = 100
            usage_results = [h for h in history if h.get("type") == "usage_result"]
            
            if len(usage_results) > window_size:
                # Keep only last window_size results
                usage_results = usage_results[-window_size:]
                # Rebuild history: keep non-usage-result entries + last window_size usage results
                other_entries = [h for h in history if h.get("type") != "usage_result"]
                history = other_entries + usage_results
            else:
                # No need to trim, but ensure usage_results is up to date
                usage_results = [h for h in history if h.get("type") == "usage_result"]
            
            prompt.improvement_history = history
            
            # Calculate success_rate from usage results (already limited to window_size)
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
            
            # Record project metrics for prompt success/failure
            try:
                from datetime import timedelta
                from app.models.project_metric import MetricType, MetricPeriod
                
                now = datetime.now(timezone.utc)
                # Round to hour for consistent period boundaries
                period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                period_end = now.replace(minute=0, second=0, microsecond=0)
                
                # Record success rate
                if prompt.success_rate is not None:
                    self.metrics_service.record_metric(
                        metric_type=MetricType.TASK_SUCCESS,
                        metric_name="prompt_success_rate",
                        value=prompt.success_rate,
                        period=MetricPeriod.HOUR,
                        period_start=period_start,
                        period_end=period_end,
                        count=1,
                        metric_metadata={
                            "prompt_id": str(prompt_id),
                            "prompt_name": prompt.name,
                            "prompt_type": prompt.prompt_type,
                            "success": success
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to record prompt result metrics: {e}", exc_info=True)
            
            return prompt
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording prompt result: {e}", exc_info=True)
            raise
    
    async def analyze_prompt_performance(
        self,
        prompt_id: UUID,
        task_description: str,
        result: Any,
        success: bool,
        execution_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Analyze prompt performance using ReflectionService
        
        Args:
            prompt_id: Prompt UUID
            task_description: Description of the task that used the prompt
            result: Result of prompt usage (successful or failed)
            success: Whether the usage was successful
            execution_metadata: Additional metadata about execution
            
        Returns:
            Analysis result dictionary or None if prompt not found
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        try:
            from app.services.reflection_service import ReflectionService
            
            reflection_service = ReflectionService(self.db)
            
            # Analyze based on success/failure
            if success:
                # For successful usage, suggest improvements
                improvements = await reflection_service.suggest_improvement(
                    task_description=task_description,
                    result=result,
                    execution_metadata=execution_metadata
                )
                analysis = {
                    "type": "success_analysis",
                    "improvements": improvements,
                    "suggestions": improvements
                }
            else:
                # For failed usage, analyze failure
                error_message = str(result) if result else "Unknown error"
                reflection_result = await reflection_service.analyze_failure(
                    task_description=task_description,
                    error=error_message,
                    context=execution_metadata
                )
                analysis = {
                    "type": "failure_analysis",
                    "analysis": reflection_result.analysis,
                    "suggested_fix": reflection_result.suggested_fix,
                    "improvements": reflection_result.improvements,
                    "similar_situations": reflection_result.similar_situations
                }
            
            # Save analysis to improvement_history (create a copy to avoid mutation issues)
            import copy
            history = copy.deepcopy(prompt.improvement_history) if prompt.improvement_history else []
            history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "performance_analysis",
                "success": success,
                "task_description": task_description[:500],  # Truncate long descriptions
                "analysis": analysis,
                "execution_metadata": execution_metadata
            })
            
            # Keep only last 50 analyses
            analyses = [h for h in history if h.get("type") == "performance_analysis"]
            if len(analyses) > 50:
                # Remove old analyses, keep only last 50
                other_entries = [h for h in history if h.get("type") != "performance_analysis"]
                history = other_entries + analyses[-50:]
            
            prompt.improvement_history = history
            prompt.last_improved_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(prompt)
            
            logger.info(
                f"Analyzed prompt performance: {prompt.name} (id: {prompt_id})",
                extra={
                    "prompt_id": str(prompt_id),
                    "success": success,
                    "analysis_type": analysis.get("type")
                }
            )
            
            return analysis
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error analyzing prompt performance: {e}", exc_info=True)
            return None
    
    async def suggest_improvements(
        self,
        prompt_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Generate improvement suggestions for a prompt based on metrics and history
        
        Args:
            prompt_id: Prompt UUID
            
        Returns:
            Dictionary with improvement suggestions including:
            - suggestions: List of improvement suggestions
            - priority: Priority level (high/medium/low)
            - expected_effect: Expected effect of improvements
            - analysis: Analysis of current performance
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        try:
            # Analyze metrics
            metrics_analysis = self._analyze_metrics(prompt)
            
            # Analyze improvement history
            history_analysis = self._analyze_improvement_history(prompt)
            
            # Generate LLM-based suggestions
            llm_suggestions = await self._generate_llm_suggestions(
                prompt,
                metrics_analysis,
                history_analysis
            )
            
            # Combine all suggestions
            all_suggestions = []
            
            # Add metric-based suggestions
            if metrics_analysis.get("issues"):
                all_suggestions.extend(metrics_analysis["issues"])
            
            # Add history-based suggestions
            if history_analysis.get("patterns"):
                all_suggestions.extend(history_analysis["patterns"])
            
            # Add LLM suggestions
            if llm_suggestions:
                all_suggestions.extend(llm_suggestions)
            
            # Determine priority
            priority = "low"
            if metrics_analysis.get("success_rate") and metrics_analysis["success_rate"] < 0.5:
                priority = "high"
            elif metrics_analysis.get("success_rate") and metrics_analysis["success_rate"] < 0.7:
                priority = "medium"
            elif metrics_analysis.get("avg_execution_time") and metrics_analysis["avg_execution_time"] > 5000:
                priority = "medium"
            
            result = {
                "suggestions": all_suggestions,
                "priority": priority,
                "expected_effect": self._estimate_expected_effect(metrics_analysis, all_suggestions),
                "analysis": {
                    "metrics": metrics_analysis,
                    "history": history_analysis
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Save suggestions to improvement_history
            history = prompt.improvement_history or []
            history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "improvement_suggestions",
                "suggestions": result
            })
            
            # Keep only last 20 suggestion sets
            suggestions = [h for h in history if h.get("type") == "improvement_suggestions"]
            if len(suggestions) > 20:
                history = [h for h in history if h.get("type") != "improvement_suggestions"]
                history.extend(suggestions[-20:])
            
            prompt.improvement_history = history
            self.db.commit()
            self.db.refresh(prompt)
            
            logger.info(
                f"Generated improvement suggestions for prompt: {prompt.name} (id: {prompt_id})",
                extra={
                    "prompt_id": str(prompt_id),
                    "suggestions_count": len(all_suggestions),
                    "priority": priority
                }
            )
            
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error generating improvement suggestions: {e}", exc_info=True)
            return None
    
    def _analyze_metrics(self, prompt: Prompt) -> Dict[str, Any]:
        """Analyze prompt metrics to identify issues"""
        issues = []
        analysis = {}
        
        # Success rate analysis
        if prompt.success_rate is not None:
            analysis["success_rate"] = prompt.success_rate
            if prompt.success_rate < 0.5:
                issues.append({
                    "type": "low_success_rate",
                    "message": f"Success rate is low ({prompt.success_rate:.1%}). Consider reviewing prompt clarity and instructions.",
                    "priority": "high"
                })
            elif prompt.success_rate < 0.7:
                issues.append({
                    "type": "moderate_success_rate",
                    "message": f"Success rate could be improved ({prompt.success_rate:.1%}). Review common failure patterns.",
                    "priority": "medium"
                })
        
        # Execution time analysis
        if prompt.avg_execution_time is not None:
            analysis["avg_execution_time"] = prompt.avg_execution_time
            if prompt.avg_execution_time > 10000:  # > 10 seconds
                issues.append({
                    "type": "slow_execution",
                    "message": f"Average execution time is high ({prompt.avg_execution_time/1000:.1f}s). Consider simplifying prompt or breaking into steps.",
                    "priority": "medium"
                })
            elif prompt.avg_execution_time > 5000:  # > 5 seconds
                issues.append({
                    "type": "moderate_execution_time",
                    "message": f"Execution time could be optimized ({prompt.avg_execution_time/1000:.1f}s).",
                    "priority": "low"
                })
        
        # Usage count analysis
        analysis["usage_count"] = prompt.usage_count
        if prompt.usage_count < 10:
            issues.append({
                "type": "low_usage",
                "message": f"Low usage count ({prompt.usage_count}). Need more data for reliable metrics.",
                "priority": "low"
            })
        
        return {
            "issues": issues,
            **analysis
        }
    
    def _analyze_improvement_history(self, prompt: Prompt) -> Dict[str, Any]:
        """Analyze improvement history to identify patterns"""
        history = prompt.improvement_history or []
        patterns = []
        
        # Analyze performance analyses
        analyses = [h for h in history if h.get("type") == "performance_analysis"]
        if analyses:
            success_count = sum(1 for a in analyses if a.get("success", False))
            failure_count = len(analyses) - success_count
            
            if failure_count > success_count:
                patterns.append({
                    "type": "failure_pattern",
                    "message": f"More failures than successes in recent analyses ({failure_count} failures, {success_count} successes). Review failure patterns.",
                    "priority": "high"
                })
            
            # Extract common failure reasons
            failure_analyses = [a for a in analyses if not a.get("success", False)]
            if failure_analyses:
                error_types = {}
                for a in failure_analyses:
                    metadata = a.get("execution_metadata")
                    if metadata and isinstance(metadata, dict):
                        error_type = metadata.get("error_type", "unknown")
                    else:
                        error_type = "unknown"
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                
                if error_types:
                    most_common = max(error_types.items(), key=lambda x: x[1])
                    if most_common[1] > 2:
                        patterns.append({
                            "type": "common_error",
                            "message": f"Common error type: {most_common[0]} (occurred {most_common[1]} times). Consider addressing this in prompt.",
                            "priority": "medium"
                        })
        
        return {
            "patterns": patterns,
            "total_analyses": len(analyses),
            "recent_analyses": len([a for a in analyses if a.get("timestamp")])  # Count with timestamps
        }
    
    async def _generate_llm_suggestions(
        self,
        prompt: Prompt,
        metrics_analysis: Dict[str, Any],
        history_analysis: Dict[str, Any]
    ) -> Optional[List[str]]:
        """Use LLM to generate improvement suggestions"""
        try:
            from app.core.ollama_client import OllamaClient, TaskType
            from app.core.model_selector import ModelSelector
            
            # Get planning model for suggestions
            model_selector = ModelSelector(self.db)
            planning_model = model_selector.get_planning_model()
            
            if not planning_model:
                logger.warning("No planning model available for LLM suggestions")
                return None
            
            server = model_selector.get_server_for_model(planning_model)
            if not server:
                logger.warning("No server available for LLM suggestions")
                return None
            
            # Build context for LLM
            context_parts = []
            context_parts.append(f"Prompt Name: {prompt.name}")
            context_parts.append(f"Prompt Text: {prompt.prompt_text[:1000]}")  # First 1000 chars
            
            if metrics_analysis.get("success_rate") is not None:
                context_parts.append(f"Success Rate: {metrics_analysis['success_rate']:.1%}")
            if metrics_analysis.get("avg_execution_time") is not None:
                context_parts.append(f"Average Execution Time: {metrics_analysis['avg_execution_time']/1000:.1f}s")
            context_parts.append(f"Usage Count: {prompt.usage_count}")
            
            if metrics_analysis.get("issues"):
                context_parts.append(f"Issues Identified: {len(metrics_analysis['issues'])}")
                for issue in metrics_analysis["issues"][:3]:  # First 3 issues
                    context_parts.append(f"- {issue['message']}")
            
            if history_analysis.get("patterns"):
                context_parts.append(f"Patterns Found: {len(history_analysis['patterns'])}")
                for pattern in history_analysis["patterns"][:3]:  # First 3 patterns
                    context_parts.append(f"- {pattern['message']}")
            
            context = "\n".join(context_parts)
            
            system_prompt = """You are an expert at analyzing and improving prompts for AI systems.
Analyze the provided prompt and its performance metrics, then suggest specific, actionable improvements.
Focus on clarity, specificity, and addressing identified issues.
Return a JSON array of improvement suggestions, each as a string."""
            
            user_prompt = f"""Analyze this prompt and suggest improvements:

{context}

Provide 3-5 specific, actionable suggestions for improving this prompt. Return as JSON array of strings."""
            
            ollama_client = OllamaClient()
            response = await ollama_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                task_type=TaskType.PLANNING,
                model=planning_model.model_name,
                server_url=server.get_api_url()
            )
            
            # Parse JSON response
            try:
                import json
                suggestions = json.loads(response.response)
                if isinstance(suggestions, list):
                    return suggestions[:5]  # Limit to 5 suggestions
                elif isinstance(suggestions, str):
                    return [suggestions]
            except json.JSONDecodeError:
                # If not JSON, try to extract suggestions from text
                lines = response.response.strip().split('\n')
                suggestions = [line.strip('- ').strip() for line in lines if line.strip() and len(line.strip()) > 20]
                return suggestions[:5] if suggestions else None
            
            return None
        except Exception as e:
            logger.warning(f"Failed to generate LLM suggestions: {e}", exc_info=True)
            return None
    
    def _estimate_expected_effect(
        self,
        metrics_analysis: Dict[str, Any],
        suggestions: List[Any]
    ) -> str:
        """Estimate expected effect of implementing suggestions"""
        if not suggestions:
            return "No suggestions available"
        
        # Simple heuristic based on current metrics
        if metrics_analysis.get("success_rate") and metrics_analysis["success_rate"] < 0.5:
            return "High potential impact: Could significantly improve success rate"
        elif metrics_analysis.get("success_rate") and metrics_analysis["success_rate"] < 0.7:
            return "Medium potential impact: Could improve success rate by 10-20%"
        elif metrics_analysis.get("avg_execution_time") and metrics_analysis["avg_execution_time"] > 5000:
            return "Medium potential impact: Could reduce execution time by 20-30%"
        else:
            return "Low to medium impact: Incremental improvements expected"
    
    async def create_improved_version(
        self,
        prompt_id: UUID,
        suggestions: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> Optional[Prompt]:
        """Create an improved version of a prompt based on suggestions
        
        Args:
            prompt_id: Prompt UUID to improve
            suggestions: Optional list of improvement suggestions (if None, will generate)
            created_by: Creator identifier
            
        Returns:
            New Prompt version with status TESTING or None if error
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        try:
            # Generate suggestions if not provided
            if not suggestions:
                suggestions_result = await self.suggest_improvements(prompt_id)
                if suggestions_result and suggestions_result.get("suggestions"):
                    # Extract suggestion messages
                    suggestions = []
                    for s in suggestions_result["suggestions"]:
                        if isinstance(s, dict):
                            suggestions.append(s.get("message", str(s)))
                        else:
                            suggestions.append(str(s))
            
            if not suggestions:
                logger.warning(f"No suggestions available for prompt {prompt_id}")
                return None
            
            # Use LLM to generate improved version
            improved_text = await self._generate_improved_prompt_text(
                prompt,
                suggestions
            )
            
            if not improved_text:
                logger.warning(f"Failed to generate improved prompt text for {prompt_id}")
                return None
            
            # Create new version with status TESTING
            new_version = self.create_version(
                parent_prompt_id=prompt_id,
                prompt_text=improved_text,
                created_by=created_by or "system"
            )
            
            if new_version:
                # Set status to TESTING
                new_version.status = PromptStatus.TESTING.value.lower()
                self.db.commit()
                self.db.refresh(new_version)
                
                # Save improvement metadata
                history = new_version.improvement_history or []
                history.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "version_creation",
                    "parent_version": prompt.version,
                    "suggestions_used": suggestions,
                    "status": "testing"
                })
                new_version.improvement_history = history
                self.db.commit()
                self.db.refresh(new_version)
                
                logger.info(
                    f"Created improved version {new_version.version} of prompt: {prompt.name} (id: {prompt_id})",
                    extra={
                        "parent_id": str(prompt_id),
                        "new_id": str(new_version.id),
                        "new_version": new_version.version
                    }
                )
            
            return new_version
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating improved version: {e}", exc_info=True)
            return None
    
    async def _generate_improved_prompt_text(
        self,
        prompt: Prompt,
        suggestions: List[str]
    ) -> Optional[str]:
        """Use LLM to generate improved prompt text based on suggestions"""
        try:
            from app.core.ollama_client import OllamaClient, TaskType
            from app.core.model_selector import ModelSelector
            
            # Get planning model
            model_selector = ModelSelector(self.db)
            planning_model = model_selector.get_planning_model()
            
            if not planning_model:
                logger.warning("No planning model available for prompt improvement")
                return None
            
            server = model_selector.get_server_for_model(planning_model)
            if not server:
                logger.warning("No server available for prompt improvement")
                return None
            
            # Build prompt for LLM
            suggestions_text = "\n".join([f"- {s}" for s in suggestions[:10]])  # Limit to 10 suggestions
            
            system_prompt = """You are an expert at writing and improving prompts for AI systems.
Your task is to improve a prompt based on specific suggestions while maintaining its core purpose and structure.
Return ONLY the improved prompt text, without any additional explanation or commentary."""
            
            user_prompt = f"""Original Prompt:
{prompt.prompt_text}

Improvement Suggestions:
{suggestions_text}

Generate an improved version of the prompt that addresses these suggestions while maintaining the original purpose and structure. Return only the improved prompt text."""
            
            ollama_client = OllamaClient()
            response = await ollama_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                task_type=TaskType.PLANNING,
                model=planning_model.model_name,
                server_url=server.get_api_url()
            )
            
            improved_text = response.response.strip()
            
            # Basic validation - ensure we got something meaningful
            if len(improved_text) < len(prompt.prompt_text) * 0.5:
                logger.warning(f"Generated prompt text seems too short: {len(improved_text)} chars")
                return None
            
            return improved_text
        except Exception as e:
            logger.error(f"Error generating improved prompt text: {e}", exc_info=True)
            return None
    
    async def auto_create_improved_version_if_needed(
        self,
        prompt_id: UUID,
        success_rate_threshold: float = 0.5,
        execution_time_threshold_ms: float = 10000.0
    ) -> Optional[Prompt]:
        """Automatically create improved version if metrics are below thresholds
        
        Args:
            prompt_id: Prompt UUID
            success_rate_threshold: Threshold below which to trigger improvement (default 0.5)
            execution_time_threshold_ms: Threshold above which to trigger improvement (default 10000ms)
            
        Returns:
            New improved version or None if not needed/error
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        # Check if improvement is needed
        needs_improvement = False
        reason = []
        
        if prompt.success_rate is not None and prompt.success_rate < success_rate_threshold:
            needs_improvement = True
            reason.append(f"low success rate ({prompt.success_rate:.1%} < {success_rate_threshold:.1%})")
        
        if prompt.avg_execution_time is not None and prompt.avg_execution_time > execution_time_threshold_ms:
            needs_improvement = True
            reason.append(f"high execution time ({prompt.avg_execution_time/1000:.1f}s > {execution_time_threshold_ms/1000:.1f}s)")
        
        if not needs_improvement:
            logger.debug(
                f"Prompt {prompt.name} does not need improvement",
                extra={"prompt_id": str(prompt_id)}
            )
            return None
        
        logger.info(
            f"Auto-creating improved version for prompt {prompt.name}: {', '.join(reason)}",
            extra={
                "prompt_id": str(prompt_id),
                "reasons": reason
            }
        )
        
        # Create improved version
        return await self.create_improved_version(prompt_id, created_by="system")

