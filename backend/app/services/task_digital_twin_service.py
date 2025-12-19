"""
Task Digital Twin Service
Manages the digital twin of a task - a single JSONB context field storing all task-related data
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.models.task import Task
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class TaskDigitalTwinService:
    """
    Service for managing the digital twin of a task
    
    The digital twin is a single JSONB context field that stores:
    - original_user_request: Original user request/query
    - active_todos: Current ToDo list (from plan steps)
    - historical_todos: Historical ToDo lists (plan versions)
    - artifacts: Generated artifacts (prompts, code, tables, etc.)
    - execution_logs: Execution logs, errors, validation results
    - interaction_history: History of human interactions (approvals, corrections, feedback)
    - planning_decisions: Planning decisions and replanning history
    - metadata: Additional metadata (model used, timestamps, etc.)
    """
    
    def __init__(self, db: Session):
        """
        Initialize Task Digital Twin Service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def initialize_context(self, task: Task, user_request: Optional[str] = None) -> Dict[str, Any]:
        """
        Initialize task context with default structure
        
        Args:
            task: Task to initialize
            user_request: Original user request
            
        Returns:
            Initialized context dictionary
        """
        context = {
            "original_user_request": user_request or task.description,
            "active_todos": [],
            "historical_todos": [],
            "artifacts": [],
            "execution_logs": [],
            "interaction_history": [],
            "planning_decisions": {
                "replanning_history": [],
                "plan_versions": []
            },
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        }
        
        task.update_context(context, merge=False)
        self.db.commit()
        
        logger.debug(f"Initialized context for task {task.id}")
        
        return context
    
    def add_user_request(self, task: Task, user_request: str) -> None:
        """Add original user request to context"""
        context = task.get_context()
        context["original_user_request"] = user_request
        context["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        task.update_context(context, merge=False)
        self.db.commit()
    
    def update_active_todos(self, task: Task, todos: List[Dict[str, Any]]) -> None:
        """
        Update active ToDo list in context
        
        Args:
            task: Task to update
            todos: List of ToDo items (from plan steps)
        """
        context = task.get_context()
        
        # Move current active_todos to historical if they exist
        if context.get("active_todos"):
            if "historical_todos" not in context:
                context["historical_todos"] = []
            context["historical_todos"].append({
                "todos": context["active_todos"],
                "archived_at": datetime.now(timezone.utc).isoformat(),
                "plan_version": context.get("metadata", {}).get("current_plan_version", 0)
            })
        
        context["active_todos"] = todos
        context["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        task.update_context(context, merge=False)
        self.db.commit()
    
    def add_artifact(self, task: Task, artifact: Dict[str, Any]) -> None:
        """
        Add generated artifact to context
        
        Args:
            task: Task to update
            artifact: Artifact data (id, type, name, code/prompt, etc.)
        """
        context = task.get_context()
        
        if "artifacts" not in context:
            context["artifacts"] = []
        
        artifact_entry = {
            "id": artifact.get("id"),
            "type": artifact.get("type"),  # agent, tool, prompt, code, etc.
            "name": artifact.get("name"),
            "description": artifact.get("description"),
            "content": artifact.get("content"),  # code or prompt
            "created_at": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in artifact.items() if k not in ["id", "type", "name", "description", "content"]}
        }
        
        context["artifacts"].append(artifact_entry)
        context["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        task.update_context(context, merge=False)
        self.db.commit()
    
    def add_execution_log(self, task: Task, log_entry: Dict[str, Any]) -> None:
        """
        Add execution log entry to context
        
        Args:
            task: Task to update
            log_entry: Log entry (step_id, status, output, error, timestamp, etc.)
        """
        context = task.get_context()
        
        if "execution_logs" not in context:
            context["execution_logs"] = []
        
        log_entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        context["execution_logs"].append(log_entry)
        context["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        task.update_context(context, merge=False)
        self.db.commit()
    
    def add_interaction(self, task: Task, interaction_type: str, data: Dict[str, Any]) -> None:
        """
        Add human interaction to history
        
        Args:
            task: Task to update
            interaction_type: Type of interaction (approval, correction, feedback, etc.)
            data: Interaction data
        """
        task.add_to_history(interaction_type, data)
        self.db.commit()
    
    def add_planning_decision(self, task: Task, decision_type: str, data: Dict[str, Any]) -> None:
        """
        Add planning decision to context
        
        Args:
            task: Task to update
            decision_type: Type of decision (plan_created, plan_replanned, etc.)
            data: Decision data
        """
        context = task.get_context()
        
        if "planning_decisions" not in context:
            context["planning_decisions"] = {}
        
        if decision_type == "plan_replanned":
            if "replanning_history" not in context["planning_decisions"]:
                context["planning_decisions"]["replanning_history"] = []
            context["planning_decisions"]["replanning_history"].append({
                **data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        elif decision_type == "plan_created":
            if "plan_versions" not in context["planning_decisions"]:
                context["planning_decisions"]["plan_versions"] = []
            context["planning_decisions"]["plan_versions"].append({
                **data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        context["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        task.update_context(context, merge=False)
        self.db.commit()
    
    def get_full_context(self, task: Task) -> Dict[str, Any]:
        """
        Get full task context (digital twin)
        
        Args:
            task: Task to get context for
            
        Returns:
            Full context dictionary
        """
        return task.get_context()
    
    def get_active_todos(self, task: Task) -> List[Dict[str, Any]]:
        """Get active ToDo list from context"""
        context = task.get_context()
        return context.get("active_todos", [])
    
    def get_artifacts(self, task: Task, artifact_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get artifacts from context
        
        Args:
            task: Task to get artifacts for
            artifact_type: Optional filter by artifact type
            
        Returns:
            List of artifacts
        """
        context = task.get_context()
        artifacts = context.get("artifacts", [])
        
        if artifact_type:
            return [a for a in artifacts if a.get("type") == artifact_type]
        
        return artifacts
    
    def get_execution_logs(self, task: Task, step_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get execution logs from context
        
        Args:
            task: Task to get logs for
            step_id: Optional filter by step_id
            
        Returns:
            List of execution log entries
        """
        context = task.get_context()
        logs = context.get("execution_logs", [])
        
        if step_id:
            return [log for log in logs if log.get("step_id") == step_id]
        
        return logs
    
    def get_interaction_history(self, task: Task, interaction_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get interaction history from context
        
        Args:
            task: Task to get history for
            interaction_type: Optional filter by interaction type
            
        Returns:
            List of interaction history entries
        """
        context = task.get_context()
        history = context.get("interaction_history", [])
        
        if interaction_type:
            return [entry for entry in history if entry.get("type") == interaction_type]
        
        return history
    
    def get_planning_decisions(self, task: Task) -> Dict[str, Any]:
        """Get planning decisions from context"""
        context = task.get_context()
        return context.get("planning_decisions", {
            "replanning_history": [],
            "plan_versions": []
        })
    
    def update_metadata(self, task: Task, metadata: Dict[str, Any]) -> None:
        """
        Update metadata in context
        
        Args:
            task: Task to update
            metadata: Metadata to add/update
        """
        context = task.get_context()
        
        if "metadata" not in context:
            context["metadata"] = {}
        
        context["metadata"].update(metadata)
        context["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        task.update_context(context, merge=False)
        self.db.commit()

