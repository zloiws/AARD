"""
Quota Management Service for managing resource quotas and limits
"""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.tracing import add_span_attributes, get_tracer
from app.models.agent import Agent
from app.models.task import Task, TaskStatus
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class ResourceType(str, Enum):
    """Types of resources that can be quota-limited"""
    LLM_REQUESTS = "llm_requests"  # Number of LLM API calls
    LLM_TOKENS = "llm_tokens"  # Number of tokens processed
    DATABASE_QUERIES = "database_queries"  # Number of database queries
    FILE_OPERATIONS = "file_operations"  # Number of file operations
    NETWORK_REQUESTS = "network_requests"  # Number of network requests
    EXECUTION_TIME = "execution_time"  # Total execution time (seconds)
    MEMORY_USAGE = "memory_usage"  # Memory usage (MB)
    STORAGE_SPACE = "storage_space"  # Storage space (MB)
    CONCURRENT_TASKS = "concurrent_tasks"  # Number of concurrent tasks
    AGENT_CREATIONS = "agent_creations"  # Number of agent creations
    TOOL_CREATIONS = "tool_creations"  # Number of tool creations


class QuotaPeriod(str, Enum):
    """Time periods for quota limits"""
    PER_REQUEST = "per_request"  # Per single request
    PER_MINUTE = "per_minute"  # Per minute
    PER_HOUR = "per_hour"  # Per hour
    PER_DAY = "per_day"  # Per day
    PER_WEEK = "per_week"  # Per week
    PER_MONTH = "per_month"  # Per month
    TOTAL = "total"  # Total limit (no time period)


class QuotaStatus(str, Enum):
    """Status of quota check"""
    WITHIN_LIMIT = "within_limit"  # Within quota limits
    APPROACHING_LIMIT = "approaching_limit"  # Close to limit (80-95%)
    AT_LIMIT = "at_limit"  # At limit (95-100%)
    EXCEEDED = "exceeded"  # Exceeded limit
    UNKNOWN = "unknown"  # Cannot determine status


