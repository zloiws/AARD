"""
Meta-Learning Service for self-improvement
Analyzes execution patterns and improves planning strategies, prompts, and tool selection
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.database import SessionLocal
from app.core.execution_context import ExecutionContext
from app.core.logging_config import LoggingConfig
from app.models.agent import Agent
from app.models.learning_pattern import LearningPattern, PatternType
from app.models.plan import Plan
from app.models.trace import ExecutionTrace
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class MetaLearningService:
    """
    Service for meta-learning and self-improvement:
    - Analyzes execution patterns
    - Extracts successful patterns
    - Improves planning strategies
    - Evolves prompts
    - Optimizes tool selection
    """
    
    def __init__(self, db_or_context: Union[Session, ExecutionContext] = None):
        """
        Initialize Meta Learning Service
        
        Args:
            db_or_context: Either a Session (for backward compatibility) or ExecutionContext
        """
        # Support both ExecutionContext and Session for backward compatibility
        if isinstance(db_or_context, ExecutionContext):
            self.context = db_or_context
            self.db = db_or_context.db
            self.workflow_id = db_or_context.workflow_id
        elif db_or_context is not None:
            # Backward compatibility: create minimal context from Session
            self.db = db_or_context
            self.context = ExecutionContext.from_db_session(db_or_context)
            self.workflow_id = self.context.workflow_id
        else:
            # Create new session and context if nothing provided
            self.db = SessionLocal()
            self.context = ExecutionContext.from_db_session(self.db)
            self.workflow_id = self.context.workflow_id
    
    async def analyze_execution_patterns_async(
        self,
        agent_id: Optional[UUID] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """
        Async version of analyze_execution_patterns (kept for backwards compat where awaited).
        Runs the synchronous analysis in a thread executor to avoid blocking the event loop.
        """
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.analyze_execution_patterns_sync(agent_id=agent_id, time_range_days=time_range_days))
        except Exception as e:
            logger.error(f"Error analyzing execution patterns (async): {e}", exc_info=True)
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "overall_success_rate": 0.0,
                "operations": {},
                "time_range_days": time_range_days
            }

    def analyze_execution_patterns(
        self,
        agent_id: Optional[UUID] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """
        Synchronous analyze_execution_patterns wrapper for compatibility with callers
        that call this method without awaiting. Delegates to the synchronous implementation.
        """
        return self.analyze_execution_patterns_sync(agent_id=agent_id, time_range_days=time_range_days)
    
    def analyze_execution_patterns_sync(
        self,
        agent_id: Optional[UUID] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """
        Synchronous version of analyze_execution_patterns (for backward compatibility)
        
        Args:
            agent_id: Optional agent ID for agent-specific analysis
            time_range_days: Number of days to analyze
            
        Returns:
            Dictionary with pattern analysis results
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=time_range_days)
            
            # Query execution traces
            query = self.db.query(ExecutionTrace).filter(
                ExecutionTrace.start_time >= cutoff_date
            )
            
            if agent_id:
                query = query.filter(ExecutionTrace.agent_id == agent_id)
            
            traces = query.all()
            
            # Analyze patterns
            total_executions = len(traces)
            successful = sum(1 for t in traces if t.status == "success")
            failed = sum(1 for t in traces if t.status == "error")
            
            # Group by operation
            operations = {}
            for trace in traces:
                op_name = trace.operation_name
                if op_name not in operations:
                    operations[op_name] = {"total": 0, "success": 0, "failed": 0}
                operations[op_name]["total"] += 1
                if trace.status == "success":
                    operations[op_name]["success"] += 1
                elif trace.status == "error":
                    operations[op_name]["failed"] += 1
            
            # Calculate success rates
            for op_name, stats in operations.items():
                stats["success_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
            
            return {
                "total_executions": total_executions,
                "successful": successful,
                "failed": failed,
                "overall_success_rate": successful / total_executions if total_executions > 0 else 0.0,
                "operations": operations,
                "time_range_days": time_range_days
            }
            
        except Exception as e:
            logger.error(f"Error analyzing execution patterns: {e}", exc_info=True)
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "overall_success_rate": 0.0,
                "operations": {},
                "time_range_days": time_range_days
            }
    
    async def extract_successful_patterns(
        self,
        execution_results: List[Dict[str, Any]],
        pattern_type: PatternType = PatternType.STRATEGY
    ) -> List[LearningPattern]:
        """
        Extract successful patterns from execution results (async)
        
        This method is now async to allow background processing without blocking.
        
        Args:
            execution_results: List of execution result dictionaries
            pattern_type: Type of pattern to extract
            
        Returns:
            List of extracted LearningPattern instances
        """
        try:
            # Run pattern extraction in background thread to avoid blocking
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            def _extract_sync():
                patterns = []
                
                # Group successful executions
                successful = [r for r in execution_results if r.get("status") == "success"]
                
                if not successful:
                    logger.warning("No successful executions to extract patterns from")
                    return []
                
                # Extract common patterns based on type
                if pattern_type == PatternType.STRATEGY:
                    patterns = self._extract_strategy_patterns(successful)
                elif pattern_type == PatternType.PROMPT:
                    patterns = self._extract_prompt_patterns(successful)
                elif pattern_type == PatternType.TOOL_SELECTION:
                    patterns = self._extract_tool_selection_patterns(successful)
                elif pattern_type == PatternType.CODE_PATTERN:
                    patterns = self._extract_code_patterns(successful)
                
                # Save patterns to database
                saved_patterns = []
                for pattern_data in patterns:
                    pattern = LearningPattern(
                        pattern_type=pattern_type.value,
                        name=pattern_data.get("name", f"{pattern_type.value}_pattern"),
                        description=pattern_data.get("description"),
                        pattern_data=pattern_data.get("data", {}),
                        success_rate=pattern_data.get("success_rate", 0.0),
                        usage_count=pattern_data.get("usage_count", 0),
                        total_executions=pattern_data.get("total_executions", 0),
                        successful_executions=pattern_data.get("successful_executions", 0),
                        agent_id=pattern_data.get("agent_id"),
                        task_category=pattern_data.get("task_category")
                    )
                    self.db.add(pattern)
                    saved_patterns.append(pattern)
                
                self.db.commit()
                
                logger.info(
                    f"Extracted {len(saved_patterns)} {pattern_type.value} patterns",
                    extra={"pattern_type": pattern_type.value, "count": len(saved_patterns)}
                )
                
                return saved_patterns
            
            # Run in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, _extract_sync)
                return result
            
        except Exception as e:
            logger.error(f"Error extracting successful patterns: {e}", exc_info=True)
            try:
                self.db.rollback()
            except:
                pass
            return []
    
    def extract_successful_patterns_sync(
        self,
        execution_results: List[Dict[str, Any]],
        pattern_type: PatternType = PatternType.STRATEGY
    ) -> List[LearningPattern]:
        """
        Synchronous version of extract_successful_patterns (for backward compatibility)
        
        Args:
            execution_results: List of execution result dictionaries
            pattern_type: Type of pattern to extract
            
        Returns:
            List of extracted LearningPattern instances
        """
        try:
            patterns = []
            
            # Group successful executions
            successful = [r for r in execution_results if r.get("status") == "success"]
            
            if not successful:
                logger.warning("No successful executions to extract patterns from")
                return []
            
            # Extract common patterns based on type
            if pattern_type == PatternType.STRATEGY:
                patterns = self._extract_strategy_patterns(successful)
            elif pattern_type == PatternType.PROMPT:
                patterns = self._extract_prompt_patterns(successful)
            elif pattern_type == PatternType.TOOL_SELECTION:
                patterns = self._extract_tool_selection_patterns(successful)
            elif pattern_type == PatternType.CODE_PATTERN:
                patterns = self._extract_code_patterns(successful)
            
            # Save patterns to database
            saved_patterns = []
            for pattern_data in patterns:
                pattern = LearningPattern(
                    pattern_type=pattern_type.value,
                    name=pattern_data.get("name", f"{pattern_type.value}_pattern"),
                    description=pattern_data.get("description"),
                    pattern_data=pattern_data.get("data", {}),
                    success_rate=pattern_data.get("success_rate", 0.0),
                    usage_count=pattern_data.get("usage_count", 0),
                    total_executions=pattern_data.get("total_executions", 0),
                    successful_executions=pattern_data.get("successful_executions", 0),
                    agent_id=pattern_data.get("agent_id"),
                    task_category=pattern_data.get("task_category")
                )
                self.db.add(pattern)
                saved_patterns.append(pattern)
            
            self.db.commit()
            
            logger.info(
                f"Extracted {len(saved_patterns)} {pattern_type.value} patterns",
                extra={"pattern_type": pattern_type.value, "count": len(saved_patterns)}
            )
            
            return saved_patterns
            
        except Exception as e:
            logger.error(f"Error extracting successful patterns: {e}", exc_info=True)
            self.db.rollback()
            return []
    
    def _extract_strategy_patterns(self, successful: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract strategy patterns from successful executions"""
        patterns = []
        
        # Find common strategy elements
        common_steps = {}
        for result in successful:
            plan = result.get("plan")
            if plan and isinstance(plan, dict):
                steps = plan.get("steps", [])
                for step in steps:
                    step_type = step.get("type")
                    if step_type:
                        if step_type not in common_steps:
                            common_steps[step_type] = 0
                        common_steps[step_type] += 1
        
        if common_steps:
            # Create pattern for most common strategy
            most_common = max(common_steps.items(), key=lambda x: x[1])
            patterns.append({
                "name": f"Strategy: {most_common[0]}",
                "description": f"Common strategy using {most_common[0]} steps",
                "data": {"step_type": most_common[0], "frequency": most_common[1]},
                "success_rate": 1.0,  # All are successful
                "usage_count": most_common[1],
                "total_executions": len(successful),
                "successful_executions": len(successful)
            })
        
        return patterns
    
    def _extract_prompt_patterns(self, successful: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract prompt patterns from successful executions"""
        patterns = []
        
        # Find common prompt structures
        prompt_keywords = {}
        for result in successful:
            prompt = result.get("prompt") or result.get("system_prompt")
            if prompt:
                # Simple keyword extraction
                words = prompt.lower().split()
                for word in words:
                    if len(word) > 4:  # Filter short words
                        if word not in prompt_keywords:
                            prompt_keywords[word] = 0
                        prompt_keywords[word] += 1
        
        if prompt_keywords:
            top_keywords = sorted(prompt_keywords.items(), key=lambda x: x[1], reverse=True)[:5]
            patterns.append({
                "name": "Prompt: Effective Keywords",
                "description": "Common keywords in successful prompts",
                "data": {"keywords": dict(top_keywords)},
                "success_rate": 1.0,
                "usage_count": len(successful),
                "total_executions": len(successful),
                "successful_executions": len(successful)
            })
        
        return patterns
    
    def _extract_tool_selection_patterns(self, successful: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tool selection patterns from successful executions"""
        patterns = []
        
        # Find commonly used tools
        tool_usage = {}
        for result in successful:
            tools = result.get("tools_used", [])
            for tool in tools:
                tool_name = tool if isinstance(tool, str) else tool.get("name", "unknown")
                if tool_name not in tool_usage:
                    tool_usage[tool_name] = 0
                tool_usage[tool_name] += 1
        
        if tool_usage:
            top_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:3]
            patterns.append({
                "name": "Tool Selection: Top Tools",
                "description": "Most effective tools for task execution",
                "data": {"tools": dict(top_tools)},
                "success_rate": 1.0,
                "usage_count": len(successful),
                "total_executions": len(successful),
                "successful_executions": len(successful)
            })
        
        return patterns
    
    def _extract_code_patterns(self, successful: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract code patterns from successful executions"""
        patterns = []
        
        # Find common code structures
        code_snippets = []
        for result in successful:
            code = result.get("code") or result.get("generated_code")
            if code:
                code_snippets.append(code[:100])  # First 100 chars
        
        if code_snippets:
            patterns.append({
                "name": "Code Pattern: Common Structures",
                "description": "Common code structures in successful executions",
                "data": {"snippets": code_snippets[:5]},  # Top 5
                "success_rate": 1.0,
                "usage_count": len(code_snippets),
                "total_executions": len(successful),
                "successful_executions": len(successful)
            })
        
        return patterns
    
    def improve_planning_strategy(self, plan_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Improve planning strategy based on execution results
        
        Args:
            plan_id: Plan ID to improve
            
        Returns:
            Dictionary with improved strategy or None
        """
        try:
            plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                logger.warning(f"Plan {plan_id} not found")
                return None
            
            # Get execution traces for this plan
            traces = self.db.query(ExecutionTrace).filter(
                ExecutionTrace.plan_id == plan_id
            ).all()
            
            if not traces:
                logger.warning(f"No execution traces found for plan {plan_id}")
                return None
            
            # Analyze execution results
            successful = [t for t in traces if t.status == "success"]
            failed = [t for t in traces if t.status == "error"]
            
            success_rate = len(successful) / len(traces) if traces else 0.0
            
            # Get similar successful patterns
            similar_patterns = self.db.query(LearningPattern).filter(
                and_(
                    LearningPattern.pattern_type == PatternType.STRATEGY.value,
                    LearningPattern.success_rate > success_rate
                )
            ).order_by(LearningPattern.success_rate.desc()).limit(5).all()
            
            improvements = {
                "current_success_rate": success_rate,
                "recommended_patterns": [p.to_dict() for p in similar_patterns],
                "suggestions": []
            }
            
            if success_rate < 0.7:
                improvements["suggestions"].append(
                    "Consider breaking down complex steps into smaller, more manageable ones"
                )
            
            if len(failed) > len(successful):
                improvements["suggestions"].append(
                    "Add more validation steps before critical operations"
                )
            
            logger.info(
                f"Generated improvements for plan {plan_id}",
                extra={"plan_id": str(plan_id), "success_rate": success_rate}
            )
            
            return improvements
            
        except Exception as e:
            logger.error(f"Error improving planning strategy: {e}", exc_info=True)
            return None
    
    def evolve_prompts(self, prompt_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """
        Evolve prompts based on successful patterns
        
        Args:
            prompt_id: Optional specific prompt ID
            
        Returns:
            List of evolved prompt suggestions
        """
        try:
            # Get successful prompt patterns
            patterns = self.db.query(LearningPattern).filter(
                LearningPattern.pattern_type == PatternType.PROMPT.value
            ).order_by(LearningPattern.success_rate.desc()).limit(10).all()
            
            evolved_prompts = []
            for pattern in patterns:
                pattern_data = pattern.pattern_data or {}
                keywords = pattern_data.get("keywords", {})
                
                if keywords:
                    evolved_prompts.append({
                        "pattern_id": str(pattern.id),
                        "success_rate": pattern.success_rate,
                        "suggested_keywords": list(keywords.keys())[:10],
                        "usage_count": pattern.usage_count
                    })
            
            logger.info(f"Generated {len(evolved_prompts)} evolved prompt suggestions")
            return evolved_prompts
            
        except Exception as e:
            logger.error(f"Error evolving prompts: {e}", exc_info=True)
            return []
    
    def get_patterns_for_task(
        self,
        task_category: str,
        pattern_type: Optional[PatternType] = None
    ) -> List[LearningPattern]:
        """
        Get learning patterns for a specific task category
        
        Args:
            task_category: Task category
            pattern_type: Optional pattern type filter
            
        Returns:
            List of LearningPattern instances
        """
        try:
            query = self.db.query(LearningPattern).filter(
                LearningPattern.task_category == task_category
            )
            
            if pattern_type:
                query = query.filter(LearningPattern.pattern_type == pattern_type.value)
            
            patterns = query.order_by(LearningPattern.success_rate.desc()).all()
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error getting patterns for task: {e}", exc_info=True)
            return []

