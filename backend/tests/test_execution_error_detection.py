"""
Tests for execution error detection and classification
"""
import pytest
from app.core.execution_error_types import (
    ExecutionErrorDetector,
    ExecutionError,
    ErrorSeverity,
    ErrorCategory,
    requires_replanning,
    detect_execution_error
)


class TestExecutionErrorDetection:
    """Tests for execution error detection"""
    
    def test_critical_plan_structure_error(self):
        """Test detection of critical plan structure errors"""
        error = detect_execution_error("Plan has no steps")
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.LOGIC
        assert error.requires_replanning is True
    
    def test_critical_dependency_error(self):
        """Test detection of critical dependency errors"""
        error = detect_execution_error("Dependency step_1 not found in execution context")
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.DEPENDENCY
        assert error.requires_replanning is True
    
    def test_critical_environment_error(self):
        """Test detection of critical environment errors"""
        error = detect_execution_error("No suitable model found for code execution")
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.ENVIRONMENT
        assert error.requires_replanning is True
    
    def test_high_severity_agent_error(self):
        """Test detection of high severity agent errors"""
        error = detect_execution_error("Agent test-agent not found")
        
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.DEPENDENCY
        assert error.requires_replanning is True
    
    def test_high_severity_validation_error(self):
        """Test detection of high severity validation errors"""
        error = detect_execution_error("Function call validation failed: missing parameter 'code'")
        
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.VALIDATION
        assert error.requires_replanning is True
    
    def test_timeout_error(self):
        """Test detection of timeout errors"""
        error = detect_execution_error("Step execution timeout after 300 seconds")
        
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.TIMEOUT
        assert error.requires_replanning is True
    
    def test_timeout_after_retries(self):
        """Test timeout becomes critical after multiple retries"""
        error = detect_execution_error(
            "Step execution timeout after 300 seconds",
            context={"retry_count": 3}
        )
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.TIMEOUT
        assert error.requires_replanning is True
    
    def test_medium_severity_unknown_error(self):
        """Test unknown errors default to medium severity"""
        error = detect_execution_error("Some random error occurred")
        
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.category == ErrorCategory.UNKNOWN
        assert error.requires_replanning is False
    
    def test_requires_replanning_function(self):
        """Test requires_replanning convenience function"""
        assert requires_replanning("Plan has no steps") is True
        assert requires_replanning("Dependency not found") is True
        assert requires_replanning("Some random error") is False
    
    def test_error_with_context(self):
        """Test error detection with context"""
        context = {
            "step_id": "step_1",
            "step_index": 0,
            "plan_id": "test-plan-id",
            "plan_version": 1
        }
        error = detect_execution_error(
            "Dependency step_0 not found",
            context=context
        )
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.DEPENDENCY
        assert "step_id" in error.metadata
        assert error.metadata["step_id"] == "step_1"
    
    def test_error_with_type(self):
        """Test error detection with error type"""
        error = detect_execution_error(
            "Invalid parameter value",
            error_type="ValueError",
            context={"parameter": "timeout"}
        )
        
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.VALIDATION
    
    def test_error_to_dict(self):
        """Test error serialization to dictionary"""
        error = detect_execution_error("Plan has no steps")
        error_dict = error.to_dict()
        
        assert "message" in error_dict
        assert "severity" in error_dict
        assert "category" in error_dict
        assert "requires_replanning" in error_dict
        assert "metadata" in error_dict
        assert error_dict["severity"] == "critical"
        assert error_dict["requires_replanning"] is True
    
    def test_case_insensitive_patterns(self):
        """Test that patterns are case-insensitive"""
        error1 = detect_execution_error("PLAN HAS NO STEPS")
        error2 = detect_execution_error("plan has no steps")
        error3 = detect_execution_error("Plan Has No Steps")
        
        assert error1.severity == ErrorSeverity.CRITICAL
        assert error2.severity == ErrorSeverity.CRITICAL
        assert error3.severity == ErrorSeverity.CRITICAL
    
    def test_multiple_pattern_matching(self):
        """Test that first matching pattern is used"""
        # This should match dependency pattern before unknown
        error = detect_execution_error("Missing required dependency: database connection")
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.DEPENDENCY
    
    def test_resource_error_detection(self):
        """Test resource constraint error detection"""
        error = detect_execution_error("Memory limit exceeded during execution")
        
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.RESOURCE
        assert error.requires_replanning is True
    
    def test_circular_dependency_error(self):
        """Test circular dependency detection"""
        error = detect_execution_error("Circular dependency detected between step_1 and step_2")
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.DEPENDENCY
        assert error.requires_replanning is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

