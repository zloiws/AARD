"""
Coder Agent - модель "Кода" для генерации и выполнения кода
Согласно dual-model архитектуре, этот агент отвечает за:
- Генерацию кода на основе Function Calling промптов от PlannerAgent
- Выполнение кода в безопасном окружении
- Валидацию результатов выполнения
"""
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.agents.base_agent import BaseAgent
from app.core.function_calling import FunctionCall, FunctionCallProtocol
from app.core.logging_config import LoggingConfig
from app.core.model_selector import ModelSelector
from app.core.ollama_client import OllamaClient
from app.services.agent_service import AgentService
from app.tools.python_tool import PythonTool

logger = LoggingConfig.get_logger(__name__)


class CoderAgent(BaseAgent):
    """
    Coder Agent - модель "Кода"
    
    Отвечает за:
    - Генерацию кода на основе Function Calling промптов
    - Выполнение кода в безопасном окружении
    - Валидацию результатов выполнения
    """
    
    def __init__(
        self,
        agent_id: UUID,
        agent_service: AgentService,
        ollama_client: Optional[OllamaClient] = None,
        db_session = None
    ):
        """
        Initialize Coder Agent
        
        Args:
            agent_id: Agent ID from database
            agent_service: AgentService instance
            ollama_client: OllamaClient instance (optional)
            db_session: Database session (optional)
        """
        super().__init__(agent_id, agent_service, ollama_client, db_session)
        self.model_selector = ModelSelector(self.db_session)
        
        # Получить code модель
        code_model = self.model_selector.get_code_model()
        if code_model:
            self._default_model = code_model.model_name
            server = self.model_selector.get_server_for_model(code_model)
            if server:
                self._default_server_url = server.get_api_url()
    
    async def generate_code(
        self,
        function_call: FunctionCall,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Сгенерировать код на основе Function Call
        
        Args:
            function_call: FunctionCall объект от PlannerAgent
            context: Дополнительный контекст
            
        Returns:
            Сгенерированный код
        """
        # Извлечь промпт для генерации кода из параметров
        parameters = function_call.parameters
        code_prompt = parameters.get("code", "")
        language = parameters.get("language", "python")
        
        # Создать промпт для генерации кода
        generation_prompt = f"""Сгенерируй {language} код для выполнения следующей задачи:

{code_prompt}

{self._format_context(context)}

Требования к коду:
- Код должен быть безопасным и не выполнять опасные операции
- Код должен обрабатывать ошибки
- Код должен возвращать результат в формате: {{"status": "success|failed", "result": "..."}}
- Код должен быть хорошо структурированным и читаемым

Верни только код без объяснений и markdown разметки."""

        try:
            response = await self._call_llm(
                prompt=generation_prompt,
                system_prompt=f"Ты эксперт по программированию на {language}. Генерируй безопасный, эффективный код.",
                temperature=0.2  # Низкая температура для более детерминированного кода
            )
            
            # Очистить ответ от markdown разметки
            code = self._extract_code_from_response(response, language)
            
            logger.info(
                f"Code generated: {len(code)} characters",
                extra={
                    "agent_id": str(self.agent_id),
                    "language": language,
                    "code_length": len(code)
                }
            )
            
            return code
            
        except Exception as e:
            logger.error(f"Error generating code: {e}", exc_info=True)
            raise
    
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 60,
        input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Выполнить код в безопасном окружении
        
        Args:
            code: Код для выполнения
            language: Язык программирования
            timeout: Таймаут выполнения в секундах
            input_data: Входные данные для кода
            
        Returns:
            Результат выполнения:
            {
                "status": "success|failed",
                "result": Any,
                "output": str,
                "error": Optional[str]
            }
        """
        try:
            # Использовать PythonTool для выполнения кода
            # Найти или создать PythonTool
            tool_service = self.tool_service
            python_tools = tool_service.search_tools(name="PythonTool", category="code_execution")
            
            if python_tools:
                tool_data = python_tools[0]
            else:
                # Создать PythonTool если не найден
                tool_data = tool_service.create_tool(
                    name="PythonTool",
                    description="Python code execution tool",
                    category="code_execution",
                    code="",  # PythonTool реализован как класс
                    status="active"
                )
            
            # Создать экземпляр PythonTool
            python_tool = PythonTool(
                tool_id=tool_data.id,
                tool_service=tool_service
            )
            
            # Подготовить параметры для выполнения
            execution_params = {
                "code": code,
                "timeout": timeout
            }
            
            if input_data:
                execution_params["input_data"] = input_data
            
            # Выполнить код
            result = await python_tool.execute(**execution_params)
            
            logger.info(
                f"Code executed: {result.get('status')}",
                extra={
                    "agent_id": str(self.agent_id),
                    "status": result.get("status"),
                    "language": language
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing code: {e}", exc_info=True)
            return {
                "status": "failed",
                "result": None,
                "output": "",
                "error": str(e)
            }
    
    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        function_call: Optional[FunctionCall] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Выполнить задачу: сгенерировать и выполнить код
        
        Args:
            task_description: Описание задачи
            context: Дополнительный контекст
            function_call: FunctionCall объект от PlannerAgent (если есть)
            **kwargs: Дополнительные параметры
            
        Returns:
            Результат выполнения:
            {
                "status": "success|failed",
                "result": Any,
                "code": str,
                "message": str
            }
        """
        try:
            # Если function_call не передан, создать его из task_description
            if not function_call:
                # Создать простой function_call для генерации кода
                function_call = FunctionCallProtocol.create_function_call(
                    function_name="code_execution_tool",
                    parameters={
                        "code": task_description,
                        "language": "python",
                        "timeout": 60
                    }
                )
            
            # 1. Сгенерировать код
            code = await self.generate_code(function_call, context)
            
            # 2. Выполнить код
            execution_result = await self.execute_code(
                code=code,
                language=function_call.parameters.get("language", "python"),
                timeout=function_call.parameters.get("timeout", 60),
                input_data=function_call.parameters.get("input_data")
            )
            
            # 3. Валидация результата (если есть validation_schema)
            if function_call.validation_schema:
                validation_result = self._validate_result(
                    execution_result,
                    function_call.validation_schema
                )
                if not validation_result["is_valid"]:
                    logger.warning(
                        f"Result validation failed: {validation_result['issues']}",
                        extra={"agent_id": str(self.agent_id)}
                    )
                    execution_result["validation_issues"] = validation_result["issues"]
            
            return {
                "status": execution_result.get("status", "failed"),
                "result": execution_result.get("result"),
                "code": code,
                "output": execution_result.get("output", ""),
                "message": execution_result.get("message", "Code executed"),
                "metadata": {
                    "agent_id": str(self.agent_id),
                    "language": function_call.parameters.get("language", "python"),
                    "execution_status": execution_result.get("status")
                }
            }
            
        except Exception as e:
            logger.error(f"Error in coder execution: {e}", exc_info=True)
            return {
                "status": "failed",
                "result": None,
                "code": "",
                "message": f"Code execution failed: {str(e)}",
                "error": str(e)
            }
    
    def _extract_code_from_response(self, response: str, language: str = "python") -> str:
        """Извлечь код из ответа LLM"""
        if isinstance(response, dict):
            response = response.get("response", str(response))
        
        # Удалить markdown code blocks
        response = response.strip()
        
        # Удалить ```python или ```{language}
        if response.startswith(f"```{language}"):
            response = response[len(f"```{language}"):]
        elif response.startswith("```"):
            response = response[3:]
        
        # Удалить закрывающий ```
        if response.endswith("```"):
            response = response[:-3]
        
        return response.strip()
    
    def _format_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Форматировать контекст для промпта"""
        if not context:
            return ""
        
        context_str = "\n\nДополнительный контекст:\n"
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            context_str += f"- {key}: {value}\n"
        
        return context_str
    
    def _validate_result(
        self,
        result: Dict[str, Any],
        validation_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Валидировать результат выполнения по схеме
        
        Args:
            result: Результат выполнения
            validation_schema: JSON Schema для валидации
            
        Returns:
            {
                "is_valid": bool,
                "issues": List[str]
            }
        """
        issues = []
        
        # Простая валидация структуры
        if "type" in validation_schema:
            expected_type = validation_schema["type"]
            if expected_type == "object" and not isinstance(result.get("result"), dict):
                issues.append(f"Expected object, got {type(result.get('result'))}")
        
        # Валидация свойств если есть
        if "properties" in validation_schema:
            for prop_name, prop_schema in validation_schema["properties"].items():
                if prop_name not in result.get("result", {}):
                    if prop_schema.get("required", False):
                        issues.append(f"Missing required property: {prop_name}")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues
        }

