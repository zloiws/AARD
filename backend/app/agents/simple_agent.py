"""
Simple Agent implementation example
This is a basic agent that can be used as a template for creating specialized agents
"""
from typing import Dict, Any, Optional
from uuid import UUID
import time

from app.agents.base_agent import BaseAgent
from app.services.agent_service import AgentService
from app.core.ollama_client import OllamaClient
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class SimpleAgent(BaseAgent):
    """
    Simple agent implementation
    
    This agent can execute basic tasks using LLM.
    Can be extended for specific use cases.
    """
    
    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a task using LLM
        
        Args:
            task_description: Description of the task
            context: Additional context
            **kwargs: Additional parameters
            
        Returns:
            Execution result
        """
        start_time = time.time()
        
        try:
            # Build prompt with context
            prompt = task_description
            if context:
                context_str = "\n\nContext:\n"
                for key, value in context.items():
                    context_str += f"{key}: {value}\n"
                prompt = f"{task_description}{context_str}"
            
            # Call LLM
            response = await self._call_llm(
                prompt=prompt,
                **kwargs
            )
            
            execution_time = int(time.time() - start_time)
            
            # Record successful execution
            await self._record_execution(success=True, execution_time=execution_time)
            
            return {
                "status": "success",
                "result": response,
                "message": "Task completed successfully",
                "metadata": {
                    "execution_time": execution_time,
                    "agent_id": str(self.agent_id),
                    "agent_name": self.name,
                }
            }
            
        except Exception as e:
            execution_time = int(time.time() - start_time)
            
            # Record failed execution
            await self._record_execution(success=False, execution_time=execution_time)
            
            logger.error(
                f"Task execution failed for agent {self.name}",
                exc_info=True,
                extra={
                    "agent_id": str(self.agent_id),
                    "task_description": task_description,
                    "error": str(e),
                }
            )
            
            return {
                "status": "failed",
                "result": None,
                "message": f"Task execution failed: {str(e)}",
                "metadata": {
                    "execution_time": execution_time,
                    "agent_id": str(self.agent_id),
                    "error": str(e),
                }
            }

