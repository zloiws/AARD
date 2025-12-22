"""
Uncertainty Handling Service for assessing and handling uncertainty in user queries
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.ollama_client import OllamaClient, TaskType
from app.core.tracing import add_span_attributes, get_tracer
from app.models.task import Task
from app.models.uncertainty_parameters import (ParameterType,
                                               UncertaintyParameter)
from app.models.uncertainty_types import UncertaintyLevel, UncertaintyType
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)

# Lazy import to avoid circular dependency
UncertaintyLearningService = None


class UncertaintyService:
    """
    Service for assessing and handling uncertainty in user queries.
    
    Handles:
    - Detection of ambiguity and uncertainty
    - Assessment of uncertainty level
    - Automatic resolution when possible
    - Escalation to human when needed
    - Clarification requests
    """
    
    def __init__(self, db: Session, ollama_client: Optional[OllamaClient] = None):
        self.db = db
        self.ollama_client = ollama_client
        self.tracer = get_tracer(__name__)
        
        # Lazy import to avoid circular dependency
        global UncertaintyLearningService
        if UncertaintyLearningService is None:
            from app.services.uncertainty_learning_service import \
                UncertaintyLearningService as ULS
            UncertaintyLearningService = ULS
        
        self.learning_service = UncertaintyLearningService(db, ollama_client)
        
        # Load parameters from database (lazy loading)
        self._parameters_cache: Dict[str, UncertaintyParameter] = {}
        self._parameters_loaded = False
    
    async def assess_uncertainty(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess uncertainty in a user query.
        
        Args:
            query: User query to assess
            context: Optional context (previous messages, task history, etc.)
            
        Returns:
            Dictionary with uncertainty assessment results
        """
        with self.tracer.start_as_current_span("uncertainty.assess") as span:
            add_span_attributes(span=span, query_length=len(query))
            
            assessment = {
                "query": query,
                "uncertainty_level": UncertaintyLevel.NONE.value,
                "uncertainty_score": 0.0,  # 0.0 to 1.0
                "uncertainty_types": [],
                "issues": [],
                "suggestions": [],
                "requires_clarification": False,
                "can_proceed": True,
                "assessed_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 1. Check for ambiguous intent
            ambiguous_intent = self._check_ambiguous_intent(query)
            if ambiguous_intent["detected"]:
                assessment["uncertainty_types"].append(UncertaintyType.AMBIGUOUS_INTENT.value)
                assessment["issues"].extend(ambiguous_intent["issues"])
                weight = self._get_parameter_value(
                    f"weight_{UncertaintyType.AMBIGUOUS_INTENT.value}",
                    ParameterType.WEIGHT,
                    default=0.2
                )
                assessment["uncertainty_score"] += weight
            
            # 2. Check for missing context
            missing_context = self._check_missing_context(query, context)
            if missing_context["detected"]:
                assessment["uncertainty_types"].append(UncertaintyType.MISSING_CONTEXT.value)
                assessment["issues"].extend(missing_context["issues"])
                weight = self._get_parameter_value(
                    f"weight_{UncertaintyType.MISSING_CONTEXT.value}",
                    ParameterType.WEIGHT,
                    default=0.15
                )
                assessment["uncertainty_score"] += weight
            
            # 3. Check for multiple interpretations
            multiple_interpretations = self._check_multiple_interpretations(query)
            if multiple_interpretations["detected"]:
                assessment["uncertainty_types"].append(UncertaintyType.MULTIPLE_INTERPRETATIONS.value)
                assessment["issues"].extend(multiple_interpretations["issues"])
                assessment["suggestions"].extend(multiple_interpretations["suggestions"])
                weight = self._get_parameter_value(
                    f"weight_{UncertaintyType.MULTIPLE_INTERPRETATIONS.value}",
                    ParameterType.WEIGHT,
                    default=0.25
                )
                assessment["uncertainty_score"] += weight
            
            # 4. Check for vague requirements
            vague_requirements = self._check_vague_requirements(query)
            if vague_requirements["detected"]:
                assessment["uncertainty_types"].append(UncertaintyType.VAGUE_REQUIREMENTS.value)
                assessment["issues"].extend(vague_requirements["issues"])
                weight = self._get_parameter_value(
                    f"weight_{UncertaintyType.VAGUE_REQUIREMENTS.value}",
                    ParameterType.WEIGHT,
                    default=0.15
                )
                assessment["uncertainty_score"] += weight
            
            # 5. Check for conflicting information
            conflicting_info = self._check_conflicting_information(query)
            if conflicting_info["detected"]:
                assessment["uncertainty_types"].append(UncertaintyType.CONFLICTING_INFORMATION.value)
                assessment["issues"].extend(conflicting_info["issues"])
                weight = self._get_parameter_value(
                    f"weight_{UncertaintyType.CONFLICTING_INFORMATION.value}",
                    ParameterType.WEIGHT,
                    default=0.3
                )
                assessment["uncertainty_score"] += weight
            
            # 6. Check for unknown entities
            unknown_entities = self._check_unknown_entities(query, context)
            if unknown_entities["detected"]:
                assessment["uncertainty_types"].append(UncertaintyType.UNKNOWN_ENTITY.value)
                assessment["issues"].extend(unknown_entities["issues"])
                weight = self._get_parameter_value(
                    f"weight_{UncertaintyType.UNKNOWN_ENTITY.value}",
                    ParameterType.WEIGHT,
                    default=0.1
                )
                assessment["uncertainty_score"] += weight
            
            # 7. Check for temporal uncertainty
            temporal_uncertainty = self._check_temporal_uncertainty(query)
            if temporal_uncertainty["detected"]:
                assessment["uncertainty_types"].append(UncertaintyType.TEMPORAL_UNCERTAINTY.value)
                assessment["issues"].extend(temporal_uncertainty["issues"])
                weight = self._get_parameter_value(
                    f"weight_{UncertaintyType.TEMPORAL_UNCERTAINTY.value}",
                    ParameterType.WEIGHT,
                    default=0.1
                )
                assessment["uncertainty_score"] += weight
            
            # 8. Check for scope uncertainty
            scope_uncertainty = self._check_scope_uncertainty(query)
            if scope_uncertainty["detected"]:
                assessment["uncertainty_types"].append(UncertaintyType.SCOPE_UNCERTAINTY.value)
                assessment["issues"].extend(scope_uncertainty["issues"])
                weight = self._get_parameter_value(
                    f"weight_{UncertaintyType.SCOPE_UNCERTAINTY.value}",
                    ParameterType.WEIGHT,
                    default=0.15
                )
                assessment["uncertainty_score"] += weight
            
            # Normalize uncertainty score to 0.0-1.0
            assessment["uncertainty_score"] = min(1.0, assessment["uncertainty_score"])
            
            # Determine uncertainty level using adaptive thresholds
            threshold_critical = self._get_parameter_value("threshold_critical", ParameterType.THRESHOLD, default=0.7)
            threshold_high = self._get_parameter_value("threshold_high", ParameterType.THRESHOLD, default=0.5)
            threshold_medium = self._get_parameter_value("threshold_medium", ParameterType.THRESHOLD, default=0.3)
            threshold_low = self._get_parameter_value("threshold_low", ParameterType.THRESHOLD, default=0.1)
            
            if assessment["uncertainty_score"] >= threshold_critical:
                assessment["uncertainty_level"] = UncertaintyLevel.CRITICAL.value
                assessment["requires_clarification"] = True
                assessment["can_proceed"] = False
            elif assessment["uncertainty_score"] >= threshold_high:
                assessment["uncertainty_level"] = UncertaintyLevel.HIGH.value
                assessment["requires_clarification"] = True
                assessment["can_proceed"] = False
            elif assessment["uncertainty_score"] >= threshold_medium:
                assessment["uncertainty_level"] = UncertaintyLevel.MEDIUM.value
                assessment["requires_clarification"] = True
                assessment["can_proceed"] = True  # Can proceed with assumptions
            elif assessment["uncertainty_score"] >= threshold_low:
                assessment["uncertainty_level"] = UncertaintyLevel.LOW.value
                assessment["requires_clarification"] = False
                assessment["can_proceed"] = True
            else:
                assessment["uncertainty_level"] = UncertaintyLevel.NONE.value
                assessment["requires_clarification"] = False
                assessment["can_proceed"] = True
            
            # Generate clarification questions if needed
            if assessment["requires_clarification"]:
                assessment["clarification_questions"] = await self._generate_clarification_questions(
                    query, assessment
                )
            
            logger.info(
                f"Assessed uncertainty for query: level={assessment['uncertainty_level']}, score={assessment['uncertainty_score']:.2f}",
                extra={
                    "uncertainty_level": assessment["uncertainty_level"],
                    "uncertainty_score": assessment["uncertainty_score"],
                    "types": assessment["uncertainty_types"]
                }
            )
            
            return assessment
    
    async def handle_uncertainty(
        self,
        assessment: Dict[str, Any],
        task: Optional[Task] = None
    ) -> Dict[str, Any]:
        """
        Handle uncertainty based on assessment.
        
        Args:
            assessment: Uncertainty assessment from assess_uncertainty()
            task: Optional task associated with the query
            
        Returns:
            Dictionary with handling actions and results
        """
        with self.tracer.start_as_current_span("uncertainty.handle") as span:
            add_span_attributes(
                span=span,
                uncertainty_level=assessment.get("uncertainty_level"),
                can_proceed=assessment.get("can_proceed", False)
            )
            
            uncertainty_level = assessment.get("uncertainty_level", UncertaintyLevel.NONE.value)
            
            handling_result = {
                "action": "proceed",  # proceed, request_clarification, escalate
                "message": None,
                "clarification_questions": [],
                "assumptions": [],
                "handled_at": datetime.now(timezone.utc).isoformat()
            }
            
            if uncertainty_level == UncertaintyLevel.CRITICAL.value:
                # Critical uncertainty - cannot proceed
                handling_result["action"] = "escalate"
                handling_result["message"] = "Запрос содержит критическую неопределенность. Требуется уточнение перед выполнением."
                handling_result["clarification_questions"] = assessment.get("clarification_questions", [])
                
            elif uncertainty_level == UncertaintyLevel.HIGH.value:
                # High uncertainty - request clarification
                handling_result["action"] = "request_clarification"
                handling_result["message"] = "Запрос содержит неоднозначность. Пожалуйста, уточните следующие моменты:"
                handling_result["clarification_questions"] = assessment.get("clarification_questions", [])
                
            elif uncertainty_level == UncertaintyLevel.MEDIUM.value:
                # Medium uncertainty - proceed with assumptions
                handling_result["action"] = "proceed_with_assumptions"
                handling_result["assumptions"] = await self._generate_assumptions(assessment)
                handling_result["message"] = "Обнаружена неоднозначность. Продолжаю с предположениями. Если что-то не так, пожалуйста, уточните."
                
            elif uncertainty_level == UncertaintyLevel.LOW.value:
                # Low uncertainty - proceed normally, log for review
                handling_result["action"] = "proceed"
                handling_result["message"] = None  # No message needed
                logger.debug(f"Low uncertainty detected, proceeding normally: {assessment.get('issues', [])}")
                
            else:
                # No uncertainty - proceed normally
                handling_result["action"] = "proceed"
                handling_result["message"] = None
            
            return handling_result
    
    def _check_ambiguous_intent(self, query: str) -> Dict[str, Any]:
        """Check for ambiguous user intent"""
        issues = []
        detected = False
        
        query_lower = query.lower()
        
        # Get keyword lists from parameters
        vague_verbs = self._get_parameter_value(
            "keywords_ambiguous_intent_verbs",
            ParameterType.KEYWORD_LIST,
            default=["сделай", "сделать", "do", "make", "обработай", "обработать", "посмотри", "посмотреть"]
        )
        
        question_words = self._get_parameter_value(
            "keywords_ambiguous_intent_questions",
            ParameterType.KEYWORD_LIST,
            default=["что", "как", "когда", "где", "кто", "why", "what", "how", "when", "where", "who"]
        )
        
        action_verbs = self._get_parameter_value(
            "keywords_ambiguous_intent_actions",
            ParameterType.KEYWORD_LIST,
            default=["найти", "find", "получить", "get"]
        )
        
        min_query_length = self._get_parameter_value(
            "threshold_ambiguous_intent_min_length",
            ParameterType.COUNT_THRESHOLD,
            default=5
        )
        
        # Check for vague action verbs
        if any(verb in query_lower for verb in vague_verbs):
            # Check if there's a clear object
            if not any(word in query_lower for word in question_words):
                # Might be ambiguous if no clear object
                if len(query.split()) < min_query_length:
                    issues.append("Неясное намерение: запрос слишком общий")
                    detected = True
        
        # Check for questions without clear subject
        if any(qw in query_lower for qw in question_words):
            # Check if question is complete
            if query.count("?") == 0 and not any(word in query_lower for word in action_verbs):
                issues.append("Неполный вопрос: требуется уточнение")
                detected = True
        
        return {"detected": detected, "issues": issues}
    
    def _check_missing_context(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Check for missing required context"""
        issues = []
        detected = False
        
        query_lower = query.lower()
        
        # Get keyword lists from parameters
        reference_words = self._get_parameter_value(
            "keywords_missing_context_references",
            ParameterType.KEYWORD_LIST,
            default=["это", "этот", "эта", "эти", "тот", "та", "те", "it", "this", "that", "these", "those"]
        )
        
        pronouns = self._get_parameter_value(
            "keywords_missing_context_pronouns",
            ParameterType.KEYWORD_LIST,
            default=["он", "она", "оно", "они", "he", "she", "it", "they"]
        )
        
        temporal_refs = self._get_parameter_value(
            "keywords_missing_context_temporal",
            ParameterType.KEYWORD_LIST,
            default=["предыдущий", "последний", "previous", "last", "прошлый", "past"]
        )
        
        # Check for references that might need context
        if any(ref in query_lower for ref in reference_words):
            # Check if context is available
            if not context or not context.get("previous_messages"):
                issues.append("Отсутствует контекст для ссылок (это, тот, etc.)")
                detected = True
        
        # Check for pronouns without clear antecedent
        if any(pronoun in query_lower for pronoun in pronouns):
            if not context or not context.get("previous_messages"):
                issues.append("Отсутствует контекст для местоимений")
                detected = True
        
        # Check for "previous" or "last" references
        if any(ref in query_lower for ref in temporal_refs):
            if not context or not context.get("task_history"):
                issues.append("Отсутствует история задач для временных ссылок")
                detected = True
        
        return {"detected": detected, "issues": issues}
    
    def _check_multiple_interpretations(self, query: str) -> Dict[str, Any]:
        """Check for multiple valid interpretations"""
        issues = []
        suggestions = []
        detected = False
        
        query_lower = query.lower()
        
        # Get keyword lists from parameters
        alternative_indicators = self._get_parameter_value(
            "keywords_multiple_interpretations_alternatives",
            ParameterType.KEYWORD_LIST,
            default=[" или ", " or "]
        )
        
        ambiguous_conjunctions = self._get_parameter_value(
            "keywords_multiple_interpretations_conjunctions",
            ParameterType.KEYWORD_LIST,
            default=["и/или", "and/or", "может быть", "maybe", "возможно", "possibly"]
        )
        
        action_verbs = self._get_parameter_value(
            "keywords_multiple_interpretations_actions",
            ParameterType.KEYWORD_LIST,
            default=["создать", "create", "найти", "find", "обработать", "process"]
        )
        
        min_list_items = self._get_parameter_value(
            "threshold_multiple_interpretations_min_items",
            ParameterType.COUNT_THRESHOLD,
            default=2
        )
        
        # Check for "or" / "или" - indicates multiple options
        if any(indicator in query_lower for indicator in alternative_indicators):
            issues.append("Запрос содержит альтернативы (или/or)")
            suggestions.append("Уточните, какой вариант предпочтителен")
            detected = True
        
        # Check for ambiguous conjunctions
        if any(ac in query_lower for ac in ambiguous_conjunctions):
            issues.append("Неоднозначные союзы указывают на множественные интерпретации")
            suggestions.append("Уточните точные требования")
            detected = True
        
        # Check for lists without clear action
        if "," in query and query.count(",") >= min_list_items:
            # Multiple items - check if action is clear for all
            if not any(verb in query_lower for verb in action_verbs):
                issues.append("Список элементов без четкого действия")
                suggestions.append("Уточните действие для каждого элемента")
                detected = True
        
        return {"detected": detected, "issues": issues, "suggestions": suggestions}
    
    def _check_vague_requirements(self, query: str) -> Dict[str, Any]:
        """Check for vague or incomplete requirements"""
        issues = []
        detected = False
        
        query_lower = query.lower()
        
        # Get keyword lists from parameters
        vague_quantifiers = self._get_parameter_value(
            "keywords_vague_requirements_quantifiers",
            ParameterType.KEYWORD_LIST,
            default=["несколько", "некоторые", "много", "мало", "some", "several", "many", "few", "a few"]
        )
        
        vague_time = self._get_parameter_value(
            "keywords_vague_requirements_time",
            ParameterType.KEYWORD_LIST,
            default=["скоро", "позже", "потом", "soon", "later", "eventually", "sometime"]
        )
        
        incomplete_indicators = self._get_parameter_value(
            "keywords_vague_requirements_incomplete",
            ParameterType.KEYWORD_LIST,
            default=["...", "и т.д.", "и т.п.", "etc", "etc.", "and so on"]
        )
        
        # Check for vague quantifiers
        if any(vq in query_lower for vq in vague_quantifiers):
            issues.append("Неопределенные количественные указания")
            detected = True
        
        # Check for vague time references
        if any(vt in query_lower for vt in vague_time):
            issues.append("Неопределенные временные указания")
            detected = True
        
        # Check for incomplete requests
        if any(ii in query_lower for ii in incomplete_indicators):
            issues.append("Неполный запрос (использованы многоточия или 'и т.д.')")
            detected = True
        
        return {"detected": detected, "issues": issues}
    
    def _check_conflicting_information(self, query: str) -> Dict[str, Any]:
        """Check for conflicting information in query"""
        issues = []
        detected = False
        
        query_lower = query.lower()
        
        # Get contradiction pairs from parameters (stored as JSON)
        contradictions_param = self._get_parameter_value(
            "keywords_conflicting_information_pairs",
            ParameterType.KEYWORD_LIST,
            default=[
                ["создать", "create"],
                ["удалить", "delete"],
                ["включить", "enable"],
                ["выключить", "disable"],
                ["увеличить", "increase"],
                ["уменьшить", "decrease"],
                ["добавить", "add"],
                ["удалить", "remove"]
            ]
        )
        
        # Reconstruct pairs (assuming even number of items, paired)
        contradictions = []
        if isinstance(contradictions_param, list) and len(contradictions_param) >= 2:
            # Try to pair them
            for i in range(0, len(contradictions_param) - 1, 2):
                if i + 1 < len(contradictions_param):
                    contradictions.append((contradictions_param[i], contradictions_param[i + 1]))
        
        # Fallback to default if structure is wrong
        if not contradictions:
            contradictions = [
                (["создать", "create"], ["удалить", "delete"]),
                (["включить", "enable"], ["выключить", "disable"]),
                (["увеличить", "increase"], ["уменьшить", "decrease"]),
                (["добавить", "add"], ["удалить", "remove"]),
            ]
        
        conflict_indicators = self._get_parameter_value(
            "keywords_conflicting_information_indicators",
            ParameterType.KEYWORD_LIST,
            default=[" но ", " but "]
        )
        
        # Check for contradictory pairs
        for positive, negative in contradictions:
            if isinstance(positive, list) and isinstance(negative, list):
                if any(p in query_lower for p in positive) and any(n in query_lower for n in negative):
                    issues.append(f"Противоречивые действия: {'/'.join(positive)} и {'/'.join(negative)}")
                    detected = True
        
        # Check for conflict indicators
        if any(indicator in query_lower for indicator in conflict_indicators):
            issues.append("Запрос содержит противоречие (но/but)")
            detected = True
        
        return {"detected": detected, "issues": issues}
    
    def _check_unknown_entities(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Check for unknown entities (names, references)"""
        issues = []
        detected = False
        
        # Get threshold from parameters
        max_capitalized_words = self._get_parameter_value(
            "threshold_unknown_entities_max_capitalized",
            ParameterType.COUNT_THRESHOLD,
            default=3
        )
        
        min_word_length = self._get_parameter_value(
            "threshold_unknown_entities_min_length",
            ParameterType.COUNT_THRESHOLD,
            default=2
        )
        
        # This is a simplified check - in production, would use NER or entity recognition
        # Check for capitalized words that might be entities
        words = query.split()
        capitalized_words = [w for w in words if w and w[0].isupper() and len(w) > min_word_length]
        
        if len(capitalized_words) > max_capitalized_words:
            issues.append("Обнаружены потенциально неизвестные сущности (имена, ссылки)")
            detected = True
        
        return {"detected": detected, "issues": issues}
    
    def _check_temporal_uncertainty(self, query: str) -> Dict[str, Any]:
        """Check for unclear time references"""
        issues = []
        detected = False
        
        query_lower = query.lower()
        
        # Get keyword lists from parameters
        relative_time = self._get_parameter_value(
            "keywords_temporal_uncertainty_relative",
            ParameterType.KEYWORD_LIST,
            default=["сегодня", "завтра", "вчера", "today", "tomorrow", "yesterday"]
        )
        
        time_question_words = self._get_parameter_value(
            "keywords_temporal_uncertainty_questions",
            ParameterType.KEYWORD_LIST,
            default=["когда", "when"]
        )
        
        vague_ranges = self._get_parameter_value(
            "keywords_temporal_uncertainty_vague",
            ParameterType.KEYWORD_LIST,
            default=["недавно", "давно", "скоро", "recently", "soon", "long ago"]
        )
        
        # Check for relative time without anchor
        if any(rt in query_lower for rt in relative_time):
            # Check if there's a clear context
            if not any(qw in query_lower for qw in time_question_words):
                # Might be okay if it's a clear request
                pass
            else:
                issues.append("Относительные временные указания без якоря")
                detected = True
        
        # Check for vague time ranges
        if any(vr in query_lower for vr in vague_ranges):
            issues.append("Неопределенные временные диапазоны")
            detected = True
        
        return {"detected": detected, "issues": issues}
    
    def _check_scope_uncertainty(self, query: str) -> Dict[str, Any]:
        """Check for unclear scope or boundaries"""
        issues = []
        detected = False
        
        query_lower = query.lower()
        
        # Get keyword lists from parameters
        scope_words = self._get_parameter_value(
            "keywords_scope_uncertainty_general",
            ParameterType.KEYWORD_LIST,
            default=["все", "all"]
        )
        
        domain_words = self._get_parameter_value(
            "keywords_scope_uncertainty_domains",
            ParameterType.KEYWORD_LIST,
            default=["файлы", "files", "задачи", "tasks", "данные", "data"]
        )
        
        extreme_scope_words = self._get_parameter_value(
            "keywords_scope_uncertainty_extreme",
            ParameterType.KEYWORD_LIST,
            default=["всё", "everything"]
        )
        
        # Check for "all" / "все" without clear domain
        if any(sw in query_lower for sw in scope_words) and not any(word in query_lower for word in domain_words):
            issues.append("Неопределенная область действия ('все' без указания домена)")
            detected = True
        
        # Check for "everything" / "всё"
        if any(esw in query_lower for esw in extreme_scope_words):
            issues.append("Слишком широкий охват ('всё')")
            detected = True
        
        return {"detected": detected, "issues": issues}
    
    async def _generate_clarification_questions(
        self,
        query: str,
        assessment: Dict[str, Any]
    ) -> List[str]:
        """Generate clarification questions based on uncertainty assessment"""
        questions = []
        
        uncertainty_types = assessment.get("uncertainty_types", [])
        issues = assessment.get("issues", [])
        
        # Generate questions based on uncertainty types
        if UncertaintyType.AMBIGUOUS_INTENT.value in uncertainty_types:
            questions.append("Что именно вы хотите сделать?")
        
        if UncertaintyType.MISSING_CONTEXT.value in uncertainty_types:
            questions.append("На что вы ссылаетесь? (это, тот, предыдущий)")
        
        if UncertaintyType.MULTIPLE_INTERPRETATIONS.value in uncertainty_types:
            questions.append("Какой вариант вы предпочитаете?")
        
        if UncertaintyType.VAGUE_REQUIREMENTS.value in uncertainty_types:
            questions.append("Можете уточнить требования? (количество, время, область)")
        
        if UncertaintyType.CONFLICTING_INFORMATION.value in uncertainty_types:
            questions.append("Обнаружено противоречие. Какой вариант правильный?")
        
        if UncertaintyType.UNKNOWN_ENTITY.value in uncertainty_types:
            questions.append("Что означает [сущность]?")
        
        if UncertaintyType.TEMPORAL_UNCERTAINTY.value in uncertainty_types:
            questions.append("Когда именно? (дата, время)")
        
        if UncertaintyType.SCOPE_UNCERTAINTY.value in uncertainty_types:
            questions.append("Какой именно объем данных/задач?")
        
        # If no specific questions, generate generic ones
        if not questions and issues:
            questions.append("Можете уточнить ваш запрос?")
        
        # Get max questions limit from parameters
        max_questions = self._get_parameter_value(
            "threshold_clarification_max_questions",
            ParameterType.COUNT_THRESHOLD,
            default=5
        )
        
        return questions[:max_questions]
    
    async def _generate_assumptions(self, assessment: Dict[str, Any]) -> List[str]:
        """Generate assumptions for medium uncertainty"""
        assumptions = []
        
        uncertainty_types = assessment.get("uncertainty_types", [])
        
        if UncertaintyType.VAGUE_REQUIREMENTS.value in uncertainty_types:
            assumptions.append("Использую разумные значения по умолчанию для неопределенных параметров")
        
        if UncertaintyType.TEMPORAL_UNCERTAINTY.value in uncertainty_types:
            assumptions.append("Использую текущее время как точку отсчета")
        
        if UncertaintyType.SCOPE_UNCERTAINTY.value in uncertainty_types:
            assumptions.append("Ограничиваю область действия разумными пределами")
        
        if UncertaintyType.MISSING_CONTEXT.value in uncertainty_types:
            assumptions.append("Использую доступный контекст, если он есть")
        
        return assumptions
    
    # Parameter management methods
    
    def _get_parameter_value(
        self,
        parameter_name: str,
        parameter_type: ParameterType,
        default: Any = None
    ) -> Any:
        """
        Get parameter value from database or use default.
        
        Args:
            parameter_name: Name of the parameter
            parameter_type: Type of parameter
            default: Default value if parameter doesn't exist
            
        Returns:
            Parameter value or default
        """
        # Lazy load parameters on first access
        if not self._parameters_loaded:
            self._load_parameters()
        
        # Check cache first
        if parameter_name in self._parameters_cache:
            param = self._parameters_cache[parameter_name]
            value = param.get_value()
            if value is not None:
                return value
        
        # Try to load from database
        param = self.db.query(UncertaintyParameter).filter(
            UncertaintyParameter.parameter_name == parameter_name
        ).first()
        
        if param:
            self._parameters_cache[parameter_name] = param
            value = param.get_value()
            if value is not None:
                return value
        
        # If parameter doesn't exist, create it with default value
        if default is not None:
            param = UncertaintyParameter(
                parameter_name=parameter_name,
                parameter_type=parameter_type,
                description=f"Auto-created parameter: {parameter_name}"
            )
            param.set_value(default)
            self.db.add(param)
            self.db.commit()
            self.db.refresh(param)
            self._parameters_cache[parameter_name] = param
            return default
        
        return None
    
    def _load_parameters(self) -> None:
        """Load all parameters from database into cache"""
        params = self.db.query(UncertaintyParameter).all()
        for param in params:
            self._parameters_cache[param.parameter_name] = param
        self._parameters_loaded = True
    
    async def learn_from_feedback(
        self,
        assessment: Dict[str, Any],
        actual_outcome: str,
        user_feedback: Optional[Dict[str, Any]] = None,
        task_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Learn from feedback about uncertainty assessment.
        
        Args:
            assessment: Original uncertainty assessment
            actual_outcome: What actually happened ("correct", "over_escalated", "under_escalated", "missed")
            user_feedback: Optional user feedback
            task_result: Optional task execution result
            
        Returns:
            Learning result
        """
        return await self.learning_service.learn_from_feedback(
            assessment=assessment,
            actual_outcome=actual_outcome,
            user_feedback=user_feedback,
            task_result=task_result
        )
    
    async def update_keyword_lists_with_llm(
        self,
        uncertainty_type: str,
        historical_queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use LLM to update keyword lists based on historical data.
        
        Args:
            uncertainty_type: Type of uncertainty
            historical_queries: List of queries with their assessments
            
        Returns:
            Update result
        """
        return await self.learning_service.update_keyword_lists_with_llm(
            uncertainty_type=uncertainty_type,
            historical_queries=historical_queries
        )

