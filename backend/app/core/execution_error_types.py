"""
Execution error classification and detection
"""
import re
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    CRITICAL = "critical"  # Requires replanning
    HIGH = "high"  # May require replanning
    MEDIUM = "medium"  # Retry or continue
    LOW = "low"  # Non-fatal, can continue


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    ENVIRONMENT = "environment"  # Environment/infrastructure issues
    DEPENDENCY = "dependency"  # Missing dependencies or resources
    VALIDATION = "validation"  # Validation/format errors
    LOGIC = "logic"  # Logic errors in plan/step
    TIMEOUT = "timeout"  # Timeout errors
    RESOURCE = "resource"  # Resource constraints
    UNKNOWN = "unknown"  # Unclassified errors


class ExecutionError:
    """Represents an execution error with classification"""
    
    def __init__(
        self,
        message: str,
        error_type: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_type = error_type
        self.severity = severity
        self.category = category
        self.metadata = metadata or {}
        self.requires_replanning = severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "message": self.message,
            "error_type": self.error_type,
            "severity": self.severity.value,
            "category": self.category.value,
            "requires_replanning": self.requires_replanning,
            "metadata": self.metadata
        }


class ExecutionErrorDetector:
    """Detects and classifies execution errors"""
    
    # Patterns for critical errors
    CRITICAL_PATTERNS = [
        # Plan structure errors
        (r"plan.*has.*no.*steps", ErrorCategory.LOGIC, ErrorSeverity.CRITICAL),
        (r"invalid.*plan.*structure", ErrorCategory.LOGIC, ErrorSeverity.CRITICAL),
        (r"plan.*validation.*failed", ErrorCategory.VALIDATION, ErrorSeverity.CRITICAL),
        
        # Dependency errors
        (r"dependency.*not.*found", ErrorCategory.DEPENDENCY, ErrorSeverity.CRITICAL),
        (r"missing.*required.*dependency", ErrorCategory.DEPENDENCY, ErrorSeverity.CRITICAL),
        (r"circular.*dependency", ErrorCategory.DEPENDENCY, ErrorSeverity.CRITICAL),
        
        # Environment errors
        (r"no.*suitable.*model.*found", ErrorCategory.ENVIRONMENT, ErrorSeverity.CRITICAL),
        (r"no.*server.*found", ErrorCategory.ENVIRONMENT, ErrorSeverity.CRITICAL),
        (r"database.*connection.*failed", ErrorCategory.ENVIRONMENT, ErrorSeverity.CRITICAL),
        
        # Logic errors that invalidate plan
        (r"invalid.*step.*sequence", ErrorCategory.LOGIC, ErrorSeverity.CRITICAL),
        (r"contradictory.*steps", ErrorCategory.LOGIC, ErrorSeverity.CRITICAL),
    ]
    
    # Patterns for high severity errors (may require replanning)
    HIGH_PATTERNS = [
        # Agent/tool errors
        (r"agent.*not.*found", ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH),
        (r"tool.*not.*found", ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH),
        (r"agent.*not.*active", ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH),
        (r"tool.*not.*active", ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH),
        
        # Validation errors
        (r"function.*call.*validation.*failed", ErrorCategory.VALIDATION, ErrorSeverity.HIGH),
        (r"invalid.*parameters", ErrorCategory.VALIDATION, ErrorSeverity.HIGH),
        (r"missing.*required.*parameter", ErrorCategory.VALIDATION, ErrorSeverity.HIGH),
        
        # Resource errors
        (r"memory.*limit.*exceeded", ErrorCategory.RESOURCE, ErrorSeverity.HIGH),
        (r"resource.*unavailable", ErrorCategory.RESOURCE, ErrorSeverity.HIGH),
    ]
    
    # Patterns for timeout errors
    TIMEOUT_PATTERNS = [
        (r"timeout", ErrorCategory.TIMEOUT, ErrorSeverity.HIGH),
        (r"execution.*timeout", ErrorCategory.TIMEOUT, ErrorSeverity.HIGH),
        (r"request.*timeout", ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM),
    ]
    
    @classmethod
    def detect_error(
        cls,
        error_message: str,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionError:
        """
        Detect and classify an execution error
        
        Args:
            error_message: Error message
            error_type: Optional error type/class name
            context: Optional context (step, plan info, etc.)
            
        Returns:
            Classified ExecutionError
        """
        error_lower = error_message.lower()
        context = context or {}
        
        # Check critical patterns
        for pattern, category, severity in cls.CRITICAL_PATTERNS:
            if re.search(pattern, error_lower, re.IGNORECASE):
                return ExecutionError(
                    message=error_message,
                    error_type=error_type,
                    severity=severity,
                    category=category,
                    metadata={"detected_by_pattern": pattern, **context}
                )
        
        # Check high severity patterns
        for pattern, category, severity in cls.HIGH_PATTERNS:
            if re.search(pattern, error_lower, re.IGNORECASE):
                return ExecutionError(
                    message=error_message,
                    error_type=error_type,
                    severity=severity,
                    category=category,
                    metadata={"detected_by_pattern": pattern, **context}
                )
        
        # Check timeout patterns
        for pattern, category, severity in cls.TIMEOUT_PATTERNS:
            if re.search(pattern, error_lower, re.IGNORECASE):
                # Timeouts may be critical if context suggests it
                final_severity = severity
                if context.get("retry_count", 0) >= 2:
                    final_severity = ErrorSeverity.CRITICAL
                
                return ExecutionError(
                    message=error_message,
                    error_type=error_type,
                    severity=final_severity,
                    category=category,
                    metadata={"detected_by_pattern": pattern, **context}
                )
        
        # Check for specific error types
        if error_type:
            if "ValueError" in error_type or "TypeError" in error_type:
                # Check if it's a critical ValueError
                if any(keyword in error_lower for keyword in ["not found", "invalid", "missing"]):
                    return ExecutionError(
                        message=error_message,
                        error_type=error_type,
                        severity=ErrorSeverity.HIGH,
                        category=ErrorCategory.VALIDATION,
                        metadata={**context}
                    )
        
        # Default classification
        return ExecutionError(
            message=error_message,
            error_type=error_type,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.UNKNOWN,
            metadata={**context}
        )
    
    @classmethod
    def requires_replanning(
        cls,
        error_message: str,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Quick check if error requires replanning
        
        Args:
            error_message: Error message
            error_type: Optional error type
            context: Optional context
            
        Returns:
            True if replanning is required
        """
        error = cls.detect_error(error_message, error_type, context)
        return error.requires_replanning
    
    @classmethod
    def is_critical_error(
        cls,
        error_message: str,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if error is critical
        
        Args:
            error_message: Error message
            error_type: Optional error type
            context: Optional context
            
        Returns:
            True if error is critical
        """
        error = cls.detect_error(error_message, error_type, context)
        return error.severity == ErrorSeverity.CRITICAL


def detect_execution_error(
    error_message: str,
    error_type: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> ExecutionError:
    """
    Convenience function to detect execution error
    
    Args:
        error_message: Error message
        error_type: Optional error type/class name
        context: Optional context
        
    Returns:
        Classified ExecutionError
    """
    return ExecutionErrorDetector.detect_error(error_message, error_type, context)


def requires_replanning(
    error_message: str,
    error_type: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Convenience function to check if replanning is required
    
    Args:
        error_message: Error message
        error_type: Optional error type
        context: Optional context
        
    Returns:
        True if replanning is required
    """
    return ExecutionErrorDetector.requires_replanning(error_message, error_type, context)

