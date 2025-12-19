"""
Function Calling Protocol for safe code execution
Provides structured interface between planning model and code execution
"""
import json
import re
from typing import Any, Dict, List, Optional

from app.core.logging_config import LoggingConfig
from pydantic import BaseModel, Field, field_validator

logger = LoggingConfig.get_logger(__name__)


class FunctionCall(BaseModel):
    """Structured function call representation"""
    function: str = Field(..., description="Function name to call")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Function parameters")
    validation_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for validation")
    safety_checks: bool = Field(default=True, description="Enable safety checks before execution")
    
    @field_validator('function')
    @classmethod
    def validate_function_name(cls, v: str) -> str:
        """Validate function name"""
        if not v or not v.strip():
            raise ValueError("Function name cannot be empty")
        # Allow alphanumeric, underscore, and dot
        if not re.match(r'^[a-zA-Z0-9_.]+$', v):
            raise ValueError(f"Invalid function name: {v}")
        return v.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "function": self.function,
            "parameters": self.parameters,
            "validation_schema": self.validation_schema,
            "safety_checks": self.safety_checks
        }


class FunctionCallProtocol:
    """
    Protocol for creating, validating, and parsing function calls
    Implements safe interface between planning model and code execution
    """
    
    # Allowed function names (whitelist approach)
    ALLOWED_FUNCTIONS = {
        "code_execution_tool": {
            "description": "Execute Python code in sandbox",
            "required_params": ["code", "language"],
            "optional_params": ["timeout", "memory_limit", "input_data"]
        },
        "file_operations_tool": {
            "description": "Perform file operations",
            "required_params": ["operation", "path"],
            "optional_params": ["content", "mode"]
        },
        "database_query_tool": {
            "description": "Execute database query",
            "required_params": ["query"],
            "optional_params": ["parameters", "timeout"]
        },
        "http_request_tool": {
            "description": "Make HTTP request",
            "required_params": ["url", "method"],
            "optional_params": ["headers", "body", "timeout"]
        }
    }
    
    @staticmethod
    def create_function_call(
        function_name: str,
        parameters: Dict[str, Any],
        validation_schema: Optional[Dict[str, Any]] = None,
        safety_checks: bool = True
    ) -> FunctionCall:
        """
        Create a structured function call
        
        Args:
            function_name: Name of the function to call
            parameters: Function parameters
            validation_schema: Optional JSON schema for parameter validation
            safety_checks: Enable safety checks
            
        Returns:
            FunctionCall instance
            
        Raises:
            ValueError: If function name is not allowed or invalid
        """
        # Validate function name
        if function_name not in FunctionCallProtocol.ALLOWED_FUNCTIONS:
            logger.warning(
                f"Function '{function_name}' not in whitelist, but allowing it",
                extra={"function_name": function_name}
            )
            # Allow unknown functions but log warning
        
        # Create function call
        function_call = FunctionCall(
            function=function_name,
            parameters=parameters,
            validation_schema=validation_schema,
            safety_checks=safety_checks
        )
        
        logger.debug(
            f"Created function call: {function_name}",
            extra={
                "function": function_name,
                "parameters_count": len(parameters)
            }
        )
        
        return function_call
    
    @staticmethod
    def validate_function_call(call: FunctionCall) -> tuple[bool, List[str]]:
        """
        Validate function call before execution
        
        Args:
            call: FunctionCall to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check if function is in whitelist
        if call.function not in FunctionCallProtocol.ALLOWED_FUNCTIONS:
            issues.append(f"Function '{call.function}' is not in allowed list")
            # Don't fail, just warn
        
        # Check required parameters if function is known
        if call.function in FunctionCallProtocol.ALLOWED_FUNCTIONS:
            function_info = FunctionCallProtocol.ALLOWED_FUNCTIONS[call.function]
            required_params = function_info.get("required_params", [])
            
            for param in required_params:
                if param not in call.parameters:
                    issues.append(f"Missing required parameter: {param}")
        
        # Validate against schema if provided
        if call.validation_schema:
            schema_issues = FunctionCallProtocol._validate_against_schema(
                call.parameters,
                call.validation_schema
            )
            issues.extend(schema_issues)
        
        # Safety checks
        if call.safety_checks:
            safety_issues = FunctionCallProtocol._perform_safety_checks(call)
            issues.extend(safety_issues)
        
        is_valid = len(issues) == 0
        
        if not is_valid:
            logger.warning(
                f"Function call validation failed: {call.function}",
                extra={
                    "function": call.function,
                    "issues": issues
                }
            )
        
        return is_valid, issues
    
    @staticmethod
    def _validate_against_schema(
        parameters: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> List[str]:
        """Validate parameters against JSON schema"""
        issues = []
        
        # Basic schema validation
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # Check required fields
        for field in required:
            if field not in parameters:
                issues.append(f"Missing required field: {field}")
        
        # Check types
        for field, value in parameters.items():
            if field in properties:
                expected_type = properties[field].get("type")
                if expected_type:
                    type_mapping = {
                        "string": str,
                        "integer": int,
                        "number": (int, float),
                        "boolean": bool,
                        "array": list,
                        "object": dict
                    }
                    
                    if expected_type in type_mapping:
                        expected_python_type = type_mapping[expected_type]
                        if isinstance(expected_python_type, tuple):
                            if not isinstance(value, expected_python_type):
                                issues.append(
                                    f"Field '{field}' has wrong type: "
                                    f"expected {expected_type}, got {type(value).__name__}"
                                )
                        else:
                            if not isinstance(value, expected_python_type):
                                issues.append(
                                    f"Field '{field}' has wrong type: "
                                    f"expected {expected_type}, got {type(value).__name__}"
                                )
        
        return issues
    
    @staticmethod
    def _perform_safety_checks(call: FunctionCall) -> List[str]:
        """Perform safety checks on function call"""
        issues = []
        
        # Check for dangerous operations in code_execution_tool
        if call.function == "code_execution_tool":
            code = call.parameters.get("code", "")
            if isinstance(code, str):
                # Check for dangerous imports
                dangerous_imports = [
                    "os.system", "subprocess", "eval", "exec", "__import__",
                    "open", "file", "input", "raw_input"
                ]
                
                for dangerous in dangerous_imports:
                    if dangerous in code:
                        issues.append(f"Potentially dangerous code detected: {dangerous}")
                
                # Check for file system access
                if any(op in code for op in ["open(", "file(", "__file__"]):
                    issues.append("File system access detected - ensure sandbox is enabled")
        
        # Check for SQL injection in database queries
        if call.function == "database_query_tool":
            query = call.parameters.get("query", "")
            if isinstance(query, str):
                # Basic check for SQL injection patterns
                if any(pattern in query.lower() for pattern in ["; drop", "; delete", "union select"]):
                    issues.append("Potentially dangerous SQL query detected")
        
        return issues
    
    @staticmethod
    def parse_function_call_from_llm(response: str) -> Optional[FunctionCall]:
        """
        Parse function call from LLM response
        
        LLM should return JSON in format:
        {
            "function": "function_name",
            "parameters": {...},
            "validation_schema": {...}  // optional
        }
        
        Args:
            response: LLM response text
            
        Returns:
            FunctionCall instance or None if parsing fails
        """
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                # Extract function call data
                function_name = data.get("function")
                if not function_name:
                    logger.warning("No function name in LLM response")
                    return None
                
                parameters = data.get("parameters", {})
                validation_schema = data.get("validation_schema")
                safety_checks = data.get("safety_checks", True)
                
                return FunctionCallProtocol.create_function_call(
                    function_name=function_name,
                    parameters=parameters,
                    validation_schema=validation_schema,
                    safety_checks=safety_checks
                )
            
            # Try to parse entire response as JSON
            data = json.loads(response)
            function_name = data.get("function")
            if function_name:
                return FunctionCallProtocol.create_function_call(
                    function_name=function_name,
                    parameters=data.get("parameters", {}),
                    validation_schema=data.get("validation_schema"),
                    safety_checks=data.get("safety_checks", True)
                )
            
            logger.warning("Could not parse function call from LLM response")
            return None
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing function call: {e}", exc_info=True)
            return None
    
    @staticmethod
    def format_function_call_for_llm(function_call: FunctionCall) -> str:
        """
        Format function call as prompt for LLM
        
        Args:
            function_call: FunctionCall to format
            
        Returns:
            Formatted string for LLM prompt
        """
        prompt = f"""Generate a function call in JSON format:

{{
    "function": "{function_call.function}",
    "parameters": {json.dumps(function_call.parameters, indent=2, ensure_ascii=False)}
}}

Function: {function_call.function}
"""
        
        if function_call.function in FunctionCallProtocol.ALLOWED_FUNCTIONS:
            function_info = FunctionCallProtocol.ALLOWED_FUNCTIONS[function_call.function]
            prompt += f"Description: {function_info.get('description', '')}\n"
            prompt += f"Required parameters: {', '.join(function_info.get('required_params', []))}\n"
            prompt += f"Optional parameters: {', '.join(function_info.get('optional_params', []))}\n"
        
        return prompt

