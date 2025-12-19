"""
Base Agent class for AARD platform
All agents should inherit from this class
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.core.ollama_client import OllamaClient, TaskType
from app.core.tracing import add_span_attributes, get_tracer
from app.models.agent import Agent
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService
from app.services.tool_service import ToolService
from app.tools.python_tool import PythonTool

logger = LoggingConfig.get_logger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in AARD platform
    
    Agents are autonomous entities that can:
    - Execute tasks using LLM
    - Use tools
    - Interact with other agents (A2A)
    - Maintain state and context
    """
    
    def __init__(
        self,
        agent_id: UUID,
        agent_service: AgentService,
        ollama_client: Optional[OllamaClient] = None,
        db_session = None
    ):
        """
        Initialize agent
        
        Args:
            agent_id: Agent ID from database
            agent_service: AgentService instance
            ollama_client: OllamaClient instance (optional, will create if not provided)
            db_session: Database session (optional, will create if not provided)
        """
        self.agent_id = agent_id
        self.agent_service = agent_service
        self.ollama_client = ollama_client or OllamaClient()
        self.tracer = get_tracer(__name__)
        
        # Database session for tools and memory
        self.db_session = db_session or SessionLocal()
        self.tool_service = ToolService(self.db_session)
        self.memory_service = MemoryService(self.db_session)
        
        # Default model and server_url для использования в _call_llm
        self._default_model: Optional[str] = None
        self._default_server_url: Optional[str] = None
        
        # Load agent data from database
        self._agent_data: Optional[Agent] = None
        self._load_agent_data()
    
    def _load_agent_data(self):
        """Load agent data from database"""
        self._agent_data = self.agent_service.get_agent(self.agent_id)
        if not self._agent_data:
            raise ValueError(f"Agent {self.agent_id} not found")
        
        if self._agent_data.status != "active":
            raise ValueError(f"Agent {self._agent_data.name} is not active (status: {self._agent_data.status})")
    
    @property
    def name(self) -> str:
        """Get agent name"""
        return self._agent_data.name if self._agent_data else "Unknown"
    
    @property
    def capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return self._agent_data.capabilities if self._agent_data and self._agent_data.capabilities else []
    
    @property
    def system_prompt(self) -> Optional[str]:
        """Get agent system prompt"""
        return self._agent_data.system_prompt if self._agent_data else None
    
    @property
    def model_preference(self) -> Optional[str]:
        """Get preferred model"""
        return self._agent_data.model_preference if self._agent_data else None
    
    @abstractmethod
    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a task
        
        Args:
            task_description: Description of the task to execute
            context: Additional context for the task
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with execution results:
            {
                "status": "success" | "failed" | "partial",
                "result": Any,
                "message": str,
                "metadata": Dict
            }
        """
        pass
    
    async def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: Optional[TaskType] = None,
        **kwargs
    ) -> str:
        """
        Call LLM with agent's configuration
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (uses agent's if not provided)
            task_type: Task type (auto-detected if not provided)
            **kwargs: Additional parameters for LLM call
            
        Returns:
            LLM response text
        """
        # Use agent's system prompt if not provided
        if system_prompt is None:
            system_prompt = self.system_prompt
        
        # Use agent's model preference if available
        model = kwargs.pop('model', None) or self.model_preference
        
        # Use agent's temperature if not specified
        temperature = kwargs.pop('temperature', None)
        if temperature is None and self._agent_data and self._agent_data.temperature:
            try:
                temperature = float(self._agent_data.temperature)
            except (ValueError, TypeError):
                temperature = 0.7
        
        # Auto-detect task type from capabilities if not provided
        if task_type is None:
            task_type = self._detect_task_type()
        
        with self.tracer.start_as_current_span(
            f"agent.llm_call",
            attributes={
                "agent.id": str(self.agent_id),
                "agent.name": self.name,
                "task_type": task_type.value if task_type else "unknown",
            }
        ) as span:
            try:
                # Использовать default model и server_url если не переданы
                actual_model = model or self._default_model
                server_url = kwargs.get("server_url") or self._default_server_url
                
                # Передать server_url в kwargs если есть
                if server_url:
                    kwargs["server_url"] = server_url
                
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type=task_type,
                    model=actual_model,
                    temperature=temperature,
                    **kwargs
                )
                
                result_text = response.response if hasattr(response, "response") else str(response)
                
                if span:
                    add_span_attributes(
                        agent_llm_success=True,
                        agent_llm_response_length=len(result_text)
                    )
                
                return result_text
            except Exception as e:
                if span:
                    add_span_attributes(
                        agent_llm_success=False,
                        agent_llm_error=str(e)
                    )
                logger.error(
                    f"LLM call failed for agent {self.name}",
                    exc_info=True,
                    extra={
                        "agent_id": str(self.agent_id),
                        "error": str(e),
                    }
                )
                raise
    
    def _detect_task_type(self) -> TaskType:
        """
        Detect task type from agent capabilities
        
        Returns:
            TaskType enum value
        """
        if not self.capabilities:
            return TaskType.GENERAL_CHAT
        
        # Map capabilities to task types
        capability_mapping = {
            "code_generation": TaskType.CODE_GENERATION,
            "code_analysis": TaskType.CODE_ANALYSIS,
            "planning": TaskType.PLANNING,
            "reasoning": TaskType.REASONING,
            "text_generation": TaskType.TEXT_GENERATION,
        }
        
        for capability in self.capabilities:
            if capability in capability_mapping:
                return capability_mapping[capability]
        
        return TaskType.GENERAL_CHAT
    
    def _check_permissions(self, action: str) -> bool:
        """
        Check if agent has permission to perform an action
        
        Args:
            action: Action to check
            
        Returns:
            True if allowed, False otherwise
        """
        if not self._agent_data:
            return False
        
        # Check forbidden actions first
        if self._agent_data.forbidden_actions:
            if action in self._agent_data.forbidden_actions:
                return False
        
        # Check allowed actions
        if self._agent_data.allowed_actions:
            return action in self._agent_data.allowed_actions
        
        # If no restrictions, allow by default
        return True
    
    async def _record_execution(
        self,
        success: bool,
        execution_time: Optional[int] = None
    ):
        """
        Record task execution for metrics
        
        Args:
            success: Whether task was successful
            execution_time: Execution time in seconds
        """
        self.agent_service.record_task_execution(
            agent_id=self.agent_id,
            success=success,
            execution_time=execution_time
        )
    
    def get_available_tools(
        self,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of tools available to this agent
        
        Args:
            category: Optional tool category filter
            
        Returns:
            List of tool dictionaries
        """
        tools = self.tool_service.list_tools(
            status="active",
            category=category,
            active_only=True
        )
        
        # Filter by agent access
        available = []
        for tool in tools:
            if self.tool_service.can_agent_use_tool(tool.id, self.agent_id):
                available.append(tool.to_dict())
        
        return available
    
    def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get tool by name if available to this agent
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool dictionary or None
        """
        tool = self.tool_service.get_tool_by_name(tool_name)
        if not tool:
            return None
        
        if not self.tool_service.can_agent_use_tool(tool.id, self.agent_id):
            logger.warning(
                f"Agent {self.name} does not have access to tool {tool_name}",
                extra={"agent_id": str(self.agent_id), "tool_name": tool_name}
            )
            return None
        
        return tool.to_dict()
    
    async def use_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Use a tool to perform an action
        
        Args:
            tool_name: Name of the tool to use
            **kwargs: Parameters to pass to the tool
            
        Returns:
            Tool execution result:
            {
                "status": "success" | "failed",
                "result": Any,
                "message": str,
                "metadata": Dict
            }
        """
        with self.tracer.start_as_current_span(
            "agent.use_tool",
            attributes={
                "agent.id": str(self.agent_id),
                "agent.name": self.name,
                "tool.name": tool_name,
            }
        ) as span:
            try:
                # Get tool
                tool_data = self.get_tool_by_name(tool_name)
                if not tool_data:
                    error_msg = f"Tool '{tool_name}' not found or not accessible"
                    if span:
                        add_span_attributes(
                            tool_error=error_msg,
                            tool_success=False
                        )
                    return {
                        "status": "failed",
                        "result": None,
                        "message": error_msg,
                        "metadata": {}
                    }
                
                # Check permissions
                if not self._check_permissions(f"use_tool:{tool_name}"):
                    error_msg = f"Agent {self.name} does not have permission to use tool {tool_name}"
                    if span:
                        add_span_attributes(
                            tool_error=error_msg,
                            tool_success=False
                        )
                    return {
                        "status": "failed",
                        "result": None,
                        "message": error_msg,
                        "metadata": {}
                    }
                
                # Create tool instance
                tool = PythonTool(
                    tool_id=tool_data["id"],
                    tool_service=self.tool_service
                )
                
                # Execute tool
                result = await tool.execute(**kwargs)
                
                if span:
                    add_span_attributes(
                        tool_success=result["status"] == "success",
                        tool_execution_time_ms=result.get("metadata", {}).get("execution_time_ms", 0)
                    )
                
                logger.info(
                    f"Agent {self.name} used tool {tool_name}",
                    extra={
                        "agent_id": str(self.agent_id),
                        "tool_name": tool_name,
                        "tool_status": result["status"],
                    }
                )
                
                return result
                
            except Exception as e:
                if span:
                    add_span_attributes(
                        tool_error=str(e),
                        tool_success=False
                    )
                logger.error(
                    f"Error using tool {tool_name} for agent {self.name}",
                    exc_info=True,
                    extra={
                        "agent_id": str(self.agent_id),
                        "tool_name": tool_name,
                        "error": str(e),
                    }
                )
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Tool execution error: {str(e)}",
                    "metadata": {"error": str(e)}
                }
    
    def list_tools_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get tools grouped by category
        
        Returns:
            Dictionary mapping category to list of tools
        """
        tools = self.get_available_tools()
        categorized = {}
        
        for tool in tools:
            category = tool.get("category", "uncategorized")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(tool)
        
        return categorized
    
    # Memory methods
    
    def remember(
        self,
        memory_type: str,
        content: Dict[str, Any],
        summary: Optional[str] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Any:
        """
        Save information to long-term memory
        
        Args:
            memory_type: Type of memory (fact, experience, pattern, rule)
            content: Memory content (dict)
            summary: Human-readable summary
            importance: Importance score (0.0 to 1.0)
            tags: Tags for categorization
            source: Source of memory (task_id, user, etc.)
            expires_at: Optional expiration date
            
        Returns:
            Created AgentMemory
        """
        with self.tracer.start_as_current_span(
            "agent.remember",
            attributes={
                "agent.id": str(self.agent_id),
                "agent.name": self.name,
                "memory.type": memory_type,
            }
        ) as span:
            try:
                memory = self.memory_service.save_memory(
                    agent_id=self.agent_id,
                    memory_type=memory_type,
                    content=content,
                    summary=summary,
                    importance=importance,
                    tags=tags,
                    source=source,
                    expires_at=expires_at
                )
                
                if span:
                    add_span_attributes(
                        memory_id=str(memory.id),
                        memory_importance=importance
                    )
                
                logger.debug(
                    f"Agent {self.name} remembered {memory_type}",
                    extra={
                        "agent_id": str(self.agent_id),
                        "memory_id": str(memory.id),
                        "memory_type": memory_type
                    }
                )
                
                return memory
            except Exception as e:
                if span:
                    add_span_attributes(memory_error=str(e))
                logger.error(
                    f"Error saving memory for agent {self.name}",
                    exc_info=True,
                    extra={
                        "agent_id": str(self.agent_id),
                        "error": str(e)
                    }
                )
                raise
    
    def recall(
        self,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recall memories from long-term storage
        
        Args:
            memory_type: Filter by memory type
            min_importance: Minimum importance score
            tags: Filter by tags
            limit: Maximum number of results
            
        Returns:
            List of memory dictionaries
        """
        with self.tracer.start_as_current_span(
            "agent.recall",
            attributes={
                "agent.id": str(self.agent_id),
                "agent.name": self.name,
            }
        ) as span:
            try:
                memories = self.memory_service.get_memories(
                    agent_id=self.agent_id,
                    memory_type=memory_type,
                    min_importance=min_importance,
                    tags=tags,
                    limit=limit
                )
                
                result = [m.to_dict() for m in memories]
                
                if span:
                    add_span_attributes(
                        memories_found=len(result)
                    )
                
                return result
            except Exception as e:
                if span:
                    add_span_attributes(recall_error=str(e))
                logger.error(
                    f"Error recalling memories for agent {self.name}",
                    exc_info=True,
                    extra={
                        "agent_id": str(self.agent_id),
                        "error": str(e)
                    }
                )
                return []
    
    def search_memory(
        self,
        query_text: Optional[str] = None,
        content_query: Optional[Dict[str, Any]] = None,
        memory_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search memories by text or content
        
        Args:
            query_text: Text to search in summary
            content_query: JSONB query for content
            memory_type: Filter by memory type
            limit: Maximum number of results
            
        Returns:
            List of matching memory dictionaries
        """
        with self.tracer.start_as_current_span(
            "agent.search_memory",
            attributes={
                "agent.id": str(self.agent_id),
                "agent.name": self.name,
            }
        ) as span:
            try:
                memories = self.memory_service.search_memories(
                    agent_id=self.agent_id,
                    query_text=query_text,
                    content_query=content_query,
                    memory_type=memory_type,
                    limit=limit
                )
                
                result = [m.to_dict() for m in memories]
                
                if span:
                    add_span_attributes(
                        memories_found=len(result)
                    )
                
                return result
            except Exception as e:
                if span:
                    add_span_attributes(search_error=str(e))
                logger.error(
                    f"Error searching memories for agent {self.name}",
                    exc_info=True,
                    extra={
                        "agent_id": str(self.agent_id),
                        "error": str(e)
                    }
                )
                return []
    
    def forget(self, memory_id: UUID) -> bool:
        """
        Delete a memory from long-term storage
        
        Args:
            memory_id: Memory ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self.tracer.start_as_current_span(
            "agent.forget",
            attributes={
                "agent.id": str(self.agent_id),
                "agent.name": self.name,
                "memory.id": str(memory_id),
            }
        ):
            try:
                result = self.memory_service.forget_memory(memory_id)
                logger.debug(
                    f"Agent {self.name} forgot memory {memory_id}",
                    extra={
                        "agent_id": str(self.agent_id),
                        "memory_id": str(memory_id),
                        "deleted": result
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"Error forgetting memory for agent {self.name}",
                    exc_info=True,
                    extra={
                        "agent_id": str(self.agent_id),
                        "memory_id": str(memory_id),
                        "error": str(e)
                    }
                )
                return False
    
    def save_context(
        self,
        context_key: str,
        content: Dict[str, Any],
        session_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> Any:
        """
        Save context to short-term memory
        
        Args:
            context_key: Key for context lookup
            content: Context data
            session_id: Optional session ID
            ttl_seconds: Time to live in seconds
            
        Returns:
            Created MemoryEntry
        """
        try:
            entry = self.memory_service.save_context(
                agent_id=self.agent_id,
                context_key=context_key,
                content=content,
                session_id=session_id,
                ttl_seconds=ttl_seconds
            )
            return entry
        except Exception as e:
            logger.error(
                f"Error saving context for agent {self.name}",
                exc_info=True,
                extra={
                    "agent_id": str(self.agent_id),
                    "context_key": context_key,
                    "error": str(e)
                }
            )
            raise
    
    def get_context(
        self,
        context_key: str,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get context from short-term memory
        
        Args:
            context_key: Context key
            session_id: Optional session ID
            
        Returns:
            Context content or None
        """
        try:
            return self.memory_service.get_context(
                agent_id=self.agent_id,
                context_key=context_key,
                session_id=session_id
            )
        except Exception as e:
            logger.error(
                f"Error getting context for agent {self.name}",
                exc_info=True,
                extra={
                    "agent_id": str(self.agent_id),
                    "context_key": context_key,
                    "error": str(e)
                }
            )
            return None
    
    def get_all_context(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all context entries for this agent/session
        
        Args:
            session_id: Optional session ID
            
        Returns:
            Dictionary of context_key -> content
        """
        try:
            return self.memory_service.get_all_context(
                agent_id=self.agent_id,
                session_id=session_id
            )
        except Exception as e:
            logger.error(
                f"Error getting all context for agent {self.name}",
                exc_info=True,
                extra={
                    "agent_id": str(self.agent_id),
                    "error": str(e)
                }
            )
            return {}

