"""
Uncertainty types and levels enums
"""
from enum import Enum


class UncertaintyLevel(str, Enum):
    """Levels of uncertainty in user queries"""
    NONE = "none"  # Clear and unambiguous
    LOW = "low"  # Minor ambiguity, can be resolved automatically
    MEDIUM = "medium"  # Moderate ambiguity, may need clarification
    HIGH = "high"  # Significant ambiguity, requires clarification
    CRITICAL = "critical"  # Cannot proceed without clarification


class UncertaintyType(str, Enum):
    """Types of uncertainty"""
    AMBIGUOUS_INTENT = "ambiguous_intent"  # Unclear user intent
    MISSING_CONTEXT = "missing_context"  # Missing required context
    MULTIPLE_INTERPRETATIONS = "multiple_interpretations"  # Multiple valid interpretations
    VAGUE_REQUIREMENTS = "vague_requirements"  # Vague or incomplete requirements
    CONFLICTING_INFORMATION = "conflicting_information"  # Conflicting information in query
    UNKNOWN_ENTITY = "unknown_entity"  # Unknown entities (names, references)
    TEMPORAL_UNCERTAINTY = "temporal_uncertainty"  # Unclear time references
    SCOPE_UNCERTAINTY = "scope_uncertainty"  # Unclear scope or boundaries

