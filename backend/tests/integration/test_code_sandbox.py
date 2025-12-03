"""
Integration tests for CodeExecutionSandbox
"""
import pytest
from app.services.code_execution_sandbox import CodeExecutionSandbox


def test_validate_code_safety_safe():
    """Test validation of safe code"""
    sandbox = CodeExecutionSandbox()
    
    safe_code = """
def add(a, b):
    return a + b

result = add(1, 2)
print(result)
"""
    
    result = sandbox.validate_code_safety(safe_code, "python")
    
    assert result["is_safe"] is True
    assert len(result["issues"]) == 0


def test_validate_code_safety_dangerous():
    """Test validation of dangerous code"""
    sandbox = CodeExecutionSandbox()
    
    dangerous_code = """
import os
os.system('rm -rf /')
"""
    
    result = sandbox.validate_code_safety(dangerous_code, "python")
    
    assert result["is_safe"] is False
    assert len(result["issues"]) > 0
    assert any("os.system" in issue.lower() for issue in result["issues"])


def test_validate_code_safety_empty():
    """Test validation of empty code"""
    sandbox = CodeExecutionSandbox()
    
    result = sandbox.validate_code_safety("", "python")
    
    assert result["is_safe"] is False
    assert "empty" in result["issues"][0].lower()


def test_execute_code_safely_simple():
    """Test executing simple safe code"""
    sandbox = CodeExecutionSandbox()
    
    code = """
result = 2 + 2
print(result)
"""
    
    result = sandbox.execute_code_safely(code, "python")
    
    assert result["status"] == "success"
    assert "4" in result["output"]


def test_execute_code_safely_with_error():
    """Test executing code that raises an error"""
    sandbox = CodeExecutionSandbox()
    
    code = """
x = 1 / 0
"""
    
    result = sandbox.execute_code_safely(code, "python")
    
    # Should execute but return error status
    assert result["status"] == "error"
    assert result["error"] is not None


def test_execute_code_safely_dangerous_blocked():
    """Test that dangerous code is blocked"""
    sandbox = CodeExecutionSandbox()
    
    dangerous_code = """
import os
os.system('echo dangerous')
"""
    
    result = sandbox.execute_code_safely(dangerous_code, "python")
    
    assert result["status"] == "error"
    assert "safety" in result["error"].lower() or "validation" in result["error"].lower()


def test_execute_code_safely_with_timeout():
    """Test code execution with timeout"""
    sandbox = CodeExecutionSandbox()
    
    code = """
import time
time.sleep(60)  # Sleep for 60 seconds
"""
    
    result = sandbox.execute_code_safely(
        code,
        "python",
        constraints={"timeout": 2}  # 2 second timeout
    )
    
    # Should timeout
    assert result["status"] == "error"
    assert "timeout" in result["error"].lower() or result.get("error_type") == "timeout"


def test_apply_resource_limits():
    """Test applying resource limits"""
    sandbox = CodeExecutionSandbox()
    
    limits = sandbox.apply_resource_limits(timeout=60, memory_limit=1024)
    
    assert limits["timeout_seconds"] == 60
    assert limits["memory_limit_mb"] == 1024
    assert "max_output_size_bytes" in limits


def test_execute_code_safely_unsupported_language():
    """Test executing code in unsupported language"""
    sandbox = CodeExecutionSandbox()
    
    result = sandbox.execute_code_safely("console.log('test')", "javascript")
    
    assert result["status"] == "error"
    assert "unsupported" in result["error"].lower()

