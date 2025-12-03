"""
Reflection Service for analyzing failures and generating fixes
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes
from app.core.ollama_client import OllamaClient
from app.services.memory_service import MemoryService

logger = LoggingConfig.get_logger(__name__)


class ReflectionResult:
    """Result of reflection analysis"""
    def __init__(
        self,
        analysis: Dict[str, Any],
        suggested_fix: Optional[Dict[str, Any]],
        similar_situations: List[Dict[str, Any]],
        improvements: List[str]
    ):
        self.analysis = analysis
        self.suggested_fix = suggested_fix
        self.similar_situations = similar_situations
        self.improvements = improvements
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis": self.analysis,
            "suggested_fix": self.suggested_fix,
            "similar_situations": self.similar_situations,
            "improvements": self.improvements
        }


class ReflectionService:
    """Service for analyzing failures and generating fixes"""
    
    def __init__(
        self,
        db: Session = None,
        ollama_client: Optional[OllamaClient] = None,
        memory_service: Optional[MemoryService] = None
    ):
        """
        Initialize Reflection Service
        
        Args:
            db: Database session (optional)
            ollama_client: OllamaClient for generating fixes (optional)
            memory_service: MemoryService for searching similar situations (optional)
        """
        self.db = db or SessionLocal()
        self.ollama_client = ollama_client or OllamaClient()
        self.memory_service = memory_service or MemoryService(self.db)
        self.tracer = get_tracer(__name__)
    
    async def analyze_failure(
        self,
        task_description: str,
        error: str,
        context: Optional[Dict[str, Any]] = None,
        agent_id: Optional[UUID] = None
    ) -> ReflectionResult:
        """
        Analyze a failure to understand what went wrong
        
        Args:
            task_description: Original task description
            error: Error message or failure description
            context: Execution context
            agent_id: Agent ID for memory search
            
        Returns:
            ReflectionResult with analysis
        """
        with self.tracer.start_as_current_span("reflection.analyze_failure") as span:
            try:
                # 1. Analyze error context
                error_analysis = self._analyze_error_context(error, context)
                
                # 2. Search for similar situations in memory
                similar_situations = []
                if agent_id:
                    similar_situations = await self._find_similar_situations(
                        task_description, error, agent_id
                    )
                
                # 3. Generate analysis using LLM
                llm_analysis = await self._llm_analyze_failure(
                    task_description, error, context, similar_situations
                )
                
                # Combine analyses
                analysis = {
                    "error_type": error_analysis.get("error_type", "unknown"),
                    "error_category": error_analysis.get("category", "unknown"),
                    "root_cause": llm_analysis.get("root_cause", "Unknown"),
                    "contributing_factors": llm_analysis.get("contributing_factors", []),
                    "error_context": error_analysis,
                    "llm_insights": llm_analysis
                }
                
                if span:
                    add_span_attributes(
                        error_type=analysis["error_type"],
                        similar_situations_found=len(similar_situations)
                    )
                
                return ReflectionResult(
                    analysis=analysis,
                    suggested_fix=None,  # Will be generated separately
                    similar_situations=similar_situations,
                    improvements=[]
                )
                
            except Exception as e:
                if span:
                    add_span_attributes(reflection_error=str(e))
                logger.error(f"Error analyzing failure: {e}", exc_info=True)
                return ReflectionResult(
                    analysis={"error": str(e)},
                    suggested_fix=None,
                    similar_situations=[],
                    improvements=[]
                )
    
    def _analyze_error_context(
        self,
        error: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze error context to extract information"""
        error_lower = error.lower()
        
        # Detect error type
        error_type = "unknown"
        if "timeout" in error_lower or "timed out" in error_lower:
            error_type = "timeout"
        elif "permission" in error_lower or "access" in error_lower or "forbidden" in error_lower:
            error_type = "permission"
        elif "not found" in error_lower or "missing" in error_lower:
            error_type = "not_found"
        elif "invalid" in error_lower or "bad" in error_lower:
            error_type = "invalid_input"
        elif "connection" in error_lower or "network" in error_lower:
            error_type = "network"
        elif "syntax" in error_lower or "parse" in error_lower:
            error_type = "syntax"
        elif "type" in error_lower and "error" in error_lower:
            error_type = "type_error"
        elif "attribute" in error_lower and "error" in error_lower:
            error_type = "attribute_error"
        elif "key" in error_lower and "error" in error_lower:
            error_type = "key_error"
        elif "value" in error_lower and "error" in error_lower:
            error_type = "value_error"
        elif "index" in error_lower and "error" in error_lower:
            error_type = "index_error"
        
        # Categorize
        category = "runtime"
        if error_type in ["syntax", "type_error", "attribute_error", "key_error", "value_error", "index_error"]:
            category = "code"
        elif error_type in ["timeout", "network", "connection"]:
            category = "infrastructure"
        elif error_type in ["permission", "not_found"]:
            category = "access"
        
        return {
            "error_type": error_type,
            "category": category,
            "error_message": error,
            "context": context or {}
        }
    
    async def _find_similar_situations(
        self,
        task_description: str,
        error: str,
        agent_id: UUID
    ) -> List[Dict[str, Any]]:
        """Find similar failure situations in memory"""
        try:
            # Search for similar failures in memory
            similar_memories = self.memory_service.search_memories(
                agent_id=agent_id,
                query_text=f"{task_description} {error}",
                memory_type="experience",
                limit=5
            )
            
            # Filter for failures
            failures = [
                m for m in similar_memories
                if m.content and m.content.get("success") is False
            ]
            
            return [m.to_dict() for m in failures]
        except Exception as e:
            logger.warning(f"Error finding similar situations: {e}")
            return []
    
    async def _llm_analyze_failure(
        self,
        task_description: str,
        error: str,
        context: Optional[Dict[str, Any]],
        similar_situations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use LLM to analyze failure"""
        prompt = f"""Analyze this failure:

Task: {task_description}
Error: {error}
Context: {context or {}}

"""
        
        if similar_situations:
            prompt += f"\nSimilar past failures:\n"
            for i, situation in enumerate(similar_situations[:3], 1):
                prompt += f"{i}. {situation.get('summary', 'N/A')}\n"
        
        prompt += """
Provide analysis in JSON format:
{
    "root_cause": "explanation",
    "contributing_factors": ["factor1", "factor2"],
    "severity": "low|medium|high",
    "preventable": true/false
}"""
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                task_type=None,
                temperature=0.3
            )
            
            response_text = response.response if hasattr(response, "response") else str(response)
            
            # Try to extract JSON
            import json
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            return {
                "root_cause": "Could not parse LLM analysis",
                "contributing_factors": [],
                "severity": "medium",
                "preventable": True
            }
        except Exception as e:
            logger.warning(f"LLM analysis error: {e}")
            return {
                "root_cause": f"LLM analysis failed: {e}",
                "contributing_factors": [],
                "severity": "medium",
                "preventable": True
            }
    
    async def generate_fix(
        self,
        task_description: str,
        error: str,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        similar_situations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a fix for the failure
        
        Args:
            task_description: Original task description
            error: Error message
            analysis: Failure analysis
            context: Execution context
            similar_situations: Similar past situations
            
        Returns:
            Suggested fix dictionary
        """
        with self.tracer.start_as_current_span("reflection.generate_fix") as span:
            try:
                # Use LLM to generate fix
                fix = await self._llm_generate_fix(
                    task_description, error, analysis, context, similar_situations
                )
                
                if span:
                    add_span_attributes(fix_generated=True)
                
                return fix
                
            except Exception as e:
                if span:
                    add_span_attributes(fix_error=str(e))
                logger.error(f"Error generating fix: {e}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"Could not generate fix: {e}",
                    "suggested_changes": []
                }
    
    async def _llm_generate_fix(
        self,
        task_description: str,
        error: str,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        similar_situations: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Use LLM to generate fix"""
        prompt = f"""Generate a fix for this failure:

Task: {task_description}
Error: {error}
Root Cause: {analysis.get('root_cause', 'Unknown')}
Contributing Factors: {', '.join(analysis.get('contributing_factors', []))}
Context: {context or {}}

"""
        
        if similar_situations:
            prompt += "\nHow similar failures were fixed:\n"
            for i, situation in enumerate(similar_situations[:2], 1):
                prompt += f"{i}. {situation.get('summary', 'N/A')}\n"
        
        prompt += """
Provide fix in JSON format:
{
    "status": "success",
    "message": "explanation",
    "suggested_changes": [
        {"action": "change X", "reason": "because Y"}
    ],
    "alternative_approach": "description if applicable"
}"""
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                task_type=None,
                temperature=0.5
            )
            
            response_text = response.response if hasattr(response, "response") else str(response)
            
            # Extract JSON
            import json
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            return {
                "status": "partial",
                "message": "Could not parse LLM fix",
                "suggested_changes": []
            }
        except Exception as e:
            logger.warning(f"LLM fix generation error: {e}")
            return {
                "status": "error",
                "message": f"LLM fix generation failed: {e}",
                "suggested_changes": []
            }
    
    async def suggest_improvement(
        self,
        task_description: str,
        result: Any,
        execution_metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Suggest improvements for future executions
        
        Args:
            task_description: Task description
            result: Execution result
            execution_metadata: Execution metadata (time, resources, etc.)
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Analyze execution metadata
        if execution_metadata:
            execution_time = execution_metadata.get("execution_time")
            if execution_time and execution_time > 60:  # More than 60 seconds
                suggestions.append("Consider optimizing execution time")
            
            memory_used = execution_metadata.get("memory_used")
            if memory_used and memory_used > 1000:  # More than 1GB
                suggestions.append("Consider reducing memory usage")
        
        # Analyze result quality
        if isinstance(result, str):
            if len(result) < 50:
                suggestions.append("Result may be too brief, consider providing more detail")
            if "TODO" in result or "FIXME" in result:
                suggestions.append("Result contains placeholder text, ensure completion")
        
        return suggestions
    
    async def learn_from_mistake(
        self,
        agent_id: UUID,
        task_description: str,
        error: str,
        fix: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> bool:
        """
        Save learning from mistake to memory
        
        Args:
            agent_id: Agent ID
            task_description: Task description
            error: Error message
            fix: Applied fix
            analysis: Failure analysis
            
        Returns:
            True if saved successfully
        """
        try:
            # Save as pattern in memory
            self.memory_service.save_memory(
                agent_id=agent_id,
                memory_type="pattern",
                content={
                    "task_type": task_description,
                    "error_type": analysis.get("error_type", "unknown"),
                    "error": error,
                    "fix": fix,
                    "root_cause": analysis.get("root_cause", "Unknown")
                },
                summary=f"Learned pattern: {analysis.get('error_type', 'error')} -> {fix.get('message', 'fix')}",
                importance=0.8,  # High importance for learning
                tags=["learning", "pattern", "fix"],
                source="reflection_service"
            )
            
            logger.info(
                f"Saved learning from mistake for agent {agent_id}",
                extra={
                    "agent_id": str(agent_id),
                    "error_type": analysis.get("error_type")
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Error saving learning: {e}", exc_info=True)
            return False

