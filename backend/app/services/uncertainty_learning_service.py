"""
Uncertainty Learning Service for learning and adapting uncertainty parameters
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.ollama_client import OllamaClient, TaskType
from app.core.tracing import add_span_attributes, get_tracer
from app.models.uncertainty_parameters import (ParameterType,
                                               UncertaintyParameter)
from app.models.uncertainty_types import UncertaintyType
from app.services.meta_learning_service import MetaLearningService
from sqlalchemy import and_
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class UncertaintyLearningService:
    """
    Service for learning and adapting uncertainty assessment parameters.
    
    Handles:
    - Learning from feedback
    - Adapting weights and thresholds
    - Updating keyword lists using LLM
    - A/B testing parameter changes
    """
    
    def __init__(self, db: Session, ollama_client: Optional[OllamaClient] = None):
        self.db = db
        self.ollama_client = ollama_client
        self.meta_learning = MetaLearningService(db)
        self.tracer = get_tracer(__name__)
    
    async def learn_from_feedback(
        self,
        assessment: Dict[str, Any],
        actual_outcome: str,  # "correct", "over_escalated", "under_escalated", "missed"
        user_feedback: Optional[Dict[str, Any]] = None,
        task_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Learn from feedback about uncertainty assessment.
        
        Args:
            assessment: Original uncertainty assessment
            actual_outcome: What actually happened
            user_feedback: Optional user feedback
            task_result: Optional task execution result
            
        Returns:
            Learning result with parameter updates
        """
        with self.tracer.start_as_current_span("uncertainty_learning.learn_from_feedback") as span:
            add_span_attributes(
                span=span,
                uncertainty_level=assessment.get("uncertainty_level"),
                actual_outcome=actual_outcome
            )
            
            learning_result = {
                "parameters_updated": [],
                "improvements": [],
                "learned_at": datetime.now(timezone.utc).isoformat()
            }
            
            uncertainty_score = assessment.get("uncertainty_score", 0.0)
            uncertainty_level = assessment.get("uncertainty_level", "none")
            uncertainty_types = assessment.get("uncertainty_types", [])
            
            # Analyze feedback and determine parameter adjustments
            if actual_outcome == "over_escalated":
                # System was too cautious - reduce weights/thresholds
                learning_result["improvements"].append("Reducing sensitivity due to over-escalation")
                await self._adjust_parameters_for_over_escalation(uncertainty_types, uncertainty_score, learning_result)
                
            elif actual_outcome == "under_escalated":
                # System was not cautious enough - increase weights/thresholds
                learning_result["improvements"].append("Increasing sensitivity due to under-escalation")
                await self._adjust_parameters_for_under_escalation(uncertainty_types, uncertainty_score, learning_result)
                
            elif actual_outcome == "missed":
                # System missed uncertainty - need to improve detection
                learning_result["improvements"].append("Improving detection due to missed uncertainty")
                await self._improve_detection(uncertainty_types, assessment, learning_result)
                
            elif actual_outcome == "correct":
                # System was correct - reinforce current parameters
                learning_result["improvements"].append("Reinforcing parameters due to correct assessment")
                await self._reinforce_parameters(uncertainty_types, learning_result)
            
            # Update performance metrics
            await self._update_performance_metrics(uncertainty_types, actual_outcome)
            
            logger.info(
                f"Learned from feedback: {actual_outcome}",
                extra={
                    "actual_outcome": actual_outcome,
                    "parameters_updated": len(learning_result["parameters_updated"]),
                    "uncertainty_level": uncertainty_level
                }
            )
            
            return learning_result
    
    async def _adjust_parameters_for_over_escalation(
        self,
        uncertainty_types: List[str],
        uncertainty_score: float,
        learning_result: Dict[str, Any]
    ) -> None:
        """Adjust parameters when system over-escalated"""
        # Reduce weights for detected types
        for uncertainty_type in uncertainty_types:
            param_name = f"weight_{uncertainty_type}"
            param = self._get_or_create_parameter(param_name, ParameterType.WEIGHT)
            
            current_weight = param.get_value() or self._get_default_weight(uncertainty_type)
            # Reduce by 10% (but not below 0.05)
            new_weight = max(0.05, current_weight * 0.9)
            
            param.set_value(new_weight)
            param.add_to_history(
                value=new_weight,
                reason=f"Reduced due to over-escalation (was {current_weight:.3f})",
                metrics={"previous_value": current_weight, "reduction_percent": 10}
            )
            self.db.add(param)
            learning_result["parameters_updated"].append({
                "parameter": param_name,
                "old_value": current_weight,
                "new_value": new_weight,
                "change": "reduced"
            })
        
        # Increase thresholds (make it harder to escalate)
        threshold_params = [
            ("threshold_critical", 0.7),
            ("threshold_high", 0.5),
            ("threshold_medium", 0.3)
        ]
        
        for param_name, default_threshold in threshold_params:
            if uncertainty_score >= default_threshold:
                param = self._get_or_create_parameter(param_name, ParameterType.THRESHOLD)
                current_threshold = param.get_value() or default_threshold
                # Increase by 5% (but not above 0.95)
                new_threshold = min(0.95, current_threshold * 1.05)
                
                param.set_value(new_threshold)
                param.add_to_history(
                    value=new_threshold,
                    reason=f"Increased due to over-escalation (was {current_threshold:.3f})",
                    metrics={"previous_value": current_threshold, "increase_percent": 5}
                )
                self.db.add(param)
                learning_result["parameters_updated"].append({
                    "parameter": param_name,
                    "old_value": current_threshold,
                    "new_value": new_threshold,
                    "change": "increased"
                })
        
        self.db.commit()
    
    async def _adjust_parameters_for_under_escalation(
        self,
        uncertainty_types: List[str],
        uncertainty_score: float,
        learning_result: Dict[str, Any]
    ) -> None:
        """Adjust parameters when system under-escalated"""
        # Increase weights for detected types
        for uncertainty_type in uncertainty_types:
            param_name = f"weight_{uncertainty_type}"
            param = self._get_or_create_parameter(param_name, ParameterType.WEIGHT)
            
            current_weight = param.get_value() or self._get_default_weight(uncertainty_type)
            # Increase by 10% (but not above 0.5)
            new_weight = min(0.5, current_weight * 1.1)
            
            param.set_value(new_weight)
            param.add_to_history(
                value=new_weight,
                reason=f"Increased due to under-escalation (was {current_weight:.3f})",
                metrics={"previous_value": current_weight, "increase_percent": 10}
            )
            self.db.add(param)
            learning_result["parameters_updated"].append({
                "parameter": param_name,
                "old_value": current_weight,
                "new_value": new_weight,
                "change": "increased"
            })
        
        # Decrease thresholds (make it easier to escalate)
        threshold_params = [
            ("threshold_critical", 0.7),
            ("threshold_high", 0.5),
            ("threshold_medium", 0.3)
        ]
        
        for param_name, default_threshold in threshold_params:
            if uncertainty_score < default_threshold:
                param = self._get_or_create_parameter(param_name, ParameterType.THRESHOLD)
                current_threshold = param.get_value() or default_threshold
                # Decrease by 5% (but not below 0.1)
                new_threshold = max(0.1, current_threshold * 0.95)
                
                param.set_value(new_threshold)
                param.add_to_history(
                    value=new_threshold,
                    reason=f"Decreased due to under-escalation (was {current_threshold:.3f})",
                    metrics={"previous_value": current_threshold, "decrease_percent": 5}
                )
                self.db.add(param)
                learning_result["parameters_updated"].append({
                    "parameter": param_name,
                    "old_value": current_threshold,
                    "new_value": new_threshold,
                    "change": "decreased"
                })
        
        self.db.commit()
    
    async def _improve_detection(
        self,
        uncertainty_types: List[str],
        assessment: Dict[str, Any],
        learning_result: Dict[str, Any]
    ) -> None:
        """Improve detection when uncertainty was missed"""
        # This would involve analyzing the query and updating keyword lists
        # For now, we'll increase weights for all types to be more sensitive
        all_types = [
            UncertaintyType.AMBIGUOUS_INTENT.value,
            UncertaintyType.MISSING_CONTEXT.value,
            UncertaintyType.MULTIPLE_INTERPRETATIONS.value,
            UncertaintyType.VAGUE_REQUIREMENTS.value,
            UncertaintyType.CONFLICTING_INFORMATION.value,
            UncertaintyType.UNKNOWN_ENTITY.value,
            UncertaintyType.TEMPORAL_UNCERTAINTY.value,
            UncertaintyType.SCOPE_UNCERTAINTY.value,
        ]
        
        for uncertainty_type in all_types:
            param_name = f"weight_{uncertainty_type}"
            param = self._get_or_create_parameter(param_name, ParameterType.WEIGHT)
            
            current_weight = param.get_value() or self._get_default_weight(uncertainty_type)
            # Small increase to improve detection
            new_weight = min(0.5, current_weight * 1.05)
            
            param.set_value(new_weight)
            param.add_to_history(
                value=new_weight,
                reason=f"Improved detection sensitivity (was {current_weight:.3f})",
                metrics={"previous_value": current_weight}
            )
            self.db.add(param)
        
        self.db.commit()
    
    async def _reinforce_parameters(
        self,
        uncertainty_types: List[str],
        learning_result: Dict[str, Any]
    ) -> None:
        """Reinforce parameters when assessment was correct"""
        # Update performance metrics to show these parameters are working well
        for uncertainty_type in uncertainty_types:
            param_name = f"weight_{uncertainty_type}"
            param = self._get_or_create_parameter(param_name, ParameterType.WEIGHT)
            
            # Update performance metrics
            current_metrics = param.performance_metrics or {}
            correct_count = current_metrics.get("correct_count", 0) + 1
            total_count = current_metrics.get("total_count", 0) + 1
            accuracy = correct_count / total_count if total_count > 0 else 1.0
            
            param.update_performance_metrics({
                "correct_count": correct_count,
                "total_count": total_count,
                "accuracy": accuracy
            })
            self.db.add(param)
        
        self.db.commit()
    
    async def _update_performance_metrics(
        self,
        uncertainty_types: List[str],
        actual_outcome: str
    ) -> None:
        """Update performance metrics for all parameters"""
        for uncertainty_type in uncertainty_types:
            param_name = f"weight_{uncertainty_type}"
            param = self._get_or_create_parameter(param_name, ParameterType.WEIGHT)
            
            current_metrics = param.performance_metrics or {}
            total_count = current_metrics.get("total_count", 0) + 1
            correct_count = current_metrics.get("correct_count", 0)
            
            if actual_outcome == "correct":
                correct_count += 1
            
            accuracy = correct_count / total_count if total_count > 0 else 0.0
            
            param.update_performance_metrics({
                "total_count": total_count,
                "correct_count": correct_count,
                "accuracy": accuracy,
                "last_outcome": actual_outcome
            })
            self.db.add(param)
        
        self.db.commit()
    
    async def update_keyword_lists_with_llm(
        self,
        uncertainty_type: str,
        historical_queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use LLM to update keyword lists based on historical data.
        
        Args:
            uncertainty_type: Type of uncertainty (e.g., "ambiguous_intent")
            historical_queries: List of queries with their uncertainty assessments
            
        Returns:
            Update result with new keywords
        """
        if not self.ollama_client:
            logger.warning("OllamaClient not available, cannot update keyword lists with LLM")
            return {"updated": False, "reason": "ollama_client_not_available"}
        
        with self.tracer.start_as_current_span("uncertainty_learning.update_keywords") as span:
            add_span_attributes(span=span, uncertainty_type=uncertainty_type)
            
            # Get current keyword list
            param_name = f"keywords_{uncertainty_type}"
            param = self._get_or_create_parameter(param_name, ParameterType.KEYWORD_LIST)
            current_keywords = param.get_value() or []
            
            # Prepare prompt for LLM
            prompt = f"""На основе следующих исторических запросов и их оценок неопределенности, предложи обновленный список ключевых слов для обнаружения типа неопределенности: {uncertainty_type}

Текущий список ключевых слов: {json.dumps(current_keywords, ensure_ascii=False)}

Примеры запросов с этим типом неопределенности:
{json.dumps(historical_queries[:10], ensure_ascii=False, indent=2)}

Предложи:
1. Новые ключевые слова, которые следует добавить
2. Ключевые слова, которые следует удалить (если они дают ложные срабатывания)
3. Обновленный полный список

Верни только JSON в формате:
{{
    "keywords_to_add": ["слово1", "слово2"],
    "keywords_to_remove": ["слово3"],
    "updated_list": ["полный", "список", "ключевых", "слов"]
}}"""
            
            try:
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    system_prompt="Ты эксперт по анализу текста и обнаружению неопределенности. Предлагай точные и эффективные ключевые слова.",
                    task_type=TaskType.REASONING,
                    temperature=0.3
                )
                
                # Parse LLM response
                response_text = response.response.strip()
                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                response_text = response_text.strip()
                
                llm_suggestions = json.loads(response_text)
                
                # Update parameter
                new_keywords = llm_suggestions.get("updated_list", current_keywords)
                old_keywords = current_keywords.copy()
                
                param.set_value(new_keywords)
                param.add_to_history(
                    value=new_keywords,
                    reason=f"Updated via LLM: added {len(llm_suggestions.get('keywords_to_add', []))}, removed {len(llm_suggestions.get('keywords_to_remove', []))}",
                    metrics={
                        "keywords_added": llm_suggestions.get("keywords_to_add", []),
                        "keywords_removed": llm_suggestions.get("keywords_to_remove", []),
                        "old_count": len(old_keywords),
                        "new_count": len(new_keywords)
                    }
                )
                self.db.add(param)
                self.db.commit()
                
                logger.info(
                    f"Updated keyword list for {uncertainty_type} via LLM",
                    extra={
                        "uncertainty_type": uncertainty_type,
                        "old_count": len(old_keywords),
                        "new_count": len(new_keywords),
                        "keywords_added": len(llm_suggestions.get("keywords_to_add", []))
                    }
                )
                
                return {
                    "updated": True,
                    "old_keywords": old_keywords,
                    "new_keywords": new_keywords,
                    "changes": llm_suggestions
                }
                
            except Exception as e:
                logger.error(f"Failed to update keyword list with LLM: {e}", exc_info=True)
                return {"updated": False, "reason": str(e)}
    
    def _get_or_create_parameter(
        self,
        parameter_name: str,
        parameter_type: ParameterType,
        default_value: Optional[Any] = None
    ) -> UncertaintyParameter:
        """Get or create a parameter"""
        param = self.db.query(UncertaintyParameter).filter(
            UncertaintyParameter.parameter_name == parameter_name
        ).first()
        
        if not param:
            param = UncertaintyParameter(
                parameter_name=parameter_name,
                parameter_type=parameter_type,
                description=f"Parameter for {parameter_name}"
            )
            if default_value is not None:
                param.set_value(default_value)
            self.db.add(param)
            self.db.commit()
            self.db.refresh(param)
        
        return param
    
    def _get_default_weight(self, uncertainty_type: str) -> float:
        """Get default weight for uncertainty type"""
        defaults = {
            UncertaintyType.AMBIGUOUS_INTENT.value: 0.2,
            UncertaintyType.MISSING_CONTEXT.value: 0.15,
            UncertaintyType.MULTIPLE_INTERPRETATIONS.value: 0.25,
            UncertaintyType.VAGUE_REQUIREMENTS.value: 0.15,
            UncertaintyType.CONFLICTING_INFORMATION.value: 0.3,
            UncertaintyType.UNKNOWN_ENTITY.value: 0.1,
            UncertaintyType.TEMPORAL_UNCERTAINTY.value: 0.1,
            UncertaintyType.SCOPE_UNCERTAINTY.value: 0.15,
        }
        return defaults.get(uncertainty_type, 0.15)

