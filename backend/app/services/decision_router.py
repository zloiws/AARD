"""
Decision Router Service for selecting tools, agents, and prompts based on task requirements
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.core.tracing import add_span_attributes, get_tracer
from app.models.agent import Agent, AgentCapability, AgentStatus
from app.models.prompt import Prompt, PromptStatus, PromptType
from app.models.tool import Tool, ToolCategory, ToolStatus
from app.services.agent_service import AgentService
from app.services.tool_service import ToolService
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class DecisionRouter:
    """Router for selecting appropriate tools, agents, and prompts for tasks"""
    
    def __init__(self, db: Session = None):
        """
        Initialize Decision Router
        
        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or SessionLocal()
        self.agent_service = AgentService(self.db)
        self.tool_service = ToolService(self.db)
        self.tracer = get_tracer(__name__)
    
    async def route_task(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        requirements: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route a task to appropriate components
        
        Args:
            task_description: Description of the task
            task_type: Type of task (code_generation, planning, etc.)
            requirements: Task requirements (capabilities, tools, etc.)
            context: Additional context
            
        Returns:
            Routing decision with selected components:
            {
                "tool": {...} or None,
                "agent": {...} or None,
                "prompt": {...} or None,
                "reasoning": str
            }
        """
        with self.tracer.start_as_current_span(
            "decision_router.route_task",
            attributes={
                "task_type": task_type or "unknown",
            }
        ) as span:
            try:
                routing_decision = {
                    "tool": None,
                    "agent": None,
                    "prompt": None,
                    "reasoning": []
                }
                
                # Analyze task to determine requirements
                analysis = self._analyze_task(task_description, task_type, requirements)
                
                # Select tool if needed
                if analysis.get("needs_tool"):
                    tool = await self.select_tool(
                        task_description=task_description,
                        task_type=task_type,
                        requirements=analysis.get("tool_requirements", {}),
                        context=context
                    )
                    routing_decision["tool"] = tool
                    if tool:
                        routing_decision["reasoning"].append(f"Selected tool: {tool.get('name')}")
                
                # Select agent if needed
                if analysis.get("needs_agent"):
                    agent = await self.select_agent(
                        task_description=task_description,
                        task_type=task_type,
                        requirements=analysis.get("agent_requirements", {}),
                        context=context
                    )
                    routing_decision["agent"] = agent
                    if agent:
                        routing_decision["reasoning"].append(f"Selected agent: {agent.get('name')}")
                
                # Select prompt if needed
                if analysis.get("needs_prompt"):
                    prompt = await self.select_prompt(
                        task_description=task_description,
                        task_type=task_type,
                        context=context
                    )
                    routing_decision["prompt"] = prompt
                    if prompt:
                        routing_decision["reasoning"].append(f"Selected prompt: {prompt.get('name')}")
                
                routing_decision["reasoning"] = "; ".join(routing_decision["reasoning"]) or "No specific components selected"
                
                if span:
                    add_span_attributes(
                        tool_selected=routing_decision["tool"] is not None,
                        agent_selected=routing_decision["agent"] is not None,
                        prompt_selected=routing_decision["prompt"] is not None
                    )
                
                logger.info(
                    "Task routed",
                    extra={
                        "task_type": task_type,
                        "tool_selected": routing_decision["tool"] is not None,
                        "agent_selected": routing_decision["agent"] is not None,
                        "prompt_selected": routing_decision["prompt"] is not None
                    }
                )
                
                return routing_decision
                
            except Exception as e:
                if span:
                    add_span_attributes(routing_error=str(e))
                logger.error(f"Error routing task: {e}", exc_info=True)
                raise
    
    def _analyze_task(
        self,
        task_description: str,
        task_type: Optional[str],
        requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze task to determine what components are needed
        
        Args:
            task_description: Task description
            task_type: Task type
            requirements: Task requirements
            
        Returns:
            Analysis result with needs and requirements
        """
        analysis = {
            "needs_tool": False,
            "needs_agent": False,
            "needs_prompt": False,
            "tool_requirements": {},
            "agent_requirements": {}
        }
        
        # Determine if tool is needed based on keywords and task type
        tool_keywords = ["execute", "run", "calculate", "process", "transform", "generate code", "file", "database"]
        if any(keyword in task_description.lower() for keyword in tool_keywords):
            analysis["needs_tool"] = True
            analysis["tool_requirements"] = {
                "category": self._infer_tool_category(task_description, task_type)
            }
        
        # Determine if agent is needed
        agent_keywords = ["plan", "reason", "analyze", "decide", "coordinate", "manage"]
        if any(keyword in task_description.lower() for keyword in agent_keywords):
            analysis["needs_agent"] = True
            analysis["agent_requirements"] = {
                "capabilities": self._infer_required_capabilities(task_description, task_type)
            }
        
        # Determine if prompt is needed
        prompt_keywords = ["template", "format", "structure", "generate text", "write"]
        if any(keyword in task_description.lower() for keyword in prompt_keywords):
            analysis["needs_prompt"] = True
        
        # Override with explicit requirements
        if requirements:
            if "tool" in requirements:
                analysis["needs_tool"] = True
                analysis["tool_requirements"].update(requirements.get("tool", {}))
            if "agent" in requirements:
                analysis["needs_agent"] = True
                analysis["agent_requirements"].update(requirements.get("agent", {}))
            if "prompt" in requirements:
                analysis["needs_prompt"] = True
        
        return analysis
    
    def _infer_tool_category(self, task_description: str, task_type: Optional[str]) -> Optional[str]:
        """Infer tool category from task description"""
        task_lower = task_description.lower()
        
        if "code" in task_lower or "python" in task_lower or "script" in task_lower:
            return "code_execution"
        if "file" in task_lower or "read" in task_lower or "write" in task_lower:
            return "file_operations"
        if "database" in task_lower or "sql" in task_lower or "query" in task_lower:
            return "database"
        if "http" in task_lower or "api" in task_lower or "request" in task_lower:
            return "http_client"
        if "calculate" in task_lower or "math" in task_lower:
            return "calculation"
        
        return None
    
    def _infer_required_capabilities(self, task_description: str, task_type: Optional[str]) -> List[str]:
        """Infer required agent capabilities from task description"""
        capabilities = []
        task_lower = task_description.lower()
        
        if "code" in task_lower or "generate" in task_lower:
            capabilities.append("code_generation")
        if "plan" in task_lower or "strategy" in task_lower:
            capabilities.append("planning")
        if "reason" in task_lower or "analyze" in task_lower:
            capabilities.append("reasoning")
        if "test" in task_lower:
            capabilities.append("testing")
        
        # Add based on task_type
        if task_type:
            type_mapping = {
                "code_generation": ["code_generation"],
                "code_analysis": ["code_analysis"],
                "planning": ["planning"],
                "reasoning": ["reasoning"],
            }
            if task_type in type_mapping:
                capabilities.extend(type_mapping[task_type])
        
        return list(set(capabilities))  # Remove duplicates
    
    async def select_tool(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        requirements: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Select appropriate tool for the task
        
        Args:
            task_description: Task description
            task_type: Task type
            requirements: Tool requirements (category, name, etc.)
            context: Additional context
            
        Returns:
            Selected tool dictionary or None
        """
        with self.tracer.start_as_current_span("decision_router.select_tool") as span:
            try:
                # Get all active tools
                tools = self.tool_service.list_tools(status="active", active_only=True)
                
                if not tools:
                    if span:
                        add_span_attributes(tool_selected=False, reason="no_tools_available")
                    return None
                
                # Filter by requirements
                filtered_tools = tools
                
                if requirements:
                    category = requirements.get("category")
                    if category:
                        filtered_tools = [t for t in filtered_tools if t.category == category]
                    
                    tool_name = requirements.get("name")
                    if tool_name:
                        filtered_tools = [t for t in filtered_tools if t.name == tool_name]
                    
                    required_capabilities = requirements.get("capabilities")
                    if required_capabilities:
                        # Filter by tool capabilities if available
                        pass  # Can be extended
                
                if not filtered_tools:
                    # Fallback to all tools
                    filtered_tools = tools
                
                # Score tools based on relevance
                scored_tools = []
                for tool in filtered_tools:
                    score = self._score_tool_relevance(tool, task_description, task_type)
                    scored_tools.append((tool, score))
                
                # Sort by score (descending)
                scored_tools.sort(key=lambda x: x[1], reverse=True)
                
                if scored_tools:
                    selected_tool = scored_tools[0][0]
                    if span:
                        add_span_attributes(
                            tool_selected=True,
                            tool_id=str(selected_tool.id),
                            tool_name=selected_tool.name,
                            tool_score=scored_tools[0][1]
                        )
                    return selected_tool.to_dict()
                
                if span:
                    add_span_attributes(tool_selected=False, reason="no_matching_tools")
                return None
                
            except Exception as e:
                if span:
                    add_span_attributes(tool_error=str(e))
                logger.error(f"Error selecting tool: {e}", exc_info=True)
                return None
    
    def _score_tool_relevance(self, tool: Tool, task_description: str, task_type: Optional[str]) -> float:
        """Score tool relevance to task (0.0 to 1.0)"""
        score = 0.5  # Base score
        
        task_lower = task_description.lower()
        tool_name_lower = tool.name.lower()
        tool_desc_lower = (tool.description or "").lower()
        
        # Name match
        if tool_name_lower in task_lower:
            score += 0.3
        
        # Description match
        if tool_desc_lower:
            matching_words = sum(1 for word in task_lower.split() if word in tool_desc_lower)
            score += min(0.2, matching_words * 0.05)
        
        # Category match
        if tool.category:
            category_keywords = {
                "code_execution": ["code", "python", "execute", "run"],
                "file_operations": ["file", "read", "write", "save"],
                "database": ["database", "sql", "query"],
                "http_client": ["http", "api", "request", "fetch"],
            }
            if tool.category in category_keywords:
                keywords = category_keywords[tool.category]
                if any(kw in task_lower for kw in keywords):
                    score += 0.2
        
        return min(1.0, score)
    
    async def select_agent(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        requirements: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Select appropriate agent for the task
        
        Args:
            task_description: Task description
            task_type: Task type
            requirements: Agent requirements (capabilities, name, etc.)
            context: Additional context
            
        Returns:
            Selected agent dictionary or None
        """
        with self.tracer.start_as_current_span("decision_router.select_agent") as span:
            try:
                # Get all active agents
                agents = self.db.query(Agent).filter(
                    Agent.status == AgentStatus.ACTIVE.value
                ).all()
                
                if not agents:
                    if span:
                        add_span_attributes(agent_selected=False, reason="no_agents_available")
                    return None
                
                # Filter by requirements
                filtered_agents = agents
                
                if requirements:
                    required_capabilities = requirements.get("capabilities", [])
                    if required_capabilities:
                        filtered_agents = [
                            a for a in filtered_agents
                            if a.capabilities and any(
                                cap in (a.capabilities or []) for cap in required_capabilities
                            )
                        ]
                    
                    agent_name = requirements.get("name")
                    if agent_name:
                        filtered_agents = [a for a in filtered_agents if a.name == agent_name]
                
                if not filtered_agents:
                    # Fallback to all agents
                    filtered_agents = agents
                
                # Score agents based on relevance
                scored_agents = []
                for agent in filtered_agents:
                    score = self._score_agent_relevance(agent, task_description, task_type, requirements)
                    scored_agents.append((agent, score))
                
                # Sort by score (descending)
                scored_agents.sort(key=lambda x: x[1], reverse=True)
                
                if scored_agents:
                    selected_agent = scored_agents[0][0]
                    if span:
                        add_span_attributes(
                            agent_selected=True,
                            agent_id=str(selected_agent.id),
                            agent_name=selected_agent.name,
                            agent_score=scored_agents[0][1]
                        )
                    return selected_agent.to_dict()
                
                if span:
                    add_span_attributes(agent_selected=False, reason="no_matching_agents")
                return None
                
            except Exception as e:
                if span:
                    add_span_attributes(agent_error=str(e))
                logger.error(f"Error selecting agent: {e}", exc_info=True)
                return None
    
    def _score_agent_relevance(
        self,
        agent: Agent,
        task_description: str,
        task_type: Optional[str],
        requirements: Optional[Dict[str, Any]]
    ) -> float:
        """Score agent relevance to task (0.0 to 1.0)"""
        score = 0.5  # Base score
        
        # Capability match
        if agent.capabilities:
            task_lower = task_description.lower()
            capability_keywords = {
                "code_generation": ["code", "generate", "create", "write"],
                "planning": ["plan", "strategy", "steps"],
                "reasoning": ["reason", "analyze", "think", "decide"],
            }
            
            for capability in agent.capabilities:
                if capability in capability_keywords:
                    keywords = capability_keywords[capability]
                    if any(kw in task_lower for kw in keywords):
                        score += 0.2
        
        # Success rate (if available)
        if agent.success_rate:
            try:
                success_rate = float(agent.success_rate)
                score += success_rate * 0.2
            except (ValueError, TypeError):
                pass
        
        # Model preference match with task type
        if agent.model_preference and task_type:
            # Simple heuristic: prefer agents with models matching task type
            score += 0.1
        
        return min(1.0, score)
    
    async def select_prompt(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Select appropriate prompt for the task
        
        Args:
            task_description: Task description
            task_type: Task type
            context: Additional context
            
        Returns:
            Selected prompt dictionary or None
        """
        with self.tracer.start_as_current_span("decision_router.select_prompt") as span:
            try:
                # Get active prompts
                prompts = self.db.query(Prompt).filter(
                    Prompt.status == PromptStatus.ACTIVE.value
                ).all()
                
                if not prompts:
                    if span:
                        add_span_attributes(prompt_selected=False, reason="no_prompts_available")
                    return None
                
                # Filter by type if task_type provided
                filtered_prompts = prompts
                if task_type:
                    type_mapping = {
                        "code_generation": PromptType.CODE_GENERATION,
                        "planning": PromptType.PLANNING,
                        "reasoning": PromptType.REASONING,
                    }
                    if task_type in type_mapping:
                        filtered_prompts = [
                            p for p in prompts
                            if p.prompt_type == type_mapping[task_type].value
                        ]
                
                if not filtered_prompts:
                    filtered_prompts = prompts
                
                # Score prompts based on relevance
                scored_prompts = []
                for prompt in filtered_prompts:
                    score = self._score_prompt_relevance(prompt, task_description, task_type)
                    scored_prompts.append((prompt, score))
                
                # Sort by score
                scored_prompts.sort(key=lambda x: x[1], reverse=True)
                
                if scored_prompts:
                    selected_prompt = scored_prompts[0][0]
                    if span:
                        add_span_attributes(
                            prompt_selected=True,
                            prompt_id=str(selected_prompt.id),
                            prompt_name=selected_prompt.name,
                            prompt_score=scored_prompts[0][1]
                        )
                    return {
                        "id": str(selected_prompt.id),
                        "name": selected_prompt.name,
                        "content": selected_prompt.content,
                        "prompt_type": selected_prompt.prompt_type,
                    }
                
                if span:
                    add_span_attributes(prompt_selected=False, reason="no_matching_prompts")
                return None
                
            except Exception as e:
                if span:
                    add_span_attributes(prompt_error=str(e))
                logger.error(f"Error selecting prompt: {e}", exc_info=True)
                return None
    
    def _score_prompt_relevance(self, prompt: Prompt, task_description: str, task_type: Optional[str]) -> float:
        """Score prompt relevance to task (0.0 to 1.0)"""
        score = 0.5  # Base score
        
        task_lower = task_description.lower()
        prompt_name_lower = prompt.name.lower()
        prompt_content_lower = (prompt.content or "").lower()
        
        # Name match
        if prompt_name_lower in task_lower:
            score += 0.3
        
        # Content match
        if prompt_content_lower:
            matching_words = sum(1 for word in task_lower.split() if word in prompt_content_lower)
            score += min(0.2, matching_words * 0.05)
        
        return min(1.0, score)

