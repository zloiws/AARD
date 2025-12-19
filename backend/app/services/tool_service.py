"""
Tool Service for managing tools lifecycle
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.tracing import add_span_attributes, get_tracer
from app.models.tool import Tool, ToolCategory, ToolStatus
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class ToolService:
    """Service for managing tools lifecycle"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
    
    def create_tool(
        self,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        code: Optional[str] = None,
        entry_point: Optional[str] = None,
        language: str = "python",
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[str]] = None,
        requirements: Optional[str] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> Tool:
        """
        Create a new tool
        
        Args:
            name: Tool name (must be unique)
            description: Tool description
            category: Tool category
            code: Tool code (Python function)
            entry_point: Function name to call (default: "execute")
            language: Programming language (default: "python")
            input_schema: JSON Schema for input parameters
            output_schema: JSON Schema for output
            parameters: Simplified parameter definitions
            dependencies: List of required packages/modules
            requirements: requirements.txt content
            created_by: User who created the tool
            **kwargs: Additional tool properties
            
        Returns:
            Created Tool
        """
        # Check if tool with same name exists
        existing = self.db.query(Tool).filter(Tool.name == name).first()
        if existing:
            raise ValueError(f"Tool with name '{name}' already exists")
        
        tool = Tool(
            name=name,
            description=description,
            category=category,
            code=code,
            entry_point=entry_point or "execute",
            language=language,
            input_schema=input_schema,
            output_schema=output_schema,
            parameters=parameters,
            dependencies=dependencies or [],
            requirements=requirements,
            created_by=created_by,
            status=ToolStatus.DRAFT.value,
            **kwargs
        )
        
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        
        logger.info(
            f"Created tool: {name}",
            extra={
                "tool_id": str(tool.id),
                "tool_name": name,
                "created_by": created_by,
            }
        )
        
        return tool
    
    def get_tool(self, tool_id: UUID) -> Optional[Tool]:
        """Get tool by ID"""
        return self.db.query(Tool).filter(Tool.id == tool_id).first()
    
    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self.db.query(Tool).filter(Tool.name == name).first()
    
    def list_tools(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        active_only: bool = False
    ) -> List[Tool]:
        """
        List tools with optional filters
        
        Args:
            status: Filter by status
            category: Filter by category
            active_only: Only return active tools
            
        Returns:
            List of tools
        """
        query = self.db.query(Tool)
        
        if active_only:
            query = query.filter(Tool.status == ToolStatus.ACTIVE.value)
        elif status:
            query = query.filter(Tool.status == status)
        
        if category:
            query = query.filter(Tool.category == category)
        
        return query.order_by(desc(Tool.created_at)).all()
    
    def update_tool(
        self,
        tool_id: UUID,
        **kwargs
    ) -> Tool:
        """
        Update tool properties
        
        Args:
            tool_id: Tool ID
            **kwargs: Properties to update
            
        Returns:
            Updated Tool
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")
        
        # Update allowed fields
        allowed_fields = [
            'description', 'category', 'code', 'entry_point', 'language',
            'input_schema', 'output_schema', 'parameters', 'dependencies',
            'requirements', 'security_policies', 'allowed_agents', 'forbidden_agents',
            'requires_approval', 'timeout_seconds', 'max_memory_mb',
            'rate_limit_per_minute', 'tool_metadata', 'tags', 'examples'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(tool, field, value)
        
        tool.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(tool)
        
        logger.info(
            f"Updated tool: {tool.name}",
            extra={
                "tool_id": str(tool.id),
                "updated_fields": list(kwargs.keys()),
            }
        )
        
        return tool
    
    def activate_tool(self, tool_id: UUID) -> Tool:
        """
        Activate a tool (change status to active)
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Activated Tool
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")
        
        if tool.status != ToolStatus.WAITING_APPROVAL.value:
            raise ValueError(f"Tool must be in 'waiting_approval' status to activate (current: {tool.status})")
        
        tool.status = ToolStatus.ACTIVE.value
        tool.activated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(tool)
        
        logger.info(f"Activated tool: {tool.name}", extra={"tool_id": str(tool.id)})
        
        return tool
    
    def pause_tool(self, tool_id: UUID) -> Tool:
        """Pause a tool"""
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")
        
        tool.status = ToolStatus.PAUSED.value
        self.db.commit()
        self.db.refresh(tool)
        
        logger.info(f"Paused tool: {tool.name}", extra={"tool_id": str(tool.id)})
        
        return tool
    
    def deprecate_tool(self, tool_id: UUID) -> Tool:
        """Deprecate a tool"""
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")
        
        tool.status = ToolStatus.DEPRECATED.value
        self.db.commit()
        self.db.refresh(tool)
        
        logger.info(f"Deprecated tool: {tool.name}", extra={"tool_id": str(tool.id)})
        
        return tool
    
    def record_execution(
        self,
        tool_id: UUID,
        success: bool,
        execution_time: Optional[int] = None
    ):
        """
        Record tool execution for metrics
        
        Args:
            tool_id: Tool ID
            success: Whether execution was successful
            execution_time: Execution time in milliseconds
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return
        
        tool.total_executions += 1
        if success:
            tool.successful_executions += 1
        else:
            tool.failed_executions += 1
        
        # Update average execution time
        if execution_time is not None:
            if tool.average_execution_time is None:
                tool.average_execution_time = execution_time
            else:
                # Simple moving average
                tool.average_execution_time = int(
                    (tool.average_execution_time + execution_time) / 2
                )
        
        # Calculate success rate
        if tool.total_executions > 0:
            rate = tool.successful_executions / tool.total_executions
            tool.success_rate = f"{rate:.2%}"
        
        tool.last_used_at = datetime.now(timezone.utc)
        self.db.commit()
    
    def get_tool_metrics(self, tool_id: UUID) -> Dict[str, Any]:
        """
        Get tool performance metrics
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Dictionary with metrics
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")
        
        return {
            "total_executions": tool.total_executions,
            "successful_executions": tool.successful_executions,
            "failed_executions": tool.failed_executions,
            "success_rate": tool.success_rate,
            "average_execution_time": tool.average_execution_time,
            "last_used_at": tool.last_used_at.isoformat() if tool.last_used_at else None,
        }
    
    def can_agent_use_tool(self, tool_id: UUID, agent_id: UUID) -> bool:
        """
        Check if an agent can use a tool
        
        Args:
            tool_id: Tool ID
            agent_id: Agent ID
            
        Returns:
            True if agent can use tool, False otherwise
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return False
        
        # Check if tool is active
        if tool.status != ToolStatus.ACTIVE.value:
            return False
        
        # Check forbidden agents
        if tool.forbidden_agents and str(agent_id) in tool.forbidden_agents:
            return False
        
        # Check allowed agents (if specified, only those agents can use)
        if tool.allowed_agents:
            return str(agent_id) in tool.allowed_agents
        
        # If no restrictions, allow by default
        return True

