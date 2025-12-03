"""
Base Agent class for AARD platform
All agents should inherit from this class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from app.core.ollama_client import OllamaClient, TaskType
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes
from app.models.agent import Agent
from app.services.agent_service import AgentService

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
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        Initialize agent
        
        Args:
            agent_id: Agent ID from database
            agent_service: AgentService instance
            ollama_client: OllamaClient instance (optional, will create if not provided)
        """
        self.agent_id = agent_id
        self.agent_service = agent_service
        self.ollama_client = ollama_client or OllamaClient()
        self.tracer = get_tracer(__name__)
        
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
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type=task_type,
                    model=model,
                    temperature=temperature,
                    **kwargs
                )
                
                result_text = response.response if hasattr(response, "response") else str(response)
                
                add_span_attributes(span, {
                    "agent.llm.success": True,
                    "agent.llm.response_length": len(result_text),
                })
                
                return result_text
            except Exception as e:
                add_span_attributes(span, {
                    "agent.llm.success": False,
                    "agent.llm.error": str(e),
                })
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

