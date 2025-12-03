"""
Critic Service for validating and assessing execution results
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import json
import re

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes
from app.core.ollama_client import OllamaClient

logger = LoggingConfig.get_logger(__name__)


class ValidationResult:
    """Result of validation"""
    def __init__(
        self,
        is_valid: bool,
        score: float,
        issues: List[str],
        validation_type: str
    ):
        self.is_valid = is_valid
        self.score = score  # 0.0 to 1.0
        self.issues = issues
        self.validation_type = validation_type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "issues": self.issues,
            "validation_type": self.validation_type
        }


class CriticService:
    """Service for validating and assessing execution results"""
    
    def __init__(self, db: Session = None, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize Critic Service
        
        Args:
            db: Database session (optional)
            ollama_client: OllamaClient for semantic validation (optional)
        """
        self.db = db or SessionLocal()
        self.ollama_client = ollama_client or OllamaClient()
        self.tracer = get_tracer(__name__)
    
    async def validate_result(
        self,
        result: Any,
        expected_format: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None,
        task_description: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate execution result
        
        Args:
            result: Execution result to validate
            expected_format: Expected format/schema
            requirements: Task requirements
            task_description: Original task description
            
        Returns:
            ValidationResult
        """
        with self.tracer.start_as_current_span("critic.validate_result") as span:
            try:
                all_issues = []
                scores = []
                
                # 1. Structural validation
                structural_result = self._validate_structure(result, expected_format)
                all_issues.extend(structural_result.issues)
                scores.append(structural_result.score)
                
                # 2. Semantic validation
                semantic_result = await self._validate_semantic(
                    result, task_description, requirements
                )
                all_issues.extend(semantic_result.issues)
                scores.append(semantic_result.score)
                
                # 3. Functional validation (if applicable)
                functional_result = self._validate_functional(result, requirements)
                all_issues.extend(functional_result.issues)
                scores.append(functional_result.score)
                
                # 4. Quality assessment
                quality_result = self._assess_quality(result, requirements)
                all_issues.extend(quality_result.issues)
                scores.append(quality_result.score)
                
                # Calculate overall score (weighted average)
                overall_score = sum(scores) / len(scores) if scores else 0.0
                is_valid = overall_score >= 0.6 and len(all_issues) == 0
                
                if span:
                    add_span_attributes(
                        validation_valid=is_valid,
                        validation_score=overall_score,
                        validation_issues_count=len(all_issues)
                    )
                
                return ValidationResult(
                    is_valid=is_valid,
                    score=overall_score,
                    issues=all_issues,
                    validation_type="comprehensive"
                )
                
            except Exception as e:
                if span:
                    add_span_attributes(validation_error=str(e))
                logger.error(f"Error validating result: {e}", exc_info=True)
                return ValidationResult(
                    is_valid=False,
                    score=0.0,
                    issues=[f"Validation error: {str(e)}"],
                    validation_type="error"
                )
    
    def _validate_structure(
        self,
        result: Any,
        expected_format: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Structural validation (format, schema)
        
        Args:
            result: Result to validate
            expected_format: Expected format/schema
            
        Returns:
            ValidationResult
        """
        issues = []
        score = 1.0
        
        if expected_format:
            # Check if result matches expected format
            if isinstance(expected_format, dict):
                if not isinstance(result, dict):
                    issues.append("Result is not a dictionary as expected")
                    score = 0.3
                else:
                    # Check required fields
                    required_fields = expected_format.get("required", [])
                    for field in required_fields:
                        if field not in result:
                            issues.append(f"Missing required field: {field}")
                            score -= 0.2
                    
                    # Check field types
                    properties = expected_format.get("properties", {})
                    for field, schema in properties.items():
                        if field in result:
                            expected_type = schema.get("type")
                            actual_type = type(result[field]).__name__
                            
                            type_mapping = {
                                "string": "str",
                                "integer": "int",
                                "number": ("int", "float"),
                                "boolean": "bool",
                                "array": "list",
                                "object": "dict"
                            }
                            
                            if expected_type in type_mapping:
                                expected_python_types = type_mapping[expected_type]
                                if isinstance(expected_python_types, tuple):
                                    if actual_type not in expected_python_types:
                                        issues.append(
                                            f"Field '{field}' has wrong type: "
                                            f"expected {expected_type}, got {actual_type}"
                                        )
                                        score -= 0.1
                                else:
                                    if actual_type != expected_python_types:
                                        issues.append(
                                            f"Field '{field}' has wrong type: "
                                            f"expected {expected_type}, got {actual_type}"
                                        )
                                        score -= 0.1
        else:
            # Basic structure checks
            if result is None:
                issues.append("Result is None")
                score = 0.0
            elif isinstance(result, str) and len(result.strip()) == 0:
                issues.append("Result is empty string")
                score = 0.2
            elif isinstance(result, (dict, list)) and len(result) == 0:
                issues.append("Result is empty")
                score = 0.3
        
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=score,
            issues=issues,
            validation_type="structural"
        )
    
    async def _validate_semantic(
        self,
        result: Any,
        task_description: Optional[str],
        requirements: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Semantic validation (meaning, task alignment)
        
        Args:
            result: Result to validate
            task_description: Original task description
            requirements: Task requirements
            
        Returns:
            ValidationResult
        """
        issues = []
        score = 1.0
        
        if not task_description:
            return ValidationResult(
                is_valid=True,
                score=1.0,
                issues=[],
                validation_type="semantic"
            )
        
        # Convert result to string for analysis
        result_str = str(result)
        
        # Basic semantic checks
        if task_description:
            task_lower = task_description.lower()
            result_lower = result_str.lower()
            
            # Check for error indicators
            error_keywords = ["error", "failed", "exception", "traceback", "none"]
            if any(keyword in result_lower for keyword in error_keywords):
                issues.append("Result contains error indicators")
                score -= 0.5
            
            # Check if result seems relevant to task
            # Simple keyword matching (can be enhanced with LLM)
            task_keywords = set(word.lower() for word in task_description.split() if len(word) > 3)
            result_keywords = set(word.lower() for word in result_str.split() if len(word) > 3)
            
            if task_keywords and result_keywords:
                overlap = len(task_keywords & result_keywords)
                if overlap == 0:
                    issues.append("Result doesn't seem related to task")
                    score -= 0.3
                elif overlap < len(task_keywords) * 0.3:
                    issues.append("Result has limited relevance to task")
                    score -= 0.2
        
        # Use LLM for deeper semantic validation if available
        if self.ollama_client and task_description:
            try:
                semantic_check = await self._llm_semantic_check(result_str, task_description)
                if not semantic_check.get("relevant", True):
                    issues.append(semantic_check.get("reason", "Result not semantically relevant"))
                    score -= 0.3
            except Exception as e:
                logger.warning(f"LLM semantic check failed: {e}")
        
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=score,
            issues=issues,
            validation_type="semantic"
        )
    
    async def _llm_semantic_check(self, result: str, task_description: str) -> Dict[str, Any]:
        """Use LLM to check semantic relevance"""
        prompt = f"""Task: {task_description}

Result: {result[:500]}

Is this result relevant and correct for the task? Respond with JSON:
{{"relevant": true/false, "reason": "explanation"}}"""
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                task_type=None,
                temperature=0.3
            )
            
            # Try to parse JSON response
            response_text = response.response if hasattr(response, "response") else str(response)
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                result_dict = json.loads(json_match.group())
                return result_dict
            
            return {"relevant": True, "reason": "Could not parse LLM response"}
        except Exception as e:
            logger.warning(f"LLM semantic check error: {e}")
            return {"relevant": True, "reason": f"LLM check failed: {e}"}
    
    def _validate_functional(
        self,
        result: Any,
        requirements: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Functional validation (does it work?)
        
        Args:
            result: Result to validate
            requirements: Task requirements
            
        Returns:
            ValidationResult
        """
        issues = []
        score = 1.0
        
        if requirements:
            # Check functional requirements
            must_contain = requirements.get("must_contain")
            if must_contain:
                result_str = str(result).lower()
                for item in must_contain:
                    if item.lower() not in result_str:
                        issues.append(f"Result must contain: {item}")
                        score -= 0.3
            
            must_not_contain = requirements.get("must_not_contain")
            if must_not_contain:
                result_str = str(result).lower()
                for item in must_not_contain:
                    if item.lower() in result_str:
                        issues.append(f"Result must not contain: {item}")
                        score -= 0.3
            
            min_length = requirements.get("min_length")
            if min_length:
                result_str = str(result)
                if len(result_str) < min_length:
                    issues.append(f"Result too short (minimum {min_length} characters)")
                    score -= 0.2
            
            max_length = requirements.get("max_length")
            if max_length:
                result_str = str(result)
                if len(result_str) > max_length:
                    issues.append(f"Result too long (maximum {max_length} characters)")
                    score -= 0.1
        
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=score,
            issues=issues,
            validation_type="functional"
        )
    
    def _assess_quality(
        self,
        result: Any,
        requirements: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Quality assessment (metrics-based)
        
        Args:
            result: Result to assess
            requirements: Task requirements
            
        Returns:
            ValidationResult
        """
        issues = []
        score = 1.0
        
        result_str = str(result)
        
        # Quality metrics
        if len(result_str) == 0:
            issues.append("Empty result")
            score = 0.0
        elif len(result_str) < 10:
            issues.append("Result too short")
            score -= 0.3
        
        # Check for common quality issues
        if isinstance(result, str):
            # Check for placeholder text
            placeholders = ["TODO", "FIXME", "XXX", "placeholder"]
            if any(ph in result.upper() for ph in placeholders):
                issues.append("Result contains placeholder text")
                score -= 0.2
            
            # Check for incomplete sentences
            if result.count(".") == 0 and len(result) > 50:
                issues.append("Result may be incomplete (no sentence endings)")
                score -= 0.1
        
        # Check requirements-based quality
        if requirements:
            quality_threshold = requirements.get("quality_threshold", 0.7)
            if score < quality_threshold:
                issues.append(f"Quality below threshold ({quality_threshold})")
        
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            is_valid=score >= 0.7,
            score=score,
            issues=issues,
            validation_type="quality"
        )
    
    async def assess_quality(
        self,
        result: Any,
        requirements: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Assess quality of result (0.0 to 1.0)
        
        Args:
            result: Result to assess
            requirements: Quality requirements
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        quality_result = self._assess_quality(result, requirements)
        return quality_result.score
    
    def check_requirements(
        self,
        result: Any,
        requirements: Dict[str, Any]
    ) -> ValidationResult:
        """
        Check if result meets requirements
        
        Args:
            result: Result to check
            requirements: Requirements dictionary
            
        Returns:
            ValidationResult
        """
        return self._validate_functional(result, requirements)
    
    def identify_issues(
        self,
        result: Any,
        expected_format: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Identify issues in result
        
        Args:
            result: Result to analyze
            expected_format: Expected format
            requirements: Requirements
            
        Returns:
            List of issue descriptions
        """
        structural = self._validate_structure(result, expected_format)
        functional = self._validate_functional(result, requirements)
        quality = self._assess_quality(result, requirements)
        
        all_issues = structural.issues + functional.issues + quality.issues
        return all_issues