class QuotaManagementService:
    """
    Service for managing resource quotas and limits.
    
    Handles:
    - Quota definition and configuration
    - Quota checking before task execution
    - Usage tracking
    - Limit notifications
    - Quota enforcement
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
        
        # Default quotas (can be overridden via configuration)
        self.default_quotas: Dict[ResourceType, Dict[str, Any]] = {
            ResourceType.LLM_REQUESTS: {
                "limit": 1000,
                "period": QuotaPeriod.PER_DAY.value,
                "warning_threshold": 0.8  # Warn at 80%
            },
            ResourceType.LLM_TOKENS: {
                "limit": 1000000,  # 1M tokens
                "period": QuotaPeriod.PER_DAY.value,
                "warning_threshold": 0.8
            },
            ResourceType.DATABASE_QUERIES: {
                "limit": 10000,
                "period": QuotaPeriod.PER_DAY.value,
                "warning_threshold": 0.8
            },
            ResourceType.FILE_OPERATIONS: {
                "limit": 5000,
                "period": QuotaPeriod.PER_DAY.value,
                "warning_threshold": 0.8
            },
            ResourceType.NETWORK_REQUESTS: {
                "limit": 2000,
                "period": QuotaPeriod.PER_DAY.value,
                "warning_threshold": 0.8
            },
            ResourceType.EXECUTION_TIME: {
                "limit": 3600,  # 1 hour in seconds
                "period": QuotaPeriod.PER_DAY.value,
                "warning_threshold": 0.8
            },
            ResourceType.MEMORY_USAGE: {
                "limit": 2048,  # 2GB in MB
                "period": QuotaPeriod.PER_DAY.value,
                "warning_threshold": 0.8
            },
            ResourceType.CONCURRENT_TASKS: {
                "limit": 10,
                "period": QuotaPeriod.PER_REQUEST.value,
                "warning_threshold": 0.8
            },
            ResourceType.AGENT_CREATIONS: {
                "limit": 50,
                "period": QuotaPeriod.PER_MONTH.value,
                "warning_threshold": 0.8
            },
            ResourceType.TOOL_CREATIONS: {
                "limit": 100,
                "period": QuotaPeriod.PER_MONTH.value,
                "warning_threshold": 0.8
            }
        }
        
        # Usage tracking (in-memory, can be moved to database for persistence)
        self.usage_tracking: Dict[str, Dict[str, Any]] = {}
    
    def check_quota(
        self,
        resource_type: ResourceType,
        requested_amount: float = 1.0,
        user_id: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Check if quota allows the requested resource usage.
        
        Args:
            resource_type: Type of resource
            requested_amount: Amount of resource requested
            user_id: Optional user ID for user-specific quotas
            agent_id: Optional agent ID for agent-specific quotas
            task_id: Optional task ID for task-specific quotas
            
        Returns:
            Dictionary with quota check results
        """
        with self.tracer.start_as_current_span("quota.check") as span:
            add_span_attributes(
                span=span,
                resource_type=resource_type.value,
                requested_amount=requested_amount
            )
            
            # Get quota configuration
            quota_config = self._get_quota_config(resource_type, user_id, agent_id)
            
            if not quota_config:
                # No quota configured - allow
                return {
                    "allowed": True,
                    "status": QuotaStatus.UNKNOWN.value,
                    "message": "No quota configured for this resource",
                    "quota_limit": None,
                    "current_usage": None,
                    "remaining": None
                }
            
            limit = quota_config["limit"]
            period = quota_config.get("period", QuotaPeriod.PER_DAY.value)
            warning_threshold = quota_config.get("warning_threshold", 0.8)
            
            # Get current usage
            current_usage = self._get_current_usage(resource_type, period, user_id, agent_id)
            
            # Calculate if request would exceed limit
            projected_usage = current_usage + requested_amount
            usage_percentage = (projected_usage / limit) if limit > 0 else 0.0
            
            # Determine status
            if projected_usage > limit:
                status = QuotaStatus.EXCEEDED.value
                allowed = False
            elif usage_percentage >= 0.95:
                status = QuotaStatus.AT_LIMIT.value
                allowed = True  # Still allow, but warn
            elif usage_percentage >= warning_threshold:
                status = QuotaStatus.APPROACHING_LIMIT.value
                allowed = True
            else:
                status = QuotaStatus.WITHIN_LIMIT.value
                allowed = True
            
            remaining = max(0, limit - projected_usage)
            
            result = {
                "allowed": allowed,
                "status": status,
                "quota_limit": limit,
                "current_usage": current_usage,
                "requested_amount": requested_amount,
                "projected_usage": projected_usage,
                "remaining": remaining,
                "usage_percentage": usage_percentage,
                "period": period,
                "message": self._generate_status_message(status, resource_type, remaining, limit)
            }
            
            # Log quota check
            logger.info(
                f"Quota check for {resource_type.value}: {status}",
                extra={
                    "resource_type": resource_type.value,
                    "status": status,
                    "allowed": allowed,
                    "current_usage": current_usage,
                    "limit": limit,
                    "user_id": user_id,
                    "agent_id": str(agent_id) if agent_id else None
                }
            )
            
            return result
    
    def record_usage(
        self,
        resource_type: ResourceType,
        amount: float,
        user_id: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None
    ) -> None:
        """
        Record resource usage for quota tracking.
        
        Args:
            resource_type: Type of resource
            amount: Amount of resource used
            user_id: Optional user ID
            agent_id: Optional agent ID
            task_id: Optional task ID
        """
        with self.tracer.start_as_current_span("quota.record_usage") as span:
            add_span_attributes(
                span=span,
                resource_type=resource_type.value,
                amount=amount
            )
            
            # Create usage key
            key = self._create_usage_key(resource_type, user_id, agent_id)
            
            # Initialize tracking if needed
            if key not in self.usage_tracking:
                self.usage_tracking[key] = {
                    "total": 0.0,
                    "periods": {}
                }
            
            # Record usage
            self.usage_tracking[key]["total"] += amount
            
            # Record by period
            now = datetime.now(timezone.utc)
            period_key = self._get_period_key(resource_type, now)
            
            if period_key not in self.usage_tracking[key]["periods"]:
                self.usage_tracking[key]["periods"][period_key] = {
                    "amount": 0.0,
                    "start_time": now.isoformat(),
                    "count": 0
                }
            
            self.usage_tracking[key]["periods"][period_key]["amount"] += amount
            self.usage_tracking[key]["periods"][period_key]["count"] += 1
            
            logger.debug(
                f"Recorded usage for {resource_type.value}: {amount}",
                extra={
                    "resource_type": resource_type.value,
                    "amount": amount,
                    "total": self.usage_tracking[key]["total"],
                    "user_id": user_id,
                    "agent_id": str(agent_id) if agent_id else None
                }
            )
    
    def check_task_quota(
        self,
        task: Task,
        estimated_resources: Optional[Dict[ResourceType, float]] = None
    ) -> Dict[str, Any]:
        """
        Check quotas for all resources required by a task.
        
        Args:
            task: Task to check quotas for
            estimated_resources: Optional estimated resource requirements
            
        Returns:
            Dictionary with quota check results for all resources
        """
        with self.tracer.start_as_current_span("quota.check_task") as span:
            add_span_attributes(span=span, task_id=str(task.id))
            
            if estimated_resources is None:
                # Estimate resources based on task description
                estimated_resources = self._estimate_task_resources(task)
            
            results = {}
            all_allowed = True
            warnings = []
            
            for resource_type, amount in estimated_resources.items():
                check_result = self.check_quota(
                    resource_type=resource_type,
                    requested_amount=amount,
                    user_id=task.created_by,
                    task_id=task.id
                )
                
                results[resource_type.value] = check_result
                
                if not check_result["allowed"]:
                    all_allowed = False
                
                if check_result["status"] in [
                    QuotaStatus.APPROACHING_LIMIT.value,
                    QuotaStatus.AT_LIMIT.value
                ]:
                    warnings.append(check_result["message"])
            
            return {
                "task_id": str(task.id),
                "all_allowed": all_allowed,
                "results": results,
                "warnings": warnings,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    
    def get_quota_status(
        self,
        resource_type: ResourceType,
        user_id: Optional[str] = None,
        agent_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get current quota status for a resource type.
        
        Args:
            resource_type: Type of resource
            user_id: Optional user ID
            agent_id: Optional agent ID
            
        Returns:
            Dictionary with current quota status
        """
        quota_config = self._get_quota_config(resource_type, user_id, agent_id)
        
        if not quota_config:
            return {
                "resource_type": resource_type.value,
                "quota_configured": False,
                "message": "No quota configured for this resource"
            }
        
        limit = quota_config["limit"]
        period = quota_config.get("period", QuotaPeriod.PER_DAY.value)
        current_usage = self._get_current_usage(resource_type, period, user_id, agent_id)
        usage_percentage = (current_usage / limit) if limit > 0 else 0.0
        remaining = max(0, limit - current_usage)
        
        # Determine status
        if usage_percentage >= 1.0:
            status = QuotaStatus.EXCEEDED.value
        elif usage_percentage >= 0.95:
            status = QuotaStatus.AT_LIMIT.value
        elif usage_percentage >= quota_config.get("warning_threshold", 0.8):
            status = QuotaStatus.APPROACHING_LIMIT.value
        else:
            status = QuotaStatus.WITHIN_LIMIT.value
        
        return {
            "resource_type": resource_type.value,
            "quota_configured": True,
            "limit": limit,
            "current_usage": current_usage,
            "remaining": remaining,
            "usage_percentage": usage_percentage,
            "period": period,
            "status": status,
            "message": self._generate_status_message(status, resource_type, remaining, limit)
        }
    
    def get_all_quotas_status(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get quota status for all resource types.
        
        Args:
            user_id: Optional user ID
            agent_id: Optional agent ID
            
        Returns:
            Dictionary with quota status for all resources
        """
        all_statuses = {}
        
        for resource_type in ResourceType:
            all_statuses[resource_type.value] = self.get_quota_status(
                resource_type, user_id, agent_id
            )
        
        return {
            "user_id": user_id,
            "agent_id": str(agent_id) if agent_id else None,
            "quotas": all_statuses,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    # Helper methods
    
    def _get_quota_config(
        self,
        resource_type: ResourceType,
        user_id: Optional[str] = None,
        agent_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """Get quota configuration for a resource type"""
        # Check for agent-specific quotas
        if agent_id:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                # Check agent-specific limits
                if resource_type == ResourceType.CONCURRENT_TASKS:
                    max_concurrent = getattr(agent, 'max_concurrent_tasks', None)
                    if max_concurrent:
                        return {
                            "limit": max_concurrent,
                            "period": QuotaPeriod.PER_REQUEST.value,
                            "warning_threshold": 0.8
                        }
        
        # Use default quotas
        return self.default_quotas.get(resource_type)
    
    def _get_current_usage(
        self,
        resource_type: ResourceType,
        period: str,
        user_id: Optional[str] = None,
        agent_id: Optional[UUID] = None
    ) -> float:
        """Get current usage for a resource type and period"""
        key = self._create_usage_key(resource_type, user_id, agent_id)
        
        if key not in self.usage_tracking:
            return 0.0
        
        # For per-request quotas, check current active tasks
        if period == QuotaPeriod.PER_REQUEST.value:
            if resource_type == ResourceType.CONCURRENT_TASKS:
                # Count active tasks
                query = self.db.query(Task).filter(
                    Task.status == TaskStatus.IN_PROGRESS.value
                )
                if agent_id:
                    # Filter by agent if specified
                    # Note: This would require a task-agent relationship
                    pass
                return float(query.count())
            return 0.0
        
        # For time-based quotas, get usage for current period
        now = datetime.now(timezone.utc)
        period_key = self._get_period_key(resource_type, now, period)
        
        if period_key in self.usage_tracking[key]["periods"]:
            return self.usage_tracking[key]["periods"][period_key]["amount"]
        
        return 0.0
    
    def _create_usage_key(
        self,
        resource_type: ResourceType,
        user_id: Optional[str] = None,
        agent_id: Optional[UUID] = None
    ) -> str:
        """Create a key for usage tracking"""
        parts = [resource_type.value]
        if user_id:
            parts.append(f"user:{user_id}")
        if agent_id:
            parts.append(f"agent:{agent_id}")
        return ":".join(parts)
    
    def _get_period_key(
        self,
        resource_type: ResourceType,
        timestamp: datetime,
        period: Optional[str] = None
    ) -> str:
        """Get period key for usage tracking"""
        if period is None:
            quota_config = self._get_quota_config(resource_type)
            period = quota_config.get("period", QuotaPeriod.PER_DAY.value) if quota_config else QuotaPeriod.PER_DAY.value
        
        if period == QuotaPeriod.PER_MINUTE.value:
            return timestamp.strftime("%Y-%m-%d-%H-%M")
        elif period == QuotaPeriod.PER_HOUR.value:
            return timestamp.strftime("%Y-%m-%d-%H")
        elif period == QuotaPeriod.PER_DAY.value:
            return timestamp.strftime("%Y-%m-%d")
        elif period == QuotaPeriod.PER_WEEK.value:
            return timestamp.strftime("%Y-W%W")
        elif period == QuotaPeriod.PER_MONTH.value:
            return timestamp.strftime("%Y-%m")
        else:
            return "total"
    
    def _estimate_task_resources(self, task: Task) -> Dict[ResourceType, float]:
        """Estimate resource requirements for a task"""
        estimates = {}
        description_lower = task.description.lower()
        
        # Estimate LLM requests (based on task complexity)
        if len(task.description.split()) > 50:
            estimates[ResourceType.LLM_REQUESTS] = 10.0
        elif len(task.description.split()) > 20:
            estimates[ResourceType.LLM_REQUESTS] = 5.0
        else:
            estimates[ResourceType.LLM_REQUESTS] = 2.0
        
        # Estimate tokens (rough estimate: 1 request = 1000 tokens)
        estimates[ResourceType.LLM_TOKENS] = estimates[ResourceType.LLM_REQUESTS] * 1000
        
        # Estimate database queries
        if any(word in description_lower for word in ["найти", "find", "получить", "get", "список", "list"]):
            estimates[ResourceType.DATABASE_QUERIES] = 5.0
        else:
            estimates[ResourceType.DATABASE_QUERIES] = 2.0
        
        # Estimate file operations
        if any(word in description_lower for word in ["файл", "file", "директория", "directory"]):
            estimates[ResourceType.FILE_OPERATIONS] = 10.0
        else:
            estimates[ResourceType.FILE_OPERATIONS] = 0.0
        
        # Estimate network requests
        if any(word in description_lower for word in ["api", "запрос", "request", "http", "сеть", "network"]):
            estimates[ResourceType.NETWORK_REQUESTS] = 5.0
        else:
            estimates[ResourceType.NETWORK_REQUESTS] = 0.0
        
        # Estimate execution time (in seconds)
        if any(word in description_lower for word in ["сложн", "complex", "больш", "large", "много", "many"]):
            estimates[ResourceType.EXECUTION_TIME] = 300.0  # 5 minutes
        else:
            estimates[ResourceType.EXECUTION_TIME] = 60.0  # 1 minute
        
        # Concurrent tasks (always 1 for a single task)
        estimates[ResourceType.CONCURRENT_TASKS] = 1.0
        
        return estimates
    
    def _generate_status_message(
        self,
        status: str,
        resource_type: ResourceType,
        remaining: float,
        limit: float
    ) -> str:
        """Generate human-readable status message"""
        resource_name = resource_type.value.replace("_", " ").title()
        
        if status == QuotaStatus.EXCEEDED.value:
            return f"Quota exceeded for {resource_name}. Limit: {limit}, cannot proceed."
        elif status == QuotaStatus.AT_LIMIT.value:
            return f"Quota at limit for {resource_name}. Remaining: {remaining:.2f}/{limit}"
        elif status == QuotaStatus.APPROACHING_LIMIT.value:
            return f"Quota approaching limit for {resource_name}. Remaining: {remaining:.2f}/{limit}"
        else:
            return f"Quota OK for {resource_name}. Remaining: {remaining:.2f}/{limit}"

