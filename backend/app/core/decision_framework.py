"""
Decision Framework for clear separation of concerns between code and LLM
"""
from typing import Dict, Any, Optional, Callable, List
from abc import ABC, abstractmethod
import json

from app.core.logging_config import LoggingConfig
from app.core.ollama_client import OllamaClient
from app.core.tracing import get_tracer, add_span_attributes

logger = LoggingConfig.get_logger(__name__)


class CodeExecutor(ABC):
    """
    Base class for code-based execution
    Handles: structure, logic, validation, tool invocation
    """
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute code-based logic"""
        pass
    
    @abstractmethod
    def validate(self, result: Any) -> bool:
        """Validate result using code logic"""
        pass


class LLMReasoner(ABC):
    """
    Base class for LLM-based reasoning
    Handles: reasoning, natural language understanding, idea generation
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama_client = ollama_client or OllamaClient()
        self.tracer = get_tracer(__name__)
    
    @abstractmethod
    async def reason(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Perform reasoning using LLM"""
        pass
    
    @abstractmethod
    async def understand(self, text: str) -> Dict[str, Any]:
        """Understand natural language using LLM"""
        pass
    
    @abstractmethod
    async def generate_ideas(self, problem: str, constraints: Optional[List[str]] = None) -> List[str]:
        """Generate ideas using LLM"""
        pass


class HybridDecisionMaker:
    """
    Combines code and LLM for decision making
    Enforces clear separation of concerns
    """
    
    def __init__(
        self,
        code_executor: CodeExecutor,
        llm_reasoner: LLMReasoner,
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        Initialize Hybrid Decision Maker
        
        Args:
            code_executor: Code executor instance
            llm_reasoner: LLM reasoner instance
            ollama_client: OllamaClient (optional, will use from reasoner)
        """
        self.code_executor = code_executor
        self.llm_reasoner = llm_reasoner
        self.ollama_client = ollama_client or OllamaClient()
        self.tracer = get_tracer(__name__)
    
    async def make_decision(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        use_llm_for_reasoning: bool = True,
        use_code_for_execution: bool = True
    ) -> Dict[str, Any]:
        """
        Make decision using hybrid approach
        
        Flow:
        1. Code: Structure and validate task
        2. LLM: Understand and reason about task
        3. Code: Execute structured actions
        4. LLM: Generate ideas if needed
        5. Code: Validate results
        
        Args:
            task: Task description
            context: Additional context
            use_llm_for_reasoning: Whether to use LLM for reasoning
            use_code_for_execution: Whether to use code for execution
            
        Returns:
            Decision result
        """
        with self.tracer.start_as_current_span("hybrid_decision_maker.make_decision") as span:
            try:
                # Stage 1: Code - Structure and validate task
                structured_task = self._structure_task(task, context)
                
                # Stage 2: LLM - Understand and reason
                if use_llm_for_reasoning:
                    understanding = await self.llm_reasoner.understand(structured_task["description"])
                    reasoning = await self.llm_reasoner.reason(
                        structured_task["description"],
                        {**(context or {}), **understanding}
                    )
                else:
                    understanding = {}
                    reasoning = ""
                
                # Stage 3: Code - Execute structured actions
                if use_code_for_execution:
                    execution_result = self.code_executor.execute(
                        task=structured_task,
                        understanding=understanding,
                        reasoning=reasoning,
                        context=context
                    )
                else:
                    execution_result = {"status": "skipped", "result": None}
                
                # Stage 4: LLM - Generate ideas if execution needs alternatives
                if execution_result.get("status") == "failed" and use_llm_for_reasoning:
                    ideas = await self.llm_reasoner.generate_ideas(
                        problem=execution_result.get("error", "Execution failed"),
                        constraints=structured_task.get("constraints", [])
                    )
                    execution_result["alternative_ideas"] = ideas
                
                # Stage 5: Code - Validate results
                validation_result = self.code_executor.validate(execution_result.get("result"))
                
                if span:
                    add_span_attributes(
                        decision_success=validation_result,
                        used_llm=use_llm_for_reasoning,
                        used_code=use_code_for_execution
                    )
                
                return {
                    "status": "success" if validation_result else "failed",
                    "task": structured_task,
                    "understanding": understanding,
                    "reasoning": reasoning,
                    "execution": execution_result,
                    "validation": validation_result,
                    "metadata": {
                        "used_llm": use_llm_for_reasoning,
                        "used_code": use_code_for_execution
                    }
                }
                
            except Exception as e:
                if span:
                    add_span_attributes(decision_error=str(e))
                logger.error(f"Hybrid decision error: {e}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                    "metadata": {}
                }
    
    def _structure_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Structure task using code logic
        
        Code responsibility: Structure, validation, parsing
        """
        # Extract task components
        task_lower = task.lower()
        
        # Determine task type
        task_type = "general"
        if any(keyword in task_lower for keyword in ["generate", "create", "write"]):
            task_type = "generation"
        elif any(keyword in task_lower for keyword in ["analyze", "examine", "review"]):
            task_type = "analysis"
        elif any(keyword in task_lower for keyword in ["execute", "run", "perform"]):
            task_type = "execution"
        elif any(keyword in task_lower for keyword in ["plan", "strategy", "design"]):
            task_type = "planning"
        
        # Extract constraints from context
        constraints = []
        if context:
            if "constraints" in context:
                constraints = context["constraints"]
            if "requirements" in context:
                constraints.extend(context.get("requirements", []))
        
        # Validate task structure
        if not task or len(task.strip()) == 0:
            raise ValueError("Task description cannot be empty")
        
        return {
            "description": task,
            "type": task_type,
            "constraints": constraints,
            "structured": True
        }


class StructuredCodeExecutor(CodeExecutor):
    """
    Example implementation of CodeExecutor
    Handles structured operations
    """
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute structured code logic"""
        task = kwargs.get("task", {})
        understanding = kwargs.get("understanding", {})
        reasoning = kwargs.get("reasoning", "")
        context = kwargs.get("context", {})
        
        # Code responsibility: Execute structured operations
        # This is where tool calls, database operations, etc. happen
        
        return {
            "status": "success",
            "result": {
                "task_type": task.get("type"),
                "processed": True
            },
            "metadata": {
                "execution_method": "code"
            }
        }
    
    def validate(self, result: Any) -> bool:
        """Validate result using code logic"""
        if not result:
            return False
        
        if isinstance(result, dict):
            return result.get("processed", False)
        
        return True


class NaturalLanguageReasoner(LLMReasoner):
    """
    Example implementation of LLMReasoner
    Handles natural language reasoning
    """
    
    async def reason(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Perform reasoning using LLM"""
        with self.tracer.start_as_current_span("llm_reasoner.reason") as span:
            try:
                context_str = ""
                if context:
                    context_str = f"\n\nContext: {json.dumps(context, indent=2)}"
                
                full_prompt = f"{prompt}{context_str}\n\nReason about this task and provide your reasoning."
                
                response = await self.ollama_client.generate(
                    prompt=full_prompt,
                    task_type=None,
                    temperature=0.7
                )
                
                result_text = response.response if hasattr(response, "response") else str(response)
                
                if span:
                    add_span_attributes(reasoning_length=len(result_text))
                
                return result_text
                
            except Exception as e:
                logger.error(f"LLM reasoning error: {e}", exc_info=True)
                return f"Reasoning error: {e}"
    
    async def understand(self, text: str) -> Dict[str, Any]:
        """Understand natural language using LLM"""
        with self.tracer.start_as_current_span("llm_reasoner.understand") as span:
            try:
                prompt = f"""Understand this text and extract key information:

{text}

Provide JSON response:
{{
    "main_topic": "...",
    "key_points": ["...", "..."],
    "intent": "...",
    "entities": ["...", "..."]
}}"""
                
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    task_type=None,
                    temperature=0.3
                )
                
                response_text = response.response if hasattr(response, "response") else str(response)
                
                # Try to extract JSON
                import re
                json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                
                return {
                    "main_topic": "unknown",
                    "key_points": [],
                    "intent": "unknown",
                    "entities": []
                }
                
            except Exception as e:
                logger.error(f"LLM understanding error: {e}", exc_info=True)
                return {
                    "main_topic": "error",
                    "key_points": [],
                    "intent": "error",
                    "entities": []
                }
    
    async def generate_ideas(
        self,
        problem: str,
        constraints: Optional[List[str]] = None
    ) -> List[str]:
        """Generate ideas using LLM"""
        with self.tracer.start_as_current_span("llm_reasoner.generate_ideas") as span:
            try:
                constraints_str = ""
                if constraints:
                    constraints_str = f"\n\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints)
                
                prompt = f"""Generate alternative solutions for this problem:

{problem}{constraints_str}

Provide a list of ideas, one per line."""
                
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    task_type=None,
                    temperature=0.8
                )
                
                response_text = response.response if hasattr(response, "response") else str(response)
                
                # Extract ideas (one per line)
                ideas = [
                    line.strip()
                    for line in response_text.split("\n")
                    if line.strip() and not line.strip().startswith("#")
                ]
                
                if span:
                    add_span_attributes(ideas_generated=len(ideas))
                
                return ideas[:10]  # Limit to 10 ideas
                
            except Exception as e:
                logger.error(f"LLM idea generation error: {e}", exc_info=True)
                return []


# Factory function for creating hybrid decision maker
def create_hybrid_decision_maker(
    code_executor: Optional[CodeExecutor] = None,
    llm_reasoner: Optional[LLMReasoner] = None,
    ollama_client: Optional[OllamaClient] = None
) -> HybridDecisionMaker:
    """
    Factory function to create HybridDecisionMaker with default implementations
    
    Args:
        code_executor: Custom code executor (uses StructuredCodeExecutor if not provided)
        llm_reasoner: Custom LLM reasoner (uses NaturalLanguageReasoner if not provided)
        ollama_client: OllamaClient instance
        
    Returns:
        HybridDecisionMaker instance
    """
    if code_executor is None:
        code_executor = StructuredCodeExecutor()
    
    if llm_reasoner is None:
        llm_reasoner = NaturalLanguageReasoner(ollama_client)
    
    return HybridDecisionMaker(
        code_executor=code_executor,
        llm_reasoner=llm_reasoner,
        ollama_client=ollama_client
    )

