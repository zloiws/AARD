"""
Base Tool class for AARD platform
All tools should inherit from this class or implement the same interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID
import time
import importlib
import sys
from io import StringIO
import traceback

from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes
from app.models.tool import Tool
from app.services.tool_service import ToolService

logger = LoggingConfig.get_logger(__name__)


class BaseTool(ABC):
    """
    Base class for all tools in AARD platform
    
    Tools are executable functions that agents can use to perform actions.
    Tools can be:
    - Python functions (most common)
    - External API calls
    - System commands
    - Database operations
    """
    
    def __init__(
        self,
        tool_id: UUID,
        tool_service: ToolService
    ):
        """
        Initialize tool
        
        Args:
            tool_id: Tool ID from database
            tool_service: ToolService instance
        """
        self.tool_id = tool_id
        self.tool_service = tool_service
        self.tracer = get_tracer(__name__)
        
        # Load tool data from database
        self._tool_data: Optional[Tool] = None
        self._load_tool_data()
        
        # Compiled code cache
        self._compiled_code = None
    
    def _load_tool_data(self):
        """Load tool data from database"""
        self._tool_data = self.tool_service.get_tool(self.tool_id)
        if not self._tool_data:
            raise ValueError(f"Tool {self.tool_id} not found")
        
        if self._tool_data.status != "active":
            raise ValueError(f"Tool {self._tool_data.name} is not active (status: {self._tool_data.status})")
    
    @property
    def name(self) -> str:
        """Get tool name"""
        return self._tool_data.name if self._tool_data else "Unknown"
    
    @property
    def category(self) -> Optional[str]:
        """Get tool category"""
        return self._tool_data.category if self._tool_data else None
    
    @property
    def entry_point(self) -> str:
        """Get entry point function name"""
        return self._tool_data.entry_point if self._tool_data and self._tool_data.entry_point else "execute"
    
    @property
    def timeout_seconds(self) -> Optional[int]:
        """Get execution timeout"""
        return self._tool_data.timeout_seconds if self._tool_data else None
    
    @abstractmethod
    async def execute(
        self,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the tool
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Dictionary with execution results:
            {
                "status": "success" | "failed",
                "result": Any,
                "message": str,
                "metadata": Dict
            }
        """
        pass
    
    async def execute_python_code(
        self,
        code: str,
        function_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute Python code dynamically
        
        Args:
            code: Python code to execute
            function_name: Name of function to call
            **kwargs: Parameters to pass to function
            
        Returns:
            Execution result
        """
        start_time = time.time()
        
        try:
            # Compile code
            if self._compiled_code is None:
                self._compiled_code = compile(code, f"<tool_{self.tool_id}>", "exec")
            
            # Create execution namespace
            namespace = {
                "__name__": f"tool_{self.tool_id}",
                "__builtins__": __builtins__,
            }
            
            # Add common imports
            namespace.update({
                "json": __import__("json"),
                "datetime": __import__("datetime"),
                "os": __import__("os"),
                "pathlib": __import__("pathlib"),
            })
            
            # Execute code
            exec(self._compiled_code, namespace)
            
            # Get function
            if function_name not in namespace:
                raise ValueError(f"Function '{function_name}' not found in tool code")
            
            func = namespace[function_name]
            
            # Call function
            result = func(**kwargs)
            
            # Handle async functions
            if hasattr(result, "__await__"):
                result = await result
            
            execution_time = int((time.time() - start_time) * 1000)  # milliseconds
            
            # Record successful execution
            self.tool_service.record_execution(
                tool_id=self.tool_id,
                success=True,
                execution_time=execution_time
            )
            
            return {
                "status": "success",
                "result": result,
                "message": "Tool executed successfully",
                "metadata": {
                    "execution_time_ms": execution_time,
                    "tool_id": str(self.tool_id),
                    "tool_name": self.name,
                }
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            
            # Record failed execution
            self.tool_service.record_execution(
                tool_id=self.tool_id,
                success=False,
                execution_time=execution_time
            )
            
            logger.error(
                f"Tool execution failed: {self.name}",
                exc_info=True,
                extra={
                    "tool_id": str(self.tool_id),
                    "function_name": function_name,
                    "error": str(e),
                }
            )
            
            return {
                "status": "failed",
                "result": None,
                "message": f"Tool execution failed: {str(e)}",
                "metadata": {
                    "execution_time_ms": execution_time,
                    "tool_id": str(self.tool_id),
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            }
    
    def validate_input(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters against schema
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._tool_data or not self._tool_data.input_schema:
            return True, None
        
        # Basic validation (can be extended with jsonschema library)
        schema = self._tool_data.input_schema
        
        # Check required fields
        if "required" in schema:
            for field in schema["required"]:
                if field not in kwargs:
                    return False, f"Missing required parameter: {field}"
        
        # Check parameter types
        if "properties" in schema:
            for field, value in kwargs.items():
                if field in schema["properties"]:
                    prop_schema = schema["properties"][field]
                    if "type" in prop_schema:
                        expected_type = prop_schema["type"]
                        actual_type = type(value).__name__
                        
                        # Simple type checking
                        type_mapping = {
                            "string": "str",
                            "integer": "int",
                            "number": ("int", "float"),
                            "boolean": "bool",
                            "array": "list",
                            "object": "dict",
                        }
                        
                        if expected_type in type_mapping:
                            expected = type_mapping[expected_type]
                            if isinstance(expected, tuple):
                                if actual_type not in expected:
                                    return False, f"Parameter '{field}' must be {expected_type}, got {actual_type}"
                            elif actual_type != expected:
                                return False, f"Parameter '{field}' must be {expected_type}, got {actual_type}"
        
        return True, None

