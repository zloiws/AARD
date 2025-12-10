"""
Conflict Resolution Service for resolving goal conflicts between agents
"""
from typing import Dict, Any, List, Optional, Set
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import Session

from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes
from app.models.task import Task, TaskStatus
from app.models.agent import Agent
from app.models.plan import Plan

logger = LoggingConfig.get_logger(__name__)


class ConflictType(str, Enum):
    """Types of conflicts between agents"""
    RESOURCE_CONFLICT = "resource_conflict"  # Multiple agents need same resource
    GOAL_CONFLICT = "goal_conflict"  # Conflicting goals/objectives
    PRIORITY_CONFLICT = "priority_conflict"  # Different priority levels
    DEPENDENCY_CONFLICT = "dependency_conflict"  # Circular or blocking dependencies
    TIMING_CONFLICT = "timing_conflict"  # Scheduling conflicts


class ConflictSeverity(str, Enum):
    """Severity levels for conflicts"""
    LOW = "low"  # Can be resolved automatically
    MEDIUM = "medium"  # May require human intervention
    HIGH = "high"  # Requires immediate human attention
    CRITICAL = "critical"  # System cannot proceed without resolution


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts"""
    PRIORITY_BASED = "priority_based"  # Resolve based on task/agent priority
    FIRST_COME_FIRST_SERVED = "first_come_first_served"  # First task wins
    NEGOTIATION = "negotiation"  # Agents negotiate a solution
    HUMAN_INTERVENTION = "human_intervention"  # Escalate to human
    RESOURCE_SHARING = "resource_sharing"  # Share resource if possible
    SEQUENTIAL_EXECUTION = "sequential_execution"  # Execute tasks sequentially
    PARALLEL_EXECUTION = "parallel_execution"  # Execute in parallel if safe


class ConflictResolutionService:
    """
    Service for detecting and resolving conflicts between agent goals and tasks.
    
    Handles:
    - Resource conflicts (multiple agents need same resource)
    - Goal conflicts (conflicting objectives)
    - Priority conflicts (different priority levels)
    - Dependency conflicts (circular or blocking dependencies)
    - Timing conflicts (scheduling issues)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
    
    def detect_conflicts(
        self,
        tasks: List[Task],
        agents: Optional[List[Agent]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between tasks and agents.
        
        Args:
            tasks: List of tasks to check for conflicts
            agents: Optional list of agents (if None, will query from tasks)
            
        Returns:
            List of detected conflicts with details
        """
        with self.tracer.start_as_current_span("conflict_resolution.detect_conflicts") as span:
            add_span_attributes(span=span, task_count=len(tasks))
            
            conflicts = []
            
            # Get active tasks only
            active_tasks = [t for t in tasks if t.status in [
                TaskStatus.PENDING_APPROVAL.value,
                TaskStatus.APPROVED.value,
                TaskStatus.IN_PROGRESS.value
            ]]
            
            if len(active_tasks) < 2:
                return conflicts  # No conflicts possible with < 2 tasks
            
            # 1. Detect resource conflicts
            conflicts.extend(self._detect_resource_conflicts(active_tasks))
            
            # 2. Detect goal conflicts
            conflicts.extend(self._detect_goal_conflicts(active_tasks))
            
            # 3. Detect priority conflicts
            conflicts.extend(self._detect_priority_conflicts(active_tasks))
            
            # 4. Detect dependency conflicts
            conflicts.extend(self._detect_dependency_conflicts(active_tasks))
            
            # 5. Detect timing conflicts
            conflicts.extend(self._detect_timing_conflicts(active_tasks))
            
            logger.info(
                f"Detected {len(conflicts)} conflicts among {len(active_tasks)} tasks",
                extra={"conflict_count": len(conflicts), "task_count": len(active_tasks)}
            )
            
            return conflicts
    
    def _detect_resource_conflicts(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """Detect conflicts where multiple tasks need the same resource"""
        conflicts = []
        
        # Extract resource requirements from task metadata or context
        resource_requirements = {}
        for task in tasks:
            task_resources = self._extract_resource_requirements(task)
            for resource in task_resources:
                if resource not in resource_requirements:
                    resource_requirements[resource] = []
                resource_requirements[resource].append(task)
        
        # Find resources with multiple tasks
        for resource, conflicting_tasks in resource_requirements.items():
            if len(conflicting_tasks) > 1:
                conflicts.append({
                    "type": ConflictType.RESOURCE_CONFLICT.value,
                    "severity": self._calculate_severity(conflicting_tasks),
                    "resource": resource,
                    "conflicting_tasks": [str(t.id) for t in conflicting_tasks],
                    "task_ids": [t.id for t in conflicting_tasks],
                    "description": f"Multiple tasks require resource: {resource}",
                    "detected_at": datetime.now(timezone.utc).isoformat()
                })
        
        return conflicts
    
    def _detect_goal_conflicts(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """Detect conflicts where tasks have conflicting goals"""
        conflicts = []
        
        # Extract goals from task descriptions
        task_goals = {}
        for task in tasks:
            goal_keywords = self._extract_goal_keywords(task.description)
            task_goals[task.id] = goal_keywords
        
        # Check for conflicting goals (e.g., "create" vs "delete", "enable" vs "disable")
        conflict_patterns = [
            (["создать", "create", "добавить", "add"], ["удалить", "delete", "удалить", "remove"]),
            (["включить", "enable", "активировать", "activate"], ["выключить", "disable", "деактивировать", "deactivate"]),
            (["увеличить", "increase", "расширить", "expand"], ["уменьшить", "decrease", "сократить", "reduce"]),
        ]
        
        for task1 in tasks:
            for task2 in tasks:
                if task1.id >= task2.id:  # Avoid duplicates
                    continue
                
                goals1 = task_goals.get(task1.id, [])
                goals2 = task_goals.get(task2.id, [])
                
                for pattern_group1, pattern_group2 in conflict_patterns:
                    if any(g in goals1 for g in pattern_group1) and any(g in goals2 for g in pattern_group2):
                        conflicts.append({
                            "type": ConflictType.GOAL_CONFLICT.value,
                            "severity": ConflictSeverity.HIGH.value,
                            "conflicting_tasks": [str(task1.id), str(task2.id)],
                            "task_ids": [task1.id, task2.id],
                            "conflict_description": f"Task {task1.id} wants to {pattern_group1[0]}, but task {task2.id} wants to {pattern_group2[0]}",
                            "detected_at": datetime.now(timezone.utc).isoformat()
                        })
        
        return conflicts
    
    def _detect_priority_conflicts(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """Detect conflicts where tasks have different priorities but similar goals"""
        conflicts = []
        
        # Group tasks by similarity
        for task1 in tasks:
            for task2 in tasks:
                if task1.id >= task2.id:
                    continue
                
                # Check if tasks are similar (same domain/object)
                similarity = self._calculate_task_similarity(task1, task2)
                if similarity > 0.7:  # High similarity threshold
                    # Check if priorities differ significantly
                    priority1 = getattr(task1, 'priority', 5)  # Default priority
                    priority2 = getattr(task2, 'priority', 5)
                    
                    if abs(priority1 - priority2) >= 3:  # Significant priority difference
                        conflicts.append({
                            "type": ConflictType.PRIORITY_CONFLICT.value,
                            "severity": ConflictSeverity.MEDIUM.value,
                            "conflicting_tasks": [str(task1.id), str(task2.id)],
                            "task_ids": [task1.id, task2.id],
                            "priority_difference": abs(priority1 - priority2),
                            "similarity": similarity,
                            "description": f"Similar tasks with different priorities: {priority1} vs {priority2}",
                            "detected_at": datetime.now(timezone.utc).isoformat()
                        })
        
        return conflicts
    
    def _detect_dependency_conflicts(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """Detect circular or blocking dependencies"""
        conflicts = []
        
        # Build dependency graph
        dependencies = {}
        for task in tasks:
            task_deps = self._extract_dependencies(task)
            dependencies[task.id] = task_deps
        
        # Check for circular dependencies
        for task_id, deps in dependencies.items():
            for dep_id in deps:
                if dep_id in dependencies and task_id in dependencies.get(dep_id, []):
                    conflicts.append({
                        "type": ConflictType.DEPENDENCY_CONFLICT.value,
                        "severity": ConflictSeverity.HIGH.value,
                        "conflicting_tasks": [str(task_id), str(dep_id)],
                        "task_ids": [task_id, dep_id],
                        "description": f"Circular dependency detected between tasks {task_id} and {dep_id}",
                        "detected_at": datetime.now(timezone.utc).isoformat()
                    })
        
        return conflicts
    
    def _detect_timing_conflicts(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """Detect scheduling/timing conflicts"""
        conflicts = []
        
        # Check for tasks that need to run at the same time but conflict
        for task1 in tasks:
            for task2 in tasks:
                if task1.id >= task2.id:
                    continue
                
                # Check if tasks have timing constraints
                timing1 = self._extract_timing_constraints(task1)
                timing2 = self._extract_timing_constraints(task2)
                
                if timing1 and timing2:
                    # Check for overlap
                    if self._timing_overlaps(timing1, timing2):
                        # Check if they conflict (same resource, etc.)
                        resources1 = set(self._extract_resource_requirements(task1))
                        resources2 = set(self._extract_resource_requirements(task2))
                        
                        if resources1 & resources2:  # Intersection
                            conflicts.append({
                                "type": ConflictType.TIMING_CONFLICT.value,
                                "severity": ConflictSeverity.MEDIUM.value,
                                "conflicting_tasks": [str(task1.id), str(task2.id)],
                                "task_ids": [task1.id, task2.id],
                                "description": f"Tasks scheduled at overlapping times with shared resources",
                                "detected_at": datetime.now(timezone.utc).isoformat()
                            })
        
        return conflicts
    
    def resolve_conflict(
        self,
        conflict: Dict[str, Any],
        strategy: Optional[ConflictResolutionStrategy] = None
    ) -> Dict[str, Any]:
        """
        Resolve a conflict using the specified strategy.
        
        Args:
            conflict: Conflict dictionary from detect_conflicts()
            strategy: Resolution strategy (if None, will auto-select)
            
        Returns:
            Resolution result with actions to take
        """
        with self.tracer.start_as_current_span("conflict_resolution.resolve_conflict") as span:
            add_span_attributes(
                span=span,
                conflict_type=conflict.get("type"),
                severity=conflict.get("severity")
            )
            
            if strategy is None:
                strategy = self._select_resolution_strategy(conflict)
            
            logger.info(
                f"Resolving conflict {conflict.get('type')} using strategy {strategy.value}",
                extra={"conflict_type": conflict.get("type"), "strategy": strategy.value}
            )
            
            if strategy == ConflictResolutionStrategy.PRIORITY_BASED:
                return self._resolve_by_priority(conflict)
            elif strategy == ConflictResolutionStrategy.FIRST_COME_FIRST_SERVED:
                return self._resolve_by_first_come(conflict)
            elif strategy == ConflictResolutionStrategy.NEGOTIATION:
                return self._resolve_by_negotiation(conflict)
            elif strategy == ConflictResolutionStrategy.HUMAN_INTERVENTION:
                return self._resolve_by_human_intervention(conflict)
            elif strategy == ConflictResolutionStrategy.RESOURCE_SHARING:
                return self._resolve_by_resource_sharing(conflict)
            elif strategy == ConflictResolutionStrategy.SEQUENTIAL_EXECUTION:
                return self._resolve_by_sequential_execution(conflict)
            elif strategy == ConflictResolutionStrategy.PARALLEL_EXECUTION:
                return self._resolve_by_parallel_execution(conflict)
            else:
                # Default: escalate to human
                return self._resolve_by_human_intervention(conflict)
    
    def _select_resolution_strategy(self, conflict: Dict[str, Any]) -> ConflictResolutionStrategy:
        """Automatically select the best resolution strategy for a conflict"""
        conflict_type = conflict.get("type")
        severity = conflict.get("severity")
        
        # Critical conflicts always require human intervention
        if severity == ConflictSeverity.CRITICAL.value:
            return ConflictResolutionStrategy.HUMAN_INTERVENTION
        
        # Resource conflicts can often be resolved by sharing or sequencing
        if conflict_type == ConflictType.RESOURCE_CONFLICT.value:
            # Check if resource can be shared
            resource = conflict.get("resource", "")
            if self._can_resource_be_shared(resource):
                return ConflictResolutionStrategy.RESOURCE_SHARING
            else:
                return ConflictResolutionStrategy.SEQUENTIAL_EXECUTION
        
        # Goal conflicts require negotiation or human intervention
        if conflict_type == ConflictType.GOAL_CONFLICT.value:
            if severity == ConflictSeverity.HIGH.value:
                return ConflictResolutionStrategy.HUMAN_INTERVENTION
            else:
                return ConflictResolutionStrategy.NEGOTIATION
        
        # Priority conflicts can be resolved by priority
        if conflict_type == ConflictType.PRIORITY_CONFLICT.value:
            return ConflictResolutionStrategy.PRIORITY_BASED
        
        # Dependency conflicts need sequential execution or human intervention
        if conflict_type == ConflictType.DEPENDENCY_CONFLICT.value:
            return ConflictResolutionStrategy.SEQUENTIAL_EXECUTION
        
        # Timing conflicts can be resolved by sequencing or parallel execution
        if conflict_type == ConflictType.TIMING_CONFLICT.value:
            # Check if tasks can run in parallel safely
            if self._can_tasks_run_in_parallel(conflict.get("task_ids", [])):
                return ConflictResolutionStrategy.PARALLEL_EXECUTION
            else:
                return ConflictResolutionStrategy.SEQUENTIAL_EXECUTION
        
        # Default: human intervention
        return ConflictResolutionStrategy.HUMAN_INTERVENTION
    
    def _resolve_by_priority(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict by prioritizing higher priority tasks"""
        task_ids = conflict.get("task_ids", [])
        tasks = [self.db.query(Task).filter(Task.id == tid).first() for tid in task_ids]
        tasks = [t for t in tasks if t is not None]
        
        # Sort by priority (higher priority first)
        tasks.sort(key=lambda t: getattr(t, 'priority', 5), reverse=True)
        
        winner = tasks[0] if tasks else None
        losers = tasks[1:] if len(tasks) > 1 else []
        
        actions = []
        if winner:
            actions.append({
                "action": "proceed",
                "task_id": str(winner.id),
                "reason": "Higher priority"
            })
        
        for loser in losers:
            actions.append({
                "action": "delay",
                "task_id": str(loser.id),
                "reason": "Lower priority",
                "delay_until": "After higher priority tasks complete"
            })
        
        return {
            "resolved": True,
            "strategy": ConflictResolutionStrategy.PRIORITY_BASED.value,
            "actions": actions,
            "resolution_time": datetime.now(timezone.utc).isoformat()
        }
    
    def _resolve_by_first_come(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict by first-come-first-served"""
        task_ids = conflict.get("task_ids", [])
        tasks = [self.db.query(Task).filter(Task.id == tid).first() for tid in task_ids]
        tasks = [t for t in tasks if t is not None]
        
        # Sort by creation time
        tasks.sort(key=lambda t: t.created_at)
        
        winner = tasks[0] if tasks else None
        losers = tasks[1:] if len(tasks) > 1 else []
        
        actions = []
        if winner:
            actions.append({
                "action": "proceed",
                "task_id": str(winner.id),
                "reason": "First created"
            })
        
        for loser in losers:
            actions.append({
                "action": "delay",
                "task_id": str(loser.id),
                "reason": "Created later",
                "delay_until": "After first task completes"
            })
        
        return {
            "resolved": True,
            "strategy": ConflictResolutionStrategy.FIRST_COME_FIRST_SERVED.value,
            "actions": actions,
            "resolution_time": datetime.now(timezone.utc).isoformat()
        }
    
    def _resolve_by_negotiation(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict through agent negotiation (placeholder for future implementation)"""
        # This would involve agents communicating and finding a compromise
        # For now, fall back to priority-based resolution
        logger.info("Negotiation strategy not fully implemented, falling back to priority-based")
        return self._resolve_by_priority(conflict)
    
    def _resolve_by_human_intervention(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Escalate conflict to human for resolution"""
        return {
            "resolved": False,
            "strategy": ConflictResolutionStrategy.HUMAN_INTERVENTION.value,
            "requires_human": True,
            "conflict": conflict,
            "message": "Conflict requires human intervention",
            "resolution_time": datetime.now(timezone.utc).isoformat()
        }
    
    def _resolve_by_resource_sharing(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict by sharing the resource"""
        task_ids = conflict.get("task_ids", [])
        
        actions = []
        for task_id in task_ids:
            actions.append({
                "action": "proceed",
                "task_id": str(task_id),
                "reason": "Resource can be shared",
                "resource_sharing": True
            })
        
        return {
            "resolved": True,
            "strategy": ConflictResolutionStrategy.RESOURCE_SHARING.value,
            "actions": actions,
            "resolution_time": datetime.now(timezone.utc).isoformat()
        }
    
    def _resolve_by_sequential_execution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict by executing tasks sequentially"""
        task_ids = conflict.get("task_ids", [])
        tasks = [self.db.query(Task).filter(Task.id == tid).first() for tid in task_ids]
        tasks = [t for t in tasks if t is not None]
        
        # Sort by priority and creation time
        tasks.sort(key=lambda t: (getattr(t, 'priority', 5), t.created_at), reverse=True)
        
        actions = []
        for i, task in enumerate(tasks):
            if i == 0:
                actions.append({
                    "action": "proceed",
                    "task_id": str(task.id),
                    "reason": "First in sequence"
                })
            else:
                actions.append({
                    "action": "delay",
                    "task_id": str(task.id),
                    "reason": "Sequential execution",
                    "wait_for": str(tasks[i-1].id)
                })
        
        return {
            "resolved": True,
            "strategy": ConflictResolutionStrategy.SEQUENTIAL_EXECUTION.value,
            "actions": actions,
            "resolution_time": datetime.now(timezone.utc).isoformat()
        }
    
    def _resolve_by_parallel_execution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict by allowing parallel execution"""
        task_ids = conflict.get("task_ids", [])
        
        actions = []
        for task_id in task_ids:
            actions.append({
                "action": "proceed",
                "task_id": str(task_id),
                "reason": "Safe to execute in parallel"
            })
        
        return {
            "resolved": True,
            "strategy": ConflictResolutionStrategy.PARALLEL_EXECUTION.value,
            "actions": actions,
            "resolution_time": datetime.now(timezone.utc).isoformat()
        }
    
    # Helper methods
    
    def _extract_resource_requirements(self, task: Task) -> List[str]:
        """Extract resource requirements from task"""
        resources = []
        
        # Check task context/metadata
        context = task.get_context() if hasattr(task, 'get_context') else {}
        metadata = context.get("metadata", {})
        
        # Extract from metadata
        if "required_resources" in metadata:
            resources.extend(metadata["required_resources"])
        
        # Extract from description (simple keyword matching)
        description_lower = task.description.lower()
        resource_keywords = {
            "database": ["база данных", "database", "db", "postgres", "mysql"],
            "api": ["api", "endpoint", "сервис"],
            "file": ["файл", "file", "директория", "directory"],
            "network": ["сеть", "network", "http", "https"],
        }
        
        for resource, keywords in resource_keywords.items():
            if any(kw in description_lower for kw in keywords):
                resources.append(resource)
        
        return list(set(resources))  # Remove duplicates
    
    def _extract_goal_keywords(self, description: str) -> List[str]:
        """Extract goal-related keywords from task description"""
        description_lower = description.lower()
        keywords = []
        
        goal_verbs = [
            "создать", "create", "добавить", "add", "удалить", "delete",
            "изменить", "change", "обновить", "update", "включить", "enable",
            "выключить", "disable", "увеличить", "increase", "уменьшить", "decrease"
        ]
        
        for verb in goal_verbs:
            if verb in description_lower:
                keywords.append(verb)
        
        return keywords
    
    def _calculate_task_similarity(self, task1: Task, task2: Task) -> float:
        """Calculate similarity between two tasks (0.0 to 1.0)"""
        # Simple similarity based on description overlap
        desc1_words = set(task1.description.lower().split())
        desc2_words = set(task2.description.lower().split())
        
        if not desc1_words or not desc2_words:
            return 0.0
        
        intersection = desc1_words & desc2_words
        union = desc1_words | desc2_words
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _extract_dependencies(self, task: Task) -> List[UUID]:
        """Extract task dependencies"""
        dependencies = []
        
        context = task.get_context() if hasattr(task, 'get_context') else {}
        metadata = context.get("metadata", {})
        
        if "depends_on" in metadata:
            deps = metadata["depends_on"]
            if isinstance(deps, list):
                for dep in deps:
                    try:
                        dependencies.append(UUID(dep) if isinstance(dep, str) else dep)
                    except (ValueError, TypeError):
                        pass
        
        return dependencies
    
    def _extract_timing_constraints(self, task: Task) -> Optional[Dict[str, Any]]:
        """Extract timing constraints from task"""
        context = task.get_context() if hasattr(task, 'get_context') else {}
        metadata = context.get("metadata", {})
        
        if "scheduled_at" in metadata or "deadline" in metadata:
            return {
                "scheduled_at": metadata.get("scheduled_at"),
                "deadline": metadata.get("deadline"),
                "duration_estimate": metadata.get("duration_estimate")
            }
        
        return None
    
    def _timing_overlaps(self, timing1: Dict[str, Any], timing2: Dict[str, Any]) -> bool:
        """Check if two timing constraints overlap"""
        # Simple overlap check (can be enhanced)
        scheduled1 = timing1.get("scheduled_at")
        scheduled2 = timing2.get("scheduled_at")
        
        if scheduled1 and scheduled2:
            # If both have scheduled times, check if they're close
            try:
                from dateutil.parser import parse
                dt1 = parse(scheduled1)
                dt2 = parse(scheduled2)
                duration1 = timing1.get("duration_estimate", 3600)  # Default 1 hour
                duration2 = timing2.get("duration_estimate", 3600)
                
                # Check if time ranges overlap
                end1 = dt1.timestamp() + duration1
                end2 = dt2.timestamp() + duration2
                
                return not (end1 < dt2.timestamp() or end2 < dt1.timestamp())
            except:
                pass
        
        return False
    
    def _calculate_severity(self, tasks: List[Task]) -> str:
        """Calculate conflict severity based on tasks"""
        # Check task priorities and statuses
        high_priority_count = sum(1 for t in tasks if getattr(t, 'priority', 5) >= 8)
        in_progress_count = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS.value)
        
        if high_priority_count >= 2 or in_progress_count >= 2:
            return ConflictSeverity.HIGH.value
        elif high_priority_count >= 1:
            return ConflictSeverity.MEDIUM.value
        else:
            return ConflictSeverity.LOW.value
    
    def _can_resource_be_shared(self, resource: str) -> bool:
        """Check if a resource can be shared between tasks"""
        # Some resources can be shared (read-only), others cannot (write operations)
        shareable_resources = ["database", "api", "network"]  # Read operations
        non_shareable = ["file"]  # Write operations
        
        resource_lower = resource.lower()
        if any(ns in resource_lower for ns in non_shareable):
            return False
        if any(sr in resource_lower for sr in shareable_resources):
            return True
        
        # Default: assume not shareable for safety
        return False
    
    def _can_tasks_run_in_parallel(self, task_ids: List[UUID]) -> bool:
        """Check if tasks can safely run in parallel"""
        tasks = [self.db.query(Task).filter(Task.id == tid).first() for tid in task_ids]
        tasks = [t for t in tasks if t is not None]
        
        # Check if tasks have conflicting write operations
        for task1 in tasks:
            for task2 in tasks:
                if task1.id >= task2.id:
                    continue
                
                resources1 = set(self._extract_resource_requirements(task1))
                resources2 = set(self._extract_resource_requirements(task2))
                
                # If both tasks write to same resource, cannot run in parallel
                if resources1 & resources2:
                    # Check if operations are read-only
                    desc1 = task1.description.lower()
                    desc2 = task2.description.lower()
                    
                    write_keywords = ["write", "create", "delete", "update", "modify", "изменить", "создать", "удалить"]
                    if any(kw in desc1 for kw in write_keywords) and any(kw in desc2 for kw in write_keywords):
                        return False
        
        return True

