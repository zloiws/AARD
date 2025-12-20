# LEGACY_PROMPT_EXEMPT
# reason: uses hard-coded system_prompt literals for planning steps; awaiting prompt assignment migration
# phase: Phase 2 inventory freeze

"""
Planner Agent - модель "Размышлений" для планирования и анализа задач
Согласно dual-model архитектуре, этот агент отвечает за:
- Анализ задач
- Декомпозицию задач
- Создание планов
- Генерацию Function Calling промптов для CoderAgent
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

logger = LoggingConfig.get_logger(__name__)


class PlannerAgent(BaseAgent):
    """
    Planner Agent - модель "Размышлений"
    
    Отвечает за:
    - Анализ и понимание задач
    - Декомпозицию задач на шаги
    - Создание планов выполнения
    - Генерацию Function Calling промптов для CoderAgent
    """
    
    def __init__(
        self,
        agent_id: UUID,
        agent_service: AgentService,
        ollama_client: Optional[OllamaClient] = None,
        db_session = None
    ):
        """
        Initialize Planner Agent
        
        Args:
            agent_id: Agent ID from database
            agent_service: AgentService instance
            ollama_client: OllamaClient instance (optional)
            db_session: Database session (optional)
        """
        super().__init__(agent_id, agent_service, ollama_client, db_session)
        self.model_selector = ModelSelector(self.db_session)
        
        # Получить planning модель
        planning_model = self.model_selector.get_planning_model()
        if planning_model:
            self._default_model = planning_model.model_name
            server = self.model_selector.get_server_for_model(planning_model)
            if server:
                self._default_server_url = server.get_api_url()
    
    async def analyze_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Анализировать задачу и определить требования
        
        Args:
            task_description: Описание задачи
            context: Дополнительный контекст
            
        Returns:
            Результат анализа:
            {
                "goal": str,
                "requirements": List[str],
                "constraints": List[str],
                "success_criteria": List[str],
                "complexity": str,
                "estimated_steps": int
            }
        """
        analysis_prompt = f"""Проанализируй следующую задачу и определи:
1. Цель задачи
2. Требования
3. Ограничения
4. Критерии успеха
5. Сложность (simple/medium/complex)
6. Ориентировочное количество шагов

Задача: {task_description}

{self._format_context(context)}

Верни ответ в формате JSON:
{{
    "goal": "основная цель задачи",
    "requirements": ["требование 1", "требование 2"],
    "constraints": ["ограничение 1", "ограничение 2"],
    "success_criteria": ["критерий 1", "критерий 2"],
    "complexity": "simple|medium|complex",
    "estimated_steps": число
}}"""

        try:
            response = await self._call_llm(
                prompt=analysis_prompt,
                system_prompt="Ты эксперт по анализу и планированию задач. Анализируй задачи структурированно и точно.",
                temperature=0.3
            )
            
            # Парсинг JSON ответа
            analysis = self._parse_json_response(response)
            
            logger.info(
                f"Task analyzed: {analysis.get('goal', 'N/A')}",
                extra={
                    "agent_id": str(self.agent_id),
                    "complexity": analysis.get("complexity"),
                    "estimated_steps": analysis.get("estimated_steps")
                }
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing task: {e}", exc_info=True)
            # Fallback анализ
            return {
                "goal": task_description,
                "requirements": [],
                "constraints": [],
                "success_criteria": ["Задача выполнена"],
                "complexity": "medium",
                "estimated_steps": 3
            }
    
    async def decompose_task(
        self,
        task_description: str,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Декомпозировать задачу на шаги
        
        Args:
            task_description: Описание задачи
            analysis: Результат анализа задачи
            context: Дополнительный контекст
            
        Returns:
            Список шагов:
            [
                {
                    "step_id": str,
                    "description": str,
                    "type": "action|decision|validation",
                    "dependencies": List[str],
                    "estimated_duration": int (seconds)
                }
            ]
        """
        decomposition_prompt = f"""Декомпозируй задачу на последовательные шаги.

Задача: {task_description}

Анализ задачи:
- Цель: {analysis.get('goal', 'N/A')}
- Требования: {', '.join(analysis.get('requirements', []))}
- Ограничения: {', '.join(analysis.get('constraints', []))}
- Критерии успеха: {', '.join(analysis.get('success_criteria', []))}

{self._format_context(context)}

Создай последовательность шагов. Каждый шаг должен быть:
- Конкретным и выполнимым
- Иметь четкое описание
- Указывать зависимости от других шагов (если есть)
- Иметь тип: action (выполнение действия), decision (принятие решения), validation (проверка)

Верни ответ в формате JSON:
{{
    "steps": [
        {{
            "step_id": "step_1",
            "description": "описание шага",
            "type": "action|decision|validation",
            "dependencies": ["step_id_зависимости"],
            "estimated_duration": число_секунд
        }}
    ]
}}"""

        try:
            response = await self._call_llm(
                prompt=decomposition_prompt,
                system_prompt="Ты эксперт по декомпозиции задач. Создавай логичные, последовательные шаги.",
                temperature=0.4
            )
            
            # Парсинг JSON ответа
            result = self._parse_json_response(response)
            steps = result.get("steps", [])
            
            logger.info(
                f"Task decomposed into {len(steps)} steps",
                extra={
                    "agent_id": str(self.agent_id),
                    "steps_count": len(steps)
                }
            )
            
            return steps
            
        except Exception as e:
            logger.error(f"Error decomposing task: {e}", exc_info=True)
            # Fallback декомпозиция
            return [
                {
                    "step_id": "step_1",
                    "description": task_description,
                    "type": "action",
                    "dependencies": [],
                    "estimated_duration": 60
                }
            ]
    
    async def create_code_prompt(
        self,
        step: Dict[str, Any],
        plan_context: Optional[Dict[str, Any]] = None
    ) -> FunctionCall:
        """
        Создать Function Calling промпт для CoderAgent
        
        Args:
            step: Описание шага
            plan_context: Контекст плана
            
        Returns:
            FunctionCall объект для передачи в CoderAgent
        """
        step_description = step.get("description", "")
        step_type = step.get("type", "action")
        
        # Определить функцию на основе типа шага
        if step_type == "action":
            function_name = "code_execution_tool"
        elif step_type == "decision":
            function_name = "code_execution_tool"  # Decision может требовать кода для анализа
        else:
            function_name = "code_execution_tool"
        
        # Создать промпт для генерации кода
        code_prompt = f"""Создай код для выполнения следующего шага:

Шаг: {step_description}
Тип: {step_type}

{self._format_context(plan_context)}

Код должен быть:
- Безопасным
- Эффективным
- Соответствовать описанию шага
- Обрабатывать ошибки

Верни только код без объяснений."""

        # Создать FunctionCall
        function_call = FunctionCallProtocol.create_function_call(
            function_name=function_name,
            parameters={
                "code": code_prompt,  # Промпт для генерации кода
                "language": "python",
                "timeout": step.get("estimated_duration", 60),
                "validation_schema": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"},
                        "status": {"type": "string", "enum": ["success", "failed"]}
                    }
                }
            },
            safety_checks=True
        )
        
        logger.debug(
            f"Created function call for step: {step.get('step_id')}",
            extra={
                "agent_id": str(self.agent_id),
                "step_id": step.get("step_id"),
                "function_name": function_name
            }
        )
        
        return function_call
    
    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Выполнить планирование задачи
        
        Args:
            task_description: Описание задачи
            context: Дополнительный контекст
            **kwargs: Дополнительные параметры
            
        Returns:
            Результат планирования:
            {
                "status": "success",
                "result": {
                    "analysis": {...},
                    "steps": [...],
                    "function_calls": [...]
                },
                "message": str
            }
        """
        try:
            # 1. Анализ задачи
            analysis = await self.analyze_task(task_description, context)
            
            # 2. Декомпозиция на шаги
            steps = await self.decompose_task(task_description, analysis, context)
            
            # 3. Создание Function Calls для каждого шага
            function_calls = []
            for step in steps:
                try:
                    function_call = await self.create_code_prompt(step, {
                        "task_description": task_description,
                        "analysis": analysis,
                        "context": context
                    })
                    function_calls.append(function_call.to_dict())
                except Exception as e:
                    logger.warning(f"Failed to create function call for step {step.get('step_id')}: {e}")
                    # Добавить шаг без function_call
                    function_calls.append(None)
            
            # Добавить function_call в каждый шаг
            for i, step in enumerate(steps):
                if i < len(function_calls) and function_calls[i]:
                    step["function_call"] = function_calls[i]
            
            return {
                "status": "success",
                "result": {
                    "analysis": analysis,
                    "steps": steps,
                    "function_calls": function_calls
                },
                "message": f"Task planned with {len(steps)} steps",
                "metadata": {
                    "agent_id": str(self.agent_id),
                    "complexity": analysis.get("complexity"),
                    "steps_count": len(steps)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in planner execution: {e}", exc_info=True)
            return {
                "status": "failed",
                "result": None,
                "message": f"Planning failed: {str(e)}",
                "error": str(e)
            }
    
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
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Парсить JSON из ответа LLM"""
        if isinstance(response, dict):
            return response
        
        # Удалить markdown code blocks если есть
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {response[:200]}")
            return {}

