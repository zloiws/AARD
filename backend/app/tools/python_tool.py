"""
Python Tool implementation
Executes Python code dynamically
"""
from typing import Dict, Any, Optional
from uuid import UUID

from app.tools.base_tool import BaseTool
from app.services.tool_service import ToolService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class PythonTool(BaseTool):
    """
    Python tool implementation
    
    Executes Python code from tool.code field
    """
    
    async def execute(
        self,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute Python tool
        
        Args:
            **kwargs: Parameters to pass to tool function
            
        Returns:
            Execution result
        """
        if not self._tool_data or not self._tool_data.code:
            return {
                "status": "failed",
                "result": None,
                "message": "Tool code is not defined",
                "metadata": {}
            }
        
        # Validate input
        is_valid, error_msg = self.validate_input(**kwargs)
        if not is_valid:
            return {
                "status": "failed",
                "result": None,
                "message": f"Input validation failed: {error_msg}",
                "metadata": {}
            }
        
        # Execute Python code
        return await self.execute_python_code(
            code=self._tool_data.code,
            function_name=self.entry_point,
            **kwargs
        )

