"""
Code Execution Sandbox for safe code execution
Provides isolated execution environment with resource limits and safety checks
"""
import subprocess
import tempfile
import os
import signal
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

# resource module is Unix-only, handle Windows gracefully
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class CodeExecutionSandbox:
    """
    Sandbox for safe code execution with:
    - Resource limits (timeout, memory)
    - Safety validation
    - Isolated execution environment
    """
    
    # Default resource limits
    DEFAULT_TIMEOUT_SECONDS = 30
    DEFAULT_MEMORY_LIMIT_MB = 512
    MAX_OUTPUT_SIZE = 10 * 1024 * 1024  # 10MB max output
    
    # Dangerous operations to block
    DANGEROUS_IMPORTS = [
        "os.system", "subprocess", "eval", "exec", "__import__",
        "open", "file", "input", "raw_input", "compile"
    ]
    
    DANGEROUS_KEYWORDS = [
        "import os", "import subprocess", "import sys",
        "__file__", "__import__", "eval(", "exec("
    ]
    
    def __init__(self):
        """Initialize Code Execution Sandbox"""
        pass
    
    def execute_code_safely(
        self,
        code: str,
        language: str = "python",
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute code safely in sandbox
        
        Args:
            code: Code to execute
            language: Programming language (python, javascript, etc.)
            constraints: Optional constraints (timeout, memory_limit, etc.)
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Validate code safety first
            safety_result = self.validate_code_safety(code, language)
            if not safety_result["is_safe"]:
                return {
                    "status": "error",
                    "output": "",
                    "error": f"Code safety validation failed: {', '.join(safety_result['issues'])}",
                    "error_type": "safety_validation_failed"
                }
            
            # Apply constraints
            timeout = constraints.get("timeout", self.DEFAULT_TIMEOUT_SECONDS) if constraints else self.DEFAULT_TIMEOUT_SECONDS
            memory_limit = constraints.get("memory_limit", self.DEFAULT_MEMORY_LIMIT_MB) if constraints else self.DEFAULT_MEMORY_LIMIT_MB
            
            # Execute based on language
            if language.lower() == "python":
                return self._execute_python(code, timeout, memory_limit)
            else:
                return {
                    "status": "error",
                    "output": "",
                    "error": f"Unsupported language: {language}",
                    "error_type": "unsupported_language"
                }
                
        except Exception as e:
            logger.error(f"Error executing code in sandbox: {e}", exc_info=True)
            return {
                "status": "error",
                "output": "",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def validate_code_safety(
        self,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Validate code safety before execution
        
        Args:
            code: Code to validate
            language: Programming language
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        if not code or not code.strip():
            return {
                "is_safe": False,
                "issues": ["Code is empty"]
            }
        
        code_lower = code.lower()
        
        # Check for dangerous imports
        for dangerous in self.DANGEROUS_IMPORTS:
            if dangerous.lower() in code_lower:
                issues.append(f"Potentially dangerous import/operation: {dangerous}")
        
        # Check for dangerous keywords
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword.lower() in code_lower:
                issues.append(f"Potentially dangerous keyword: {keyword}")
        
        # Check for file system access
        if any(op in code_lower for op in ["open(", "file(", "__file__"]):
            issues.append("File system access detected - ensure sandbox is properly isolated")
        
        # Check for network access (basic check)
        if any(op in code_lower for op in ["socket", "urllib", "requests", "http"]):
            issues.append("Network access detected - ensure sandbox blocks network")
        
        is_safe = len(issues) == 0
        
        return {
            "is_safe": is_safe,
            "issues": issues
        }
    
    def _execute_python(
        self,
        code: str,
        timeout: int,
        memory_limit_mb: int
    ) -> Dict[str, Any]:
        """
        Execute Python code in isolated environment
        
        Args:
            code: Python code to execute
            timeout: Timeout in seconds
            memory_limit_mb: Memory limit in MB
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Create temporary file for code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                # Set up resource limits (Unix only)
                def set_limits():
                    if HAS_RESOURCE:
                        try:
                            # Set memory limit (RSS - Resident Set Size)
                            memory_bytes = memory_limit_mb * 1024 * 1024
                            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                        except (ValueError, OSError) as e:
                            logger.warning(f"Could not set memory limit: {e}")
                
                # Execute with timeout
                try:
                    # Use preexec_fn only on Unix systems
                    preexec_fn = set_limits if (os.name != 'nt' and HAS_RESOURCE) else None
                    
                    result = subprocess.run(
                        ["python", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        preexec_fn=preexec_fn,
                        env={**os.environ, "PYTHONUNBUFFERED": "1"}
                    )
                    
                    # Limit output size
                    stdout = result.stdout[:self.MAX_OUTPUT_SIZE] if result.stdout else ""
                    stderr = result.stderr[:self.MAX_OUTPUT_SIZE] if result.stderr else ""
                    
                    return {
                        "status": "success" if result.returncode == 0 else "error",
                        "output": stdout,
                        "error": stderr if result.returncode != 0 else None,
                        "return_code": result.returncode,
                        "execution_time_ms": None  # Could be calculated if needed
                    }
                    
                except subprocess.TimeoutExpired:
                    return {
                        "status": "error",
                        "output": "",
                        "error": f"Execution timeout after {timeout} seconds",
                        "error_type": "timeout"
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "output": "",
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Could not delete temporary file {temp_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in Python execution: {e}", exc_info=True)
            return {
                "status": "error",
                "output": "",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def apply_resource_limits(
        self,
        timeout: Optional[int] = None,
        memory_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Apply resource limits (for documentation/preparation)
        
        Args:
            timeout: Timeout in seconds
            memory_limit: Memory limit in MB
            
        Returns:
            Dictionary with applied limits
        """
        return {
            "timeout_seconds": timeout or self.DEFAULT_TIMEOUT_SECONDS,
            "memory_limit_mb": memory_limit or self.DEFAULT_MEMORY_LIMIT_MB,
            "max_output_size_bytes": self.MAX_OUTPUT_SIZE
        }

