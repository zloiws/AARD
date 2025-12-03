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
        session_id = kwargs.get("session_id")  # Get session ID if provided
        
        try:
            # 1. Search relevant memories before execution
            relevant_memories = []
            try:
                # Search for relevant memories based on task description
                memory_search = self.search_memory(
                    query_text=task_description[:100] if len(task_description) > 100 else task_description,
                    limit=5
                )
                relevant_memories = memory_search
                
                # Also get recent experiences
                recent_experiences = self.recall(
                    memory_type="experience",
                    limit=3
                )
                relevant_memories.extend(recent_experiences)
            except Exception as e:
                logger.warning(
                    f"Error searching memories: {e}",
                    extra={"agent_id": str(self.agent_id)}
                )
            
            # 2. Save current context to short-term memory
            try:
                self.save_context(
                    context_key="current_task",
                    content={
                        "task_description": task_description,
                        "context": context or {},
                        "timestamp": time.time()
                    },
                    session_id=session_id,
                    ttl_seconds=3600  # 1 hour TTL
                )
            except Exception as e:
                logger.warning(
                    f"Error saving context: {e}",
                    extra={"agent_id": str(self.agent_id)}
                )
            
            # 3. Get existing context if available
            existing_context = {}
            try:
                existing_context = self.get_all_context(session_id=session_id)
            except Exception as e:
                logger.warning(
                    f"Error getting context: {e}",
                    extra={"agent_id": str(self.agent_id)}
                )
            
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
            
            # Build prompt with context and relevant memories
            prompt = task_description
            
            # Add relevant memories to prompt
            if relevant_memories:
                memories_str = "\n\nRelevant memories from past experiences:\n"
                for mem in relevant_memories[:5]:  # Limit to 5 most relevant
                    mem_summary = mem.get("summary") or str(mem.get("content", ""))[:200]
                    memories_str += f"- {mem_summary}\n"
                prompt = f"{prompt}{memories_str}"
            
            # Add context
            if context:
                context_str = "\n\nContext:\n"
                for key, value in context.items():
                    context_str += f"{key}: {value}\n"
                prompt = f"{prompt}{context_str}"
            
            # Add existing short-term context
            if existing_context:
                context_str = "\n\nPrevious context:\n"
                for key, value in existing_context.items():
                    if isinstance(value, dict):
                        context_str += f"{key}: {str(value)[:200]}\n"
                    else:
                        context_str += f"{key}: {value}\n"
                prompt = f"{prompt}{context_str}"
            
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
            
            # 4. Save execution result to long-term memory
            try:
                self.remember(
                    memory_type="experience",
                    content={
                        "task_description": task_description,
                        "result": response[:500] if isinstance(response, str) else str(response)[:500],
                        "execution_time": execution_time,
                        "success": True,
                        "context": context or {}
                    },
                    summary=f"Successfully completed: {task_description[:100]}",
                    importance=0.6,
                    tags=["execution", "success"],
                    source=session_id or "system"
                )
            except Exception as e:
                logger.warning(
                    f"Error saving execution to memory: {e}",
                    extra={"agent_id": str(self.agent_id)}
                )
            
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
                    "memories_used": len(relevant_memories),
                }
            }
            
        except Exception as e:
            execution_time = int(time.time() - start_time)
            
            # 5. Save failure to memory for learning
            try:
                self.remember(
                    memory_type="experience",
                    content={
                        "task_description": task_description,
                        "error": str(e),
                        "execution_time": execution_time,
                        "success": False,
                        "context": context or {}
                    },
                    summary=f"Failed: {task_description[:100]} - {str(e)[:100]}",
                    importance=0.7,  # Failures are important to remember
                    tags=["execution", "failure", "error"],
                    source=session_id or "system"
                )
            except Exception as mem_error:
                logger.warning(
                    f"Error saving failure to memory: {mem_error}",
                    extra={"agent_id": str(self.agent_id)}
                )
            
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

