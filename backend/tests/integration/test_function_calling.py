"""
Integration tests for Function Calling Protocol
"""
import pytest
from app.core.function_calling import FunctionCallProtocol, FunctionCall


def test_create_function_call():
    """Test creating a function call"""
    call = FunctionCallProtocol.create_function_call(
        function_name="code_execution_tool",
        parameters={
            "code": "print('Hello, World!')",
            "language": "python"
        },
        safety_checks=True
    )
    
    assert call.function == "code_execution_tool"
    assert call.parameters["code"] == "print('Hello, World!')"
    assert call.parameters["language"] == "python"
    assert call.safety_checks is True


def test_create_function_call_invalid_name():
    """Test creating function call with invalid name"""
    with pytest.raises(ValueError, match="Function name cannot be empty"):
        FunctionCallProtocol.create_function_call(
            function_name="",
            parameters={}
        )
    
    with pytest.raises(ValueError, match="Invalid function name"):
        FunctionCallProtocol.create_function_call(
            function_name="invalid-function-name!",
            parameters={}
        )


def test_validate_function_call_valid():
    """Test validating a valid function call"""
    call = FunctionCallProtocol.create_function_call(
        function_name="code_execution_tool",
        parameters={
            "code": "print('Hello')",
            "language": "python"
        }
    )
    
    is_valid, issues = FunctionCallProtocol.validate_function_call(call)
    
    assert is_valid is True
    assert len(issues) == 0


def test_validate_function_call_missing_required():
    """Test validating function call with missing required parameters"""
    call = FunctionCallProtocol.create_function_call(
        function_name="code_execution_tool",
        parameters={
            "code": "print('Hello')"
            # Missing "language" parameter
        }
    )
    
    is_valid, issues = FunctionCallProtocol.validate_function_call(call)
    
    assert is_valid is False
    assert any("language" in issue.lower() for issue in issues)


def test_validate_function_call_safety_checks():
    """Test safety checks for dangerous code"""
    call = FunctionCallProtocol.create_function_call(
        function_name="code_execution_tool",
        parameters={
            "code": "import os; os.system('rm -rf /')",
            "language": "python"
        },
        safety_checks=True
    )
    
    is_valid, issues = FunctionCallProtocol.validate_function_call(call)
    
    # Should detect dangerous code
    assert is_valid is False or len(issues) > 0
    assert any("dangerous" in issue.lower() for issue in issues)


def test_parse_function_call_from_llm_json():
    """Test parsing function call from LLM JSON response"""
    llm_response = """{
        "function": "code_execution_tool",
        "parameters": {
            "code": "print('Hello')",
            "language": "python"
        }
    }"""
    
    call = FunctionCallProtocol.parse_function_call_from_llm(llm_response)
    
    assert call is not None
    assert call.function == "code_execution_tool"
    assert call.parameters["code"] == "print('Hello')"
    assert call.parameters["language"] == "python"


def test_parse_function_call_from_llm_with_text():
    """Test parsing function call from LLM response with surrounding text"""
    llm_response = """Here is the function call:
    {
        "function": "code_execution_tool",
        "parameters": {
            "code": "x = 1 + 1",
            "language": "python"
        }
    }
    This will execute the code safely."""
    
    call = FunctionCallProtocol.parse_function_call_from_llm(llm_response)
    
    assert call is not None
    assert call.function == "code_execution_tool"


def test_parse_function_call_from_llm_invalid():
    """Test parsing invalid function call"""
    llm_response = "This is not a valid function call"
    
    call = FunctionCallProtocol.parse_function_call_from_llm(llm_response)
    
    assert call is None


def test_validate_against_schema():
    """Test validation against JSON schema"""
    call = FunctionCallProtocol.create_function_call(
        function_name="code_execution_tool",
        parameters={
            "code": "print('Hello')",
            "language": "python"
        },
        validation_schema={
            "type": "object",
            "required": ["code", "language"],
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"}
            }
        }
    )
    
    is_valid, issues = FunctionCallProtocol.validate_function_call(call)
    
    assert is_valid is True


def test_validate_against_schema_type_mismatch():
    """Test validation with type mismatch"""
    call = FunctionCallProtocol.create_function_call(
        function_name="code_execution_tool",
        parameters={
            "code": 123,  # Should be string
            "language": "python"
        },
        validation_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"}
            }
        }
    )
    
    is_valid, issues = FunctionCallProtocol.validate_function_call(call)
    
    # Should detect type mismatch
    assert is_valid is False or len(issues) > 0


def test_format_function_call_for_llm():
    """Test formatting function call for LLM prompt"""
    call = FunctionCallProtocol.create_function_call(
        function_name="code_execution_tool",
        parameters={
            "code": "print('Hello')",
            "language": "python"
        }
    )
    
    formatted = FunctionCallProtocol.format_function_call_for_llm(call)
    
    assert "code_execution_tool" in formatted
    assert "print('Hello')" in formatted or "print" in formatted
    assert "python" in formatted


def test_function_call_to_dict():
    """Test converting function call to dictionary"""
    call = FunctionCallProtocol.create_function_call(
        function_name="code_execution_tool",
        parameters={"code": "test", "language": "python"}
    )
    
    call_dict = call.to_dict()
    
    assert call_dict["function"] == "code_execution_tool"
    assert call_dict["parameters"]["code"] == "test"
    assert call_dict["safety_checks"] is True

