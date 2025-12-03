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
        use_tools: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a task using LLM, optionally with tools
        
        Args:
            task_description: Description of the task
            context: Additional context
            use_tools: Whether to attempt using tools for the task
            **kwargs: Additional parameters (may include tool_name and tool_params)
            
        Returns:
            Execution result
        """
        start_time = time.time()
        
        try:
            # Check if specific tool is requested
            tool_name = kwargs.get("tool_name")
            if tool_name:
                # Use specific tool
                tool_result = await self.use_tool(tool_name, **kwargs.get("tool_params", {}))
                
                if tool_result["status"] == "success":
                    execution_time = int(time.time() - start_time)
                    await self._record_execution(success=True, execution_time=execution_time)
                    
                    return {
                        "status": "success",
                        "result": tool_result["result"],
                        "message": f"Task completed using tool {tool_name}",
                        "metadata": {
                            "execution_time": execution_time,
                            "agent_id": str(self.agent_id),
                            "agent_name": self.name,
                            "tool_used": tool_name,
                            "tool_metadata": tool_result.get("metadata", {}),
                        }
                    }
                else:
                    # Tool failed, fall back to LLM
                    logger.warning(
                        f"Tool {tool_name} failed, falling back to LLM: {tool_result.get('message')}",
                        extra={"tool_result": tool_result}
                    )
            
            # Build prompt with context
            prompt = task_description
            if context:
                context_str = "\n\nContext:\n"
                for key, value in context.items():
                    context_str += f"{key}: {value}\n"
                prompt = f"{task_description}{context_str}"
            
            # If use_tools is True, include available tools in the prompt
            if use_tools:
                available_tools = self.get_available_tools()
                if available_tools:
                    tools_info = "\n".join([
                        f"- {tool['name']}: {tool.get('description', 'No description')}"
                        for tool in available_tools[:5]  # Limit to 5 tools
                    ])
                    prompt += f"\n\nAvailable tools:\n{tools_info}\n\nYou can request to use a tool by including 'use_tool:tool_name' in your response."
            
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
                    "tools_available": len(self.get_available_tools()) if use_tools else 0,
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

