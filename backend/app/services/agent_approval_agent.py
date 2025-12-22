# LEGACY_PROMPT_EXEMPT
# reason: uses a hard-coded system_prompt literal for agent assessment; awaiting prompt assignment migration
# phase: Phase 2 inventory freeze

"""
Agent Approval Agent (AAA) - Validate-Then-Build механизм
Проверяет необходимость создания новых агентов перед их созданием
"""
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.model_selector import ModelSelector
from app.core.ollama_client import OllamaClient
from app.models.approval import ApprovalRequest, ApprovalRequestType
from app.services.agent_service import AgentService
from app.services.tool_service import ToolService
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class AgentApprovalAgent:
    """
    Agent Approval Agent (AAA) - валидация перед созданием агентов
    
    Отвечает за:
    - Проверку необходимости создания нового агента
    - Анализ существующих агентов и инструментов
    - Оценку ценности и рисков нового агента
    - Создание запросов на утверждение при необходимости
    """
    
    def __init__(self, db: Session):
        """
        Initialize Agent Approval Agent
        
        Args:
            db: Database session
        """
        self.db = db
        self.agent_service = AgentService(db)
        self.tool_service = ToolService(db)
        self.model_selector = ModelSelector(db)
        self.ollama_client = OllamaClient()
        
        # Get planning model for reasoning
        planning_model = self.model_selector.get_planning_model()
        if planning_model:
            self._default_model = planning_model.model_name
            server = self.model_selector.get_server_for_model(planning_model)
            if server:
                self._default_server_url = server.get_api_url()
    
    async def validate_agent_creation(
        self,
        proposed_agent: Dict[str, Any],
        task_description: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Валидировать предложение о создании нового агента
        
        Args:
            proposed_agent: Предложение агента:
                {
                    "name": str,
                    "description": str,
                    "capabilities": List[str],
                    "tools": List[str],
                    "expected_benefit": str,
                    "risks": List[str]
                }
            task_description: Описание задачи, для которой нужен агент
            context: Дополнительный контекст
            
        Returns:
            Результат валидации:
            {
                "is_needed": bool,
                "can_use_existing": bool,
                "existing_agents": List[Dict],
                "value_assessment": float,  # 0.0-1.0
                "risk_assessment": float,  # 0.0-1.0
                "recommendation": str,
                "requires_approval": bool,
                "approval_request_id": Optional[UUID]
            }
        """
        try:
            # 1. Проверить существующие агенты
            existing_agents = self._find_similar_agents(proposed_agent)
            
            # 2. Проверить существующие инструменты
            existing_tools = self._find_relevant_tools(proposed_agent)
            
            # 3. Оценить необходимость через LLM
            assessment = await self._assess_agent_necessity(
                proposed_agent=proposed_agent,
                existing_agents=existing_agents,
                existing_tools=existing_tools,
                task_description=task_description,
                context=context
            )
            
            # 4. Определить, требуется ли утверждение
            requires_approval = self._should_require_approval(assessment)
            
            approval_request_id = None
            if requires_approval:
                # Создать запрос на утверждение
                approval_request_id = await self._create_approval_request(
                    proposed_agent=proposed_agent,
                    assessment=assessment,
                    existing_agents=existing_agents,
                    existing_tools=existing_tools
                )
            
            result = {
                "is_needed": assessment.get("is_needed", False),
                "can_use_existing": assessment.get("can_use_existing", False),
                "existing_agents": existing_agents,
                "existing_tools": existing_tools,
                "value_assessment": assessment.get("value_score", 0.5),
                "risk_assessment": assessment.get("risk_score", 0.5),
                "recommendation": assessment.get("recommendation", "Review required"),
                "requires_approval": requires_approval,
                "approval_request_id": approval_request_id,
                "assessment_details": assessment
            }
            
            logger.info(
                f"Agent creation validation completed: {proposed_agent.get('name')}",
                extra={
                    "agent_name": proposed_agent.get("name"),
                    "is_needed": result["is_needed"],
                    "requires_approval": requires_approval
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error validating agent creation: {e}",
                exc_info=True,
                extra={"proposed_agent": proposed_agent.get("name")}
            )
            # В случае ошибки требуем утверждение (безопасный вариант)
            return {
                "is_needed": True,
                "can_use_existing": False,
                "existing_agents": [],
                "existing_tools": [],
                "value_assessment": 0.5,
                "risk_assessment": 0.7,  # Высокий риск при ошибке
                "recommendation": f"Validation error: {str(e)}. Manual review required.",
                "requires_approval": True,
                "approval_request_id": None,
                "error": str(e)
            }
    
    def _find_similar_agents(self, proposed_agent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Найти похожих существующих агентов"""
        proposed_capabilities = proposed_agent.get("capabilities", [])
        proposed_name = proposed_agent.get("name", "").lower()
        
        # Поиск по возможностям
        similar_agents = []
        all_agents = self.agent_service.list_agents(active_only=True)
        
        for agent in all_agents:
            agent_capabilities = agent.capabilities or []
            
            # Проверка совпадения возможностей
            common_capabilities = set(proposed_capabilities) & set(agent_capabilities)
            similarity_score = len(common_capabilities) / max(len(proposed_capabilities), 1) if proposed_capabilities else 0
            
            # Проверка похожести имени
            name_similarity = 0.0
            if proposed_name and agent.name:
                if proposed_name in agent.name.lower() or agent.name.lower() in proposed_name:
                    name_similarity = 0.5
                # Простая проверка на общие слова
                proposed_words = set(proposed_name.split())
                agent_words = set(agent.name.lower().split())
                if proposed_words & agent_words:
                    name_similarity = len(proposed_words & agent_words) / max(len(proposed_words), 1)
            
            # Если есть совпадения, добавить агента
            if similarity_score > 0.3 or name_similarity > 0.3:
                similar_agents.append({
                    "id": str(agent.id),
                    "name": agent.name,
                    "description": agent.description,
                    "capabilities": agent_capabilities,
                    "similarity_score": max(similarity_score, name_similarity)
                })
        
        # Сортировать по похожести
        similar_agents.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_agents[:5]  # Топ-5 похожих агентов
    
    def _find_relevant_tools(self, proposed_agent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Найти релевантные существующие инструменты"""
        proposed_tools = proposed_agent.get("tools", [])
        
        relevant_tools = []
        all_tools = self.tool_service.list_tools(status="active", active_only=True)
        
        for tool in all_tools:
            tool_name_lower = tool.name.lower() if tool.name else ""
            
            # Проверка совпадения имен инструментов
            for proposed_tool in proposed_tools:
                if isinstance(proposed_tool, str):
                    if proposed_tool.lower() in tool_name_lower or tool_name_lower in proposed_tool.lower():
                        relevant_tools.append({
                            "id": str(tool.id),
                            "name": tool.name,
                            "description": tool.description,
                            "category": tool.category
                        })
                        break
        
        return relevant_tools
    
    async def _assess_agent_necessity(
        self,
        proposed_agent: Dict[str, Any],
        existing_agents: List[Dict[str, Any]],
        existing_tools: List[Dict[str, Any]],
        task_description: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Оценить необходимость создания агента через LLM"""
        
        # Подготовить информацию о существующих агентах
        existing_agents_info = ""
        if existing_agents:
            existing_agents_info = "\n\nСуществующие похожие агенты:\n"
            for agent in existing_agents[:3]:  # Топ-3
                existing_agents_info += f"- {agent['name']}: {agent.get('description', 'N/A')}\n"
                existing_agents_info += f"  Возможности: {', '.join(agent.get('capabilities', []))}\n"
                existing_agents_info += f"  Похожесть: {agent['similarity_score']:.2f}\n"
        
        # Подготовить информацию о существующих инструментах
        existing_tools_info = ""
        if existing_tools:
            existing_tools_info = "\n\nСуществующие релевантные инструменты:\n"
            for tool in existing_tools[:5]:
                existing_tools_info += f"- {tool['name']}: {tool.get('description', 'N/A')}\n"
        
        assessment_prompt = f"""Проанализируй предложение о создании нового агента и определи:

1. Действительно ли нужен новый агент, или можно использовать комбинацию существующих?
2. Какова ценность создания этого агента (0.0-1.0)?
3. Каковы риски создания этого агента (0.0-1.0)?
4. Какая рекомендация по созданию?

Предлагаемый агент:
- Имя: {proposed_agent.get('name', 'N/A')}
- Описание: {proposed_agent.get('description', 'N/A')}
- Возможности: {', '.join(proposed_agent.get('capabilities', []))}
- Инструменты: {', '.join(proposed_agent.get('tools', []))}
- Ожидаемая польза: {proposed_agent.get('expected_benefit', 'N/A')}
- Риски: {', '.join(proposed_agent.get('risks', []))}
{existing_agents_info}
{existing_tools_info}
{f"Задача: {task_description}" if task_description else ""}

Верни ответ в формате JSON:
{{
    "is_needed": true/false,
    "can_use_existing": true/false,
    "value_score": 0.0-1.0,
    "risk_score": 0.0-1.0,
    "recommendation": "текст рекомендации",
    "reasoning": "обоснование решения"
}}"""

        try:
            response = await self.ollama_client.generate(
                prompt=assessment_prompt,
                system_prompt="Ты эксперт по анализу архитектуры агентных систем. Оценивай необходимость создания новых агентов критически и предлагай использовать существующие компоненты когда возможно.",
                model=self._default_model,
                server_url=self._default_server_url,
                temperature=0.3,
                format="json"
            )
            
            # Парсинг JSON ответа
            if isinstance(response, dict):
                response_text = response.get("response", "")
            else:
                response_text = str(response)
            
            # Удалить markdown code blocks если есть
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            assessment = json.loads(response_text)
            
            return assessment
            
        except Exception as e:
            logger.warning(f"Failed to assess agent necessity via LLM: {e}, using fallback")
            # Fallback оценка
            return {
                "is_needed": len(existing_agents) == 0,  # Нужен если нет похожих
                "can_use_existing": len(existing_agents) > 0,
                "value_score": 0.5,
                "risk_score": 0.5,
                "recommendation": "Manual review required due to assessment error",
                "reasoning": f"LLM assessment failed: {str(e)}"
            }
    
    def _should_require_approval(self, assessment: Dict[str, Any]) -> bool:
        """Определить, требуется ли утверждение"""
        # Всегда требовать утверждение если:
        # 1. Высокий риск (>0.7)
        # 2. Низкая ценность (<0.3)
        # 3. Можно использовать существующие агенты
        risk_score = assessment.get("risk_score", 0.5)
        value_score = assessment.get("value_score", 0.5)
        can_use_existing = assessment.get("can_use_existing", False)
        
        if risk_score > 0.7:
            return True
        if value_score < 0.3:
            return True
        if can_use_existing:
            return True
        
        return False
    
    async def _create_approval_request(
        self,
        proposed_agent: Dict[str, Any],
        assessment: Dict[str, Any],
        existing_agents: List[Dict[str, Any]],
        existing_tools: List[Dict[str, Any]]
    ) -> Optional[UUID]:
        """Создать запрос на утверждение создания агента"""
        try:
            from app.services.approval_service import ApprovalService
            approval_service = ApprovalService(self.db)
            
            approval_data = {
                "proposed_agent": proposed_agent,
                "assessment": assessment,
                "existing_agents": existing_agents,
                "existing_tools": existing_tools
            }
            
            approval_request = approval_service.create_approval_request(
                request_type=ApprovalRequestType.AGENT_CREATION,
                request_data=approval_data,
                risk_assessment={
                    "risk_level": assessment.get("risk_score", 0.5),
                    "value_level": assessment.get("value_score", 0.5),
                    "reason": assessment.get("recommendation", "Agent creation requires approval")
                },
                recommendation=assessment.get("recommendation", "Review agent creation proposal")
            )
            
            logger.info(
                f"Created approval request for agent creation: {proposed_agent.get('name')}",
                extra={
                    "approval_request_id": str(approval_request.id),
                    "agent_name": proposed_agent.get("name")
                }
            )
            
            return approval_request.id
            
        except Exception as e:
            logger.error(
                f"Failed to create approval request: {e}",
                exc_info=True,
                extra={"agent_name": proposed_agent.get("name")}
            )
            return None

