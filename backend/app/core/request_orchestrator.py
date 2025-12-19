"""
Request Orchestrator - центральный оркестратор для обработки запросов
"""
import time
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from app.components.interpretation_service import InterpretationService
from app.components.semantic_validator import SemanticValidator
from app.core.execution_context import ExecutionContext
from app.core.logging_config import LoggingConfig
from app.core.model_selector import ModelSelector
from app.core.ollama_client import OllamaClient, TaskType
from app.core.prompt_manager import PromptManager
from app.core.request_router import RequestType, determine_request_type
from app.core.service_registry import get_service_registry
from app.core.workflow_engine import WorkflowEngine, WorkflowState
from app.models.interpretation import DecisionTimeline
from app.models.task import Task, TaskStatus
from app.services.ollama_service import OllamaService
from app.services.planning_hypothesis_service import PlanningHypothesisService
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class OrchestrationResult:
    """Результат оркестрации запроса"""
    
    def __init__(
        self,
        response: str,
        model: str = "unknown",
        task_type: str = "unknown",
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.response = response
        self.model = model
        self.task_type = task_type
        self.duration_ms = duration_ms
        self.metadata = metadata or {}


class RequestOrchestrator:
    """
    Центральный оркестратор для обработки запросов пользователей
    
    Управляет всем workflow от запроса до результата:
    - Определяет тип запроса
    - Выбирает подходящую стратегию обработки
    - Интегрирует все необходимые сервисы
    - Обрабатывает ошибки и fallback
    """
    
    def __init__(self):
        """Инициализация оркестратора"""
        self.registry = get_service_registry()
        # WorkflowEngine будет создан для каждого запроса с его ExecutionContext
    
    async def process_request(
        self,
        message: str,
        context: ExecutionContext,
        task_type: Optional[str] = None,
        model: Optional[str] = None,
        server_id: Optional[str] = None,
        temperature: float = 0.7
    ) -> OrchestrationResult:
        """
        Обработать запрос пользователя
        
        Args:
            message: Сообщение пользователя
            context: ExecutionContext
            task_type: Опциональный тип задачи
            model: Опциональная модель
            server_id: Опциональный ID сервера
            temperature: Temperature для генерации
            
        Returns:
            OrchestrationResult с результатом обработки
        """
        start_time = time.time()
        
        # Создать WorkflowEngine для управления состояниями
        workflow_engine = WorkflowEngine.from_context(context)
        workflow_engine.initialize(
            user_request=message,
            username=context.user_id or "user",
            interaction_type=task_type or "chat"
        )
        # Сохранить workflow_engine в контексте для доступа из других мест
        context.set_workflow_engine(workflow_engine)
        
        # Создать PromptManager и добавить в контекст
        prompt_manager = PromptManager(context)
        context.set_prompt_manager(prompt_manager)
        
        # Interpretation step: run explicit interpretation layer before routing/planning
        try:
            interpretation_service = InterpretationService(context.db)
            structured_intent = await interpretation_service.interpret(message, context)
            semantic_validator = SemanticValidator()
            validation = await semantic_validator.validate_intent(structured_intent)
            # Ensure metadata exists
            if not getattr(context, "metadata", None):
                context.metadata = context.metadata or {}
            # Persist both typed contract and legacy payload (for compatibility with existing services)
            context.metadata["structured_intent"] = structured_intent.model_dump()
            context.metadata["interpretation"] = structured_intent.metadata.get("legacy") or structured_intent.model_dump()

            # If interpretation requires clarification, ask user immediately
            if validation.status == "clarification_required":
                questions = validation.clarification_questions or structured_intent.clarification_questions or []
                clarification_text = "Требуется уточнение:\n" + ("\n".join(f"- {q}" for q in questions) if questions else "Пожалуйста, уточните запрос.")
                return OrchestrationResult(
                    response=clarification_text,
                    model="none",
                    task_type="clarification",
                    metadata={"clarification_required": True, "questions": questions, "validation": validation.model_dump()}
                )

            # Planning step: generate plan hypotheses for complex requests
            try:
                # Find the timeline created by interpretation service
                session_id = str(context.workflow_id) if hasattr(context, "workflow_id") and context.workflow_id else str(uuid4())
                timeline = context.db.query(DecisionTimeline).filter(DecisionTimeline.session_id == session_id).first()

                if timeline:
                    planning_service = PlanningHypothesisService(context.db)
                    hypotheses = await planning_service.generate_plan_hypotheses(
                        timeline.id,
                        context.metadata.get("interpretation") or {}
                    )

                    # Store hypotheses in context for later use
                    context.metadata["plan_hypotheses"] = [
                        {
                            "id": str(h.id),
                            "name": h.name,
                            "confidence": h.confidence,
                            "lifecycle": h.lifecycle.value
                        }
                        for h in hypotheses
                    ]

                    logger.info(f"Generated {len(hypotheses)} plan hypotheses for timeline {timeline.id}")

            except Exception as e:
                # Non-fatal: log and continue (fallback to existing flow)
                logger.warning(f"Planning hypothesis generation failed: {e}", exc_info=True)

        except Exception as e:
            # Non-fatal: log and continue (fallback to existing flow)
            logger.warning(f"Interpretation step failed: {e}", exc_info=True)
        
        # Определить тип запроса
        request_type, request_metadata = determine_request_type(message, task_type)
        
        # Переход в состояние PARSING
        workflow_engine.transition_to(
            WorkflowState.PARSING,
            f"Определен тип запроса: {request_type.value}",
            metadata={"request_type": request_type.value, "metadata": request_metadata}
        )
        
        logger.info(
            f"Processing request: {request_type.value}",
            extra={
                "request_type": request_type.value,
                "workflow_id": context.workflow_id,
                "message_preview": message[:100]
            }
        )
        
        # Событие уже сохранено через WorkflowEngine.transition_to()
        
        try:
            # Обработать в зависимости от типа запроса
            if request_type == RequestType.SIMPLE_QUESTION:
                result = await self._handle_simple_question(
                    message, context, task_type, model, server_id, temperature
                )
            elif request_type == RequestType.INFORMATION_QUERY:
                result = await self._handle_information_query(
                    message, context, request_metadata
                )
            elif request_type == RequestType.CODE_GENERATION:
                result = await self._handle_code_generation(
                    message, context, request_metadata, model, server_id
                )
            elif request_type == RequestType.COMPLEX_TASK:
                result = await self._handle_complex_task(
                    message, context, request_metadata
                )
            elif request_type == RequestType.PLANNING_ONLY:
                result = await self._handle_planning_only(
                    message, context, request_metadata, model, server_id
                )
            else:
                # Fallback к простому вопросу
                result = await self._handle_simple_question(
                    message, context, task_type, model, server_id, temperature
                )
            
            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms
            
            # Анализировать и улучшить промпты после обработки
            try:
                improvement_results = await prompt_manager.analyze_and_improve_prompts()
                if improvement_results.get("improved", 0) > 0:
                    logger.info(
                        f"Created {improvement_results['improved']} improved prompt versions",
                        extra={"workflow_id": context.workflow_id, "results": improvement_results}
                    )
            except Exception as e:
                logger.warning(f"Failed to analyze and improve prompts: {e}", exc_info=True)
            
            # Отметить workflow как завершенный
            try:
                workflow_engine = context.workflow_engine or WorkflowEngine.from_context(context)
                if workflow_engine and workflow_engine.get_current_state() not in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
                    workflow_engine.mark_completed(result=result.response[:200] if result.response else None)
            except Exception:
                pass  # Игнорируем ошибки при сохранении состояния
            
            # Событие завершения уже сохранено через WorkflowEngine.mark_completed()
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error processing request: {e}",
                exc_info=True,
                extra={"workflow_id": context.workflow_id}
            )
            
            # Отметить workflow как проваленный
            try:
                workflow_engine = getattr(context, 'workflow_engine', None)
                if workflow_engine:
                    workflow_engine.mark_failed(
                        error=str(e),
                        error_details={"request_type": request_type.value if 'request_type' in locals() else "unknown", "stage": "processing"}
                    )
            except Exception:
                pass  # Игнорируем ошибки при сохранении состояния
            
            # Попытка автоматического replanning для CODE_GENERATION и COMPLEX_TASK
            workflow_engine = getattr(context, 'workflow_engine', None)
            if request_type in [RequestType.CODE_GENERATION, RequestType.COMPLEX_TASK] and workflow_engine:
                try:
                    logger.info("Attempting automatic replanning after error")
                    # Переход в состояние RETRYING
                    workflow_engine.transition_to(
                        WorkflowState.RETRYING,
                        "Автоматический replanning после ошибки",
                        metadata={"original_error": str(e)}
                    )
                    
                    # Упрощенный replanning - попробовать более простой подход
                    result = await self._handle_simple_question(
                        message, context, task_type, model, server_id, temperature
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    result.duration_ms = duration_ms
                    
                    # Если replanning успешен, отметить как completed
                    workflow_engine.mark_completed(result=result.response[:200])
                    
                    return result
                except Exception as replanning_error:
                    logger.warning(f"Replanning failed: {replanning_error}")
            
            # Fallback к простому вопросу при ошибке
            try:
                if workflow_engine:
                    workflow_engine.transition_to(
                        WorkflowState.RETRYING,
                        "Fallback к простому вопросу",
                        metadata={"original_error": str(e)}
                    )
                
                result = await self._handle_simple_question(
                    message, context, task_type, model, server_id, temperature
                )
                duration_ms = int((time.time() - start_time) * 1000)
                result.duration_ms = duration_ms
                
                # Если fallback успешен, отметить как completed
                if workflow_engine:
                    workflow_engine.mark_completed(result=result.response[:200])
                
                return result
            except Exception as fallback_error:
                logger.error(
                    f"Fallback also failed: {fallback_error}",
                    exc_info=True
                )
                
                # Финальная ошибка
                if workflow_engine:
                    workflow_engine.mark_failed(
                        error=f"All fallback strategies failed: {str(fallback_error)}",
                        error_details={"original_error": str(e), "fallback_error": str(fallback_error)}
                    )
                
                # Возвращаем ошибку
                return OrchestrationResult(
                    response=f"Произошла ошибка при обработке запроса: {str(e)}",
                    model="error",
                    task_type=request_type.value,
                    duration_ms=int((time.time() - start_time) * 1000),
                    metadata={"error": str(e), "fallback_error": str(fallback_error)}
                )
    
    async def _handle_simple_question(
        self,
        message: str,
        context: ExecutionContext,
        task_type: Optional[str] = None,
        model: Optional[str] = None,
        server_id: Optional[str] = None,
        temperature: float = 0.7
    ) -> OrchestrationResult:
        """Обработать простой вопрос - прямой ответ от LLM"""
        logger.debug("Handling simple question with direct LLM")
        
        prompt_start_time = time.time()
        prompt_id = None
        
        # Получить system prompt через PromptManager
        system_prompt = await self._get_system_prompt(context)
        
        # Записать использование промпта, если есть PromptManager
        if context.prompt_manager and system_prompt:
            try:
                prompt = await context.prompt_manager.get_prompt_for_stage("planning")
                if prompt:
                    prompt_id = prompt.id
            except Exception as e:
                logger.debug(f"Could not get prompt for recording: {e}")
        
        # Выбрать модель и сервер
        selected_model, selected_server = self._select_model_and_server(
            context.db, task_type, model, server_id
        )
        
        if not selected_model or not selected_server:
            raise ValueError("No available model or server found")
        
        # Сгенерировать ответ
        execution_start = time.time()
        try:
            ollama_client = OllamaClient()
            response = await ollama_client.generate(
                prompt=message,
                task_type=TaskType.DEFAULT if not task_type else TaskType(task_type),
                model=selected_model,
                server_url=selected_server.get_api_url(),
                system_prompt=system_prompt,
                temperature=temperature
            )
            
            execution_time_ms = (time.time() - execution_start) * 1000
            
            # Записать успешное использование промпта
            if context.prompt_manager and prompt_id:
                await context.prompt_manager.record_prompt_usage(
                    prompt_id=prompt_id,
                    success=True,
                    execution_time_ms=execution_time_ms,
                    stage="simple_question"
                )
            
            return OrchestrationResult(
                response=response.response,
                model=selected_model,
                task_type=task_type or "general_chat",
                metadata={"server_id": str(selected_server.id)}
            )
        except Exception as e:
            execution_time_ms = (time.time() - execution_start) * 1000
            
            # Записать неудачное использование промпта
            if context.prompt_manager and prompt_id:
                await context.prompt_manager.record_prompt_usage(
                    prompt_id=prompt_id,
                    success=False,
                    execution_time_ms=execution_time_ms,
                    stage="simple_question"
                )
            
            raise
    
    async def _handle_information_query(
        self,
        message: str,
        context: ExecutionContext,
        metadata: Dict[str, Any]
    ) -> OrchestrationResult:
        """Обработать информационный запрос - нужен поиск"""
        logger.debug("Handling information query")
        
        # Интеграция MemoryService для поиска в памяти
        from app.services.memory_service import MemoryService
        
        memory_service = MemoryService(context)
        
        # Получить WorkflowEngine из контекста
        workflow_engine = getattr(context, 'workflow_engine', None)
        if workflow_engine:
            workflow_engine.transition_to(
                WorkflowState.PARSING,
                "Поиск информации в памяти",
                metadata={"query": message[:100]}
            )
        
        # Поиск в памяти агента (если есть agent_id в контексте)
        relevant_memories = []
        agent_id = metadata.get("agent_id") or context.metadata.get("agent_id")
        
        if agent_id:
            try:
                # Векторный поиск в памяти
                relevant_memories = await memory_service.search_memories_vector(
                    agent_id=agent_id,
                    query_text=message,
                    limit=5,
                    similarity_threshold=0.6,
                    combine_with_text_search=True
                )
                logger.debug(f"Found {len(relevant_memories)} relevant memories")
            except Exception as e:
                logger.warning(f"Memory search failed: {e}", exc_info=True)
        
        # Если найдены релевантные воспоминания, используем их для контекста
        if relevant_memories:
            memory_context = "\n\nРелевантная информация из памяти:\n"
            for i, memory in enumerate(relevant_memories[:3], 1):  # Берем топ-3
                memory_context += f"{i}. {memory.summary or str(memory.content)}\n"
            
            # Добавляем контекст к запросу
            enhanced_message = f"{message}\n\n{memory_context}"
            
            # Используем улучшенный запрос для LLM
            result = await self._handle_simple_question(enhanced_message, context)
            result.metadata = result.metadata or {}
            result.metadata["memories_used"] = len(relevant_memories)
            result.metadata["memory_search"] = True
            return result
        
        # Если воспоминаний нет, используем WebSearchTool для поиска в интернете
        # Проверяем необходимость одобрения через AdaptiveApprovalService
        from uuid import UUID

        from app.models.approval import ApprovalRequestType
        from app.services.adaptive_approval_service import \
            AdaptiveApprovalService
        from app.services.approval_service import ApprovalService
        from app.services.tool_service import ToolService
        from app.tools.web_search_tool import WebSearchTool

        # Создаем фиктивный план для проверки одобрения (для информационных запросов)
        # Используем минимальный риск для веб-поиска
        adaptive_approval = AdaptiveApprovalService(context.db)
        
        # Для веб-поиска считаем риск средним (может требовать одобрения)
        web_search_risk = 0.5  # Средний риск для веб-поиска
        
        # Проверяем, требуется ли одобрение
        # Для веб-поиска используем упрощенную проверку
        requires_approval = web_search_risk >= 0.4  # MEDIUM_RISK_THRESHOLD
        
        if requires_approval:
            # Создаем запрос на одобрение
            approval_service = ApprovalService(context.db)
            approval = approval_service.create_approval_request(
                request_type=ApprovalRequestType.EXECUTION_STEP,
                request_data={
                    "query": message,
                    "search_type": "information_query",
                    "action": "web_search"
                },
                task_id=metadata.get("task_id"),
                risk_assessment={
                    "risk_level": web_search_risk,
                    "reason": "web_search_medium_risk"
                },
                recommendation=f"Требуется одобрение для веб-поиска: {message[:100]}"
            )
            
            # Возвращаем результат с ожиданием одобрения
            result = OrchestrationResult(
                response=f"Требуется одобрение для веб-поиска: {message[:100]}...",
                model="unknown",
                task_type="information_query",
                metadata={
                    "approval_required": True,
                    "approval_id": str(approval.id),
                    "search_type": "web",
                    "query": message,
                    "requires_approval": True
                }
            )
            return result
        
        # Если одобрение не требуется или уже получено, выполняем поиск
        try:
            # Получаем или создаем WebSearchTool
            tool_service = ToolService(context.db)
            
            # Ищем существующий WebSearchTool
            web_search_tools = tool_service.search_tools(
                name="WebSearchTool",
                category="web_search"
            )
            
            if web_search_tools:
                tool_data = web_search_tools[0]
            else:
                # Создаем новый инструмент если не найден
                tool_data = tool_service.create_tool(
                    name="WebSearchTool",
                    description="Поиск информации в интернете",
                    category="web_search",
                    code="",  # WebSearchTool реализован как класс
                    status="active"
                )
            
            # Создаем экземпляр WebSearchTool
            web_search_tool = WebSearchTool(
                tool_id=tool_data.id,
                tool_service=tool_service
            )
            
            # Выполняем поиск
            search_result = await web_search_tool.execute(
                query=message,
                max_results=5
            )
            
            if search_result.get("status") == "success":
                # Сохраняем результаты поиска в память
                try:
                    if agent_id:
                        from uuid import UUID
                        agent_uuid = UUID(agent_id) if isinstance(agent_id, str) else agent_id
                        search_results = search_result.get("result", {}).get("results", [])
                        for result_item in search_results[:3]:  # Сохраняем топ-3
                            await memory_service.save_memory_async(
                                agent_id=agent_uuid,
                                memory_type="episodic",
                                content={
                                    "snippet": result_item.get("snippet", ""),
                                    "title": result_item.get("title", ""),
                                    "url": result_item.get("url", "")
                                },
                                summary=f"Результат поиска: {result_item.get('title', '')}",
                                tags=["web_search"],
                                source="web_search",
                                generate_embedding=True
                            )
                except Exception as e:
                    logger.warning(f"Failed to save search results to memory: {e}", exc_info=True)
                
                # Формируем ответ с результатами поиска
                search_results = search_result.get("result", {}).get("results", [])
                results_text = "\n\nРезультаты поиска в интернете:\n\n"
                for i, result_item in enumerate(search_results, 1):
                    results_text += f"{i}. {result_item.get('title', 'N/A')}\n"
                    results_text += f"   {result_item.get('snippet', '')}\n"
                    if result_item.get('url'):
                        results_text += f"   URL: {result_item.get('url')}\n"
                    results_text += "\n"
                
                # Используем результаты для ответа LLM
                enhanced_message = f"{message}\n\n{results_text}"
                result = await self._handle_simple_question(enhanced_message, context)
                result.metadata = result.metadata or {}
                result.metadata["web_search"] = True
                result.metadata["search_results_count"] = len(search_results)
                result.metadata["search_query"] = message
                return result
            else:
                # Если поиск не удался, используем обычный ответ
                logger.warning(f"Web search failed: {search_result.get('message')}")
                return await self._handle_simple_question(message, context)
                
        except Exception as e:
            logger.error(
                f"Error executing web search: {e}",
                exc_info=True,
                extra={
                    "query": message,
                    "agent_id": str(agent_id) if agent_id else None
                }
            )
            # Fallback to simple question if web search fails
            return await self._handle_simple_question(message, context)
    
    async def _handle_code_generation(
        self,
        message: str,
        context: ExecutionContext,
        metadata: Dict[str, Any],
        model: Optional[str] = None,
        server_id: Optional[str] = None
    ) -> OrchestrationResult:
        """Обработать запрос на генерацию кода"""
        logger.debug("Handling code generation request")
        
        # Получить WorkflowEngine из контекста (если был создан)
        workflow_engine = getattr(context, 'workflow_engine', None)
        
        planning_start = time.time()
        planning_prompt_id = None
        
        # Получить модель и server_id для использования в планировании и выполнении
        selected_model, selected_server = self._select_model_and_server(
            context.db, "code_generation", model, server_id
        )
        
        # Сохранить модель и server_id в metadata и context для передачи в ExecutionService
        if not metadata:
            metadata = {}
        metadata["model"] = selected_model
        metadata["server_id"] = str(selected_server.id)
        metadata["server_url"] = selected_server.get_api_url()
        
        # Сохранить в context.metadata для доступа в ExecutionService
        if not context.metadata:
            context.metadata = {}
        context.metadata["model"] = selected_model
        context.metadata["server_id"] = str(selected_server.id)
        context.metadata["server_url"] = selected_server.get_api_url()
        
        # Получить промпт для планирования
        if context.prompt_manager:
            try:
                planning_prompt = await context.prompt_manager.get_prompt_for_stage("planning")
                if planning_prompt:
                    planning_prompt_id = planning_prompt.id
            except Exception as e:
                logger.debug(f"Could not get planning prompt: {e}")
        
        # Создать задачу
        task = Task(
            description=message,
            status=TaskStatus.PENDING
        )
        context.db.add(task)
        context.db.commit()
        context.db.refresh(task)
        
        # Получить PlanningService через ExecutionContext
        from app.services.planning_service import PlanningService
        planning_service = PlanningService(context)
        
        # Переход в состояние PLANNING
        if workflow_engine:
            workflow_engine.transition_to(
                WorkflowState.PLANNING,
                "Начало генерации плана",
                metadata={"task_id": str(task.id)}
            )
        
        # Генерировать план
        plan = None
        planning_success = False
        try:
            plan = await planning_service.generate_plan(
                task_id=task.id,
                task_description=message,
                context=metadata
            )
            planning_success = plan is not None and plan.status == "approved"
            
            # Использовать AdaptiveApprovalService для определения необходимости одобрения
            from app.services.adaptive_approval_service import \
                AdaptiveApprovalService
            adaptive_approval = AdaptiveApprovalService(context)
            
            # Get task autonomy level
            task_autonomy_level = None
            if plan and plan.task_id:
                from app.models.task import Task
                task = context.db.query(Task).filter(Task.id == plan.task_id).first()
                if task:
                    task_autonomy_level = task.autonomy_level
            
            requires_approval, approval_metadata = adaptive_approval.should_require_approval(
                plan=plan,
                agent_id=None,  # Можно передать agent_id если известен
                task_risk_level=None,
                task_autonomy_level=task_autonomy_level
            )
            
            # Обновить состояние workflow в зависимости от статуса плана и решения об одобрении
            if workflow_engine:
                if requires_approval and plan.status == "draft":
                    workflow_engine.transition_to(
                        WorkflowState.APPROVAL_PENDING,
                        f"План создан, требуется одобрение ({approval_metadata.get('reason', 'unknown')})",
                        metadata={
                            "plan_id": str(plan.id),
                            "approval_metadata": approval_metadata
                        }
                    )
                elif plan.status == "approved":
                    workflow_engine.transition_to(
                        WorkflowState.APPROVED,
                        "План одобрен, готов к выполнению",
                        metadata={"plan_id": str(plan.id), "steps_count": len(plan.steps) if plan.steps else 0}
                    )
                elif not requires_approval and plan.status == "draft":
                    # Автоматически одобряем если не требуется одобрение
                    workflow_engine.transition_to(
                        WorkflowState.APPROVED,
                        "План автоматически одобрен (низкий риск, высокое доверие)",
                        metadata={
                            "plan_id": str(plan.id),
                            "auto_approved": True,
                            "approval_metadata": approval_metadata
                        }
                    )
                    # Обновить статус плана в БД
                    plan.status = "approved"
                    try:
                        # Keep lifecycle metadata consistent
                        from datetime import datetime as _dt
                        plan.approved_at = _dt.utcnow()
                    except Exception:
                        pass
                    context.db.commit()
        except Exception as e:
            logger.error(f"Plan generation failed: {e}", exc_info=True)
            workflow_engine = getattr(context, 'workflow_engine', None)
            if workflow_engine:
                workflow_engine.mark_failed(
                    error=f"Plan generation failed: {str(e)}",
                    error_details={"task_id": str(task.id), "stage": "planning"}
                )
        
        # Записать метрики промпта планирования
        if context.prompt_manager and planning_prompt_id:
            planning_time_ms = (time.time() - planning_start) * 1000
            await context.prompt_manager.record_prompt_usage(
                prompt_id=planning_prompt_id,
                success=planning_success,
                execution_time_ms=planning_time_ms,
                stage="planning"
            )
        
        if plan and plan.status == "approved":
            # Переход в состояние EXECUTING
            if workflow_engine:
                workflow_engine.transition_to(
                    WorkflowState.EXECUTING,
                    "Начало выполнения плана",
                    metadata={"plan_id": str(plan.id)}
                )
            
            execution_start = time.time()
            execution_prompt_id = None
            
            # Получить промпт для выполнения
            if context.prompt_manager:
                try:
                    execution_prompt = await context.prompt_manager.get_prompt_for_stage("execution")
                    if execution_prompt:
                        execution_prompt_id = execution_prompt.id
                except Exception as e:
                    logger.debug(f"Could not get execution prompt: {e}")
            
            # Получить ExecutionService через ExecutionContext
            from app.services.execution_service import ExecutionService
            execution_service = ExecutionService(context)
            
            # Выполнить план
            execution_success = False
            try:
                executed_plan = await execution_service.execute_plan(plan.id)
                execution_success = executed_plan.status == "completed"
                
                # Обновить состояние workflow
                if workflow_engine:
                    if execution_success:
                        workflow_engine.mark_completed(result=result_text[:200] if 'result_text' in locals() else None)
                    else:
                        workflow_engine.mark_failed(
                            error=f"Plan execution failed: {executed_plan.status}",
                            error_details={"plan_id": str(plan.id), "final_status": executed_plan.status}
                        )
                
                # Извлечь результаты
                result_text = self._extract_plan_results(executed_plan)
                
                # Сохранить информацию о выполнении в память через MemoryService
                try:
                    from app.services.memory_service import MemoryService
                    memory_service = MemoryService(context)
                    
                    # Получаем agent_id из контекста или метаданных
                    agent_id = metadata.get("agent_id") or context.metadata.get("agent_id")
                    
                    if agent_id:
                        # Сохраняем память о выполненной задаче
                        memory_service.save_memory(
                            agent_id=agent_id,
                            memory_type="execution",
                            content={
                                "task": message,
                                "plan_id": str(plan.id),
                                "status": executed_plan.status,
                                "result": result_text[:500] if result_text else None
                            },
                            summary=f"Выполнена задача: {message[:100]}",
                            importance=0.7 if execution_success else 0.5,
                            tags=["execution", "code_generation", "success" if execution_success else "failure"]
                        )
                        logger.debug(f"Saved execution memory for agent {agent_id}")
                except Exception as e:
                    logger.warning(f"Failed to save execution memory: {e}", exc_info=True)
                
                # Записать метрики промпта выполнения
                if context.prompt_manager and execution_prompt_id:
                    execution_time_ms = (time.time() - execution_start) * 1000
                    await context.prompt_manager.record_prompt_usage(
                        prompt_id=execution_prompt_id,
                        success=execution_success,
                        execution_time_ms=execution_time_ms,
                        stage="execution"
                    )
                
                # Получить реальную модель из контекста или использовать переданную
                actual_model = metadata.get("model") or context.metadata.get("model") or "planning+execution"
                
                return OrchestrationResult(
                    response=result_text,
                    model=selected_model,  # Используем реальную модель вместо "planning+execution"
                    task_type="code_generation",
                    metadata={
                        "plan_id": str(plan.id), 
                        "task_id": str(task.id),
                        "used_model": selected_model,
                        "execution_method": "planning+execution"
                    }
                )
            except Exception as e:
                logger.error(f"Plan execution failed: {e}", exc_info=True)
                if workflow_engine:
                    workflow_engine.mark_failed(
                        error=f"Plan execution exception: {str(e)}",
                        error_details={"plan_id": str(plan.id), "exception_type": type(e).__name__}
                    )
                
                # Записать метрики неудачного выполнения
                if context.prompt_manager and execution_prompt_id:
                    execution_time_ms = (time.time() - execution_start) * 1000
                    await context.prompt_manager.record_prompt_usage(
                        prompt_id=execution_prompt_id,
                        success=False,
                        execution_time_ms=execution_time_ms,
                        stage="execution"
                    )
                
                raise
        else:
            # Fallback к простому LLM
            logger.warning(f"Plan generation failed, falling back to direct LLM")
            return await self._handle_simple_question(message, context, task_type="code_generation")
    
    async def _handle_complex_task(
        self,
        message: str,
        context: ExecutionContext,
        metadata: Dict[str, Any]
    ) -> OrchestrationResult:
        """Обработать сложную задачу - планирование + выполнение + рефлексия"""
        logger.debug("Handling complex task")
        
        # Получить WorkflowEngine из контекста
        workflow_engine = getattr(context, 'workflow_engine', None)
        if workflow_engine:
            workflow_engine.transition_to(
                WorkflowState.PLANNING,
                "Обработка сложной задачи с рефлексией",
                metadata={"task": message[:100]}
            )
        
        # Сначала выполняем как code_generation
        result = await self._handle_code_generation(message, context, metadata, None, None)
        
        # После выполнения добавляем рефлексию через ReflectionService
        from app.services.reflection_service import ReflectionService
        
        reflection_service = ReflectionService(context)
        
        # Анализируем результат выполнения
        try:
            # Если выполнение было неудачным, анализируем ошибку
            if result.metadata and result.metadata.get("execution_success") is False:
                error_info = result.metadata.get("error", "Unknown error")
                
                # Анализ ошибки через ReflectionService
                analysis = await reflection_service.analyze_failure(
                    task_description=message,
                    error=error_info,
                    context=result.metadata
                )
                
                # Генерация исправления
                if analysis and analysis.get("root_cause"):
                    fix = await reflection_service.generate_fix(
                        task_description=message,
                        error=error_info,
                        analysis=analysis
                    )
                    
                    if fix and fix.get("suggested_fix"):
                        # Добавляем предложение по исправлению к результату
                        result.response += f"\n\n💡 Предложение по исправлению:\n{fix.get('suggested_fix')}"
                        result.metadata["reflection_analysis"] = analysis
                        result.metadata["reflection_fix"] = fix
                        
                        logger.info("Reflection analysis completed", extra={
                            "workflow_id": context.workflow_id,
                            "root_cause": analysis.get("root_cause")
                        })
            
            # Анализ успешного выполнения для улучшения
            elif result.metadata and result.metadata.get("execution_success") is True:
                # Можно добавить анализ успешных паттернов для улучшения
                logger.debug("Task completed successfully, skipping reflection")
                
        except Exception as e:
            logger.warning(f"Reflection analysis failed: {e}", exc_info=True)
            # Не прерываем выполнение, если рефлексия не удалась
        
        # Интеграция MetaLearningService для анализа паттернов выполнения
        from app.services.meta_learning_service import MetaLearningService
        
        meta_learning_service = MetaLearningService(context)
        
        try:
            # Анализируем паттерны выполнения для улучшения
            # Получаем agent_id из контекста для анализа
            agent_id = metadata.get("agent_id") or context.metadata.get("agent_id")
            agent_uuid = None
            if agent_id:
                try:
                    from uuid import UUID
                    agent_uuid = UUID(agent_id) if isinstance(agent_id, str) else agent_id
                except (ValueError, TypeError):
                    pass
            
            # Use synchronous analysis to avoid awaiting a coroutine in this context
            patterns = meta_learning_service.analyze_execution_patterns_sync(
                agent_id=agent_uuid,
                time_range_days=1  # Анализ за последний день
            )
            
            if patterns and patterns.get("total_executions", 0) > 0:
                logger.debug(f"Meta-learning analysis completed: {patterns.get('total_executions')} executions analyzed")
                result.metadata = result.metadata or {}
                result.metadata["meta_learning_patterns"] = patterns
                
        except Exception as e:
            logger.warning(f"Meta-learning analysis failed: {e}", exc_info=True)
        
        return result
    
    async def _handle_planning_only(
        self,
        message: str,
        context: ExecutionContext,
        metadata: Dict[str, Any],
        model: Optional[str] = None,
        server_id: Optional[str] = None
    ) -> OrchestrationResult:
        """Обработать запрос только на планирование (без выполнения)"""
        logger.debug("Handling planning-only request")
        
        # Получить модель и server_id для использования
        selected_model, selected_server = self._select_model_and_server(
            context.db, "planning", model, server_id
        )
        
        planning_start = time.time()
        planning_prompt_id = None
        
        # Получить промпт для планирования
        if context.prompt_manager:
            try:
                planning_prompt = await context.prompt_manager.get_prompt_for_stage("planning")
                if planning_prompt:
                    planning_prompt_id = planning_prompt.id
            except Exception as e:
                logger.debug(f"Could not get planning prompt: {e}")
        
        # Создать задачу
        task = Task(
            description=message,
            status=TaskStatus.PENDING
        )
        context.db.add(task)
        context.db.commit()
        context.db.refresh(task)
        
        # Получить PlanningService через ExecutionContext
        from app.services.planning_service import PlanningService
        planning_service = PlanningService(context)
        
        # Генерировать план
        plan = None
        planning_success = False
        try:
            plan = await planning_service.generate_plan(
                task_id=task.id,
                task_description=message,
                context=metadata
            )
            planning_success = plan is not None
        except Exception as e:
            logger.error(f"Plan generation failed: {e}", exc_info=True)
        
        # Записать метрики промпта планирования
        if context.prompt_manager and planning_prompt_id:
            planning_time_ms = (time.time() - planning_start) * 1000
            await context.prompt_manager.record_prompt_usage(
                prompt_id=planning_prompt_id,
                success=planning_success,
                execution_time_ms=planning_time_ms,
                stage="planning"
            )
        
        if plan:
            # Вернуть описание плана
            steps = plan.steps or []
            plan_description = f"Создан план из {len(steps)} шагов:\n\n"
            for i, step in enumerate(steps, 1):
                step_desc = step.get("description", "Без описания")
                plan_description += f"{i}. {step_desc}\n"
            
            return OrchestrationResult(
                response=plan_description,
                model=selected_model,  # Используем реальную модель вместо "planning"
                task_type="planning_only",
                metadata={"plan_id": str(plan.id), "task_id": str(task.id), "used_model": selected_model}
            )
        else:
            return OrchestrationResult(
                response="Не удалось создать план",
                model=selected_model,  # Используем реальную модель
                task_type="planning_only"
            )
    
    def _select_model_and_server(
        self,
        db: Session,
        task_type: Optional[str] = None,
        model: Optional[str] = None,
        server_id: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[Any]]:
        """Выбрать модель и сервер для запроса"""
        selected_model = None
        selected_server = None
        
        # PRIORITY 1: Если server_id указан
        if server_id and server_id.strip():
            selected_server = OllamaService.get_server_by_id(db, server_id.strip())
            if not selected_server:
                raise ValueError(f"Server {server_id} not found")
        
        # PRIORITY 2: Если model указана, найти сервер
        if model and model.strip():
            selected_model = model.strip()
            if not selected_server:
                # Ищем сервер с этой моделью
                all_servers = OllamaService.get_all_active_servers(db)
                for server in all_servers:
                    models = OllamaService.get_models_for_server(db, str(server.id))
                    if any(m.model_name == selected_model for m in models):
                        selected_server = server
                        break
        
        # PRIORITY 3: Автоматический выбор на основе task_type
        if not selected_model or not selected_server:
            model_selector = ModelSelector(db)
            
            if task_type == "code_generation":
                model_obj = model_selector.get_code_model(selected_server)
            elif task_type in ["planning", "reasoning"]:
                model_obj = model_selector.get_planning_model(selected_server)
            else:
                # Общая модель - ищем chat/general модели
                if selected_server:
                    models = OllamaService.get_models_for_server(db, str(selected_server.id))
                    # Фильтруем embedding модели и ищем chat/general
                    chat_models = [
                        m for m in models
                        if m.is_active 
                        and not any(cap in ['embedding'] for cap in (m.capabilities or []))
                        and ("embedding" not in m.model_name.lower() and "embed" not in m.model_name.lower())
                    ]
                    # Предпочитаем модели с chat/general capabilities
                    preferred = [m for m in chat_models if any(cap in ['chat', 'general'] for cap in (m.capabilities or []))]
                    model_obj = preferred[0] if preferred else (chat_models[0] if chat_models else None)
                else:
                    default_server = OllamaService.get_default_server(db)
                    if default_server:
                        models = OllamaService.get_models_for_server(db, str(default_server.id))
                        # Фильтруем embedding модели
                        chat_models = [
                            m for m in models
                            if m.is_active 
                            and not any(cap in ['embedding'] for cap in (m.capabilities or []))
                            and ("embedding" not in m.model_name.lower() and "embed" not in m.model_name.lower())
                        ]
                        preferred = [m for m in chat_models if any(cap in ['chat', 'general'] for cap in (m.capabilities or []))]
                        model_obj = preferred[0] if preferred else (chat_models[0] if chat_models else None)
                        selected_server = default_server
                    else:
                        model_obj = None
            
            if model_obj:
                selected_model = model_obj.model_name
                if not selected_server:
                    selected_server = model_selector.get_server_for_model(model_obj)
        
        # PRIORITY 4: Fallback - любой доступный сервер и модель
        if not selected_model or not selected_server:
            all_servers = OllamaService.get_all_active_servers(db)
            for server in all_servers:
                models = OllamaService.get_models_for_server(db, str(server.id))
                # Фильтруем embedding модели по capabilities И по имени
                chat_models = [
                    m for m in models
                    if m.is_active 
                    and m.model_name
                    and not any(cap.lower() in ['embedding', 'embed'] for cap in (m.capabilities or []))
                    and "embedding" not in m.model_name.lower()
                    and "embed" not in m.model_name.lower()
                ]
                if chat_models:
                    selected_server = server
                    preferred = [
                        m for m in chat_models
                        if any(cap.lower() in ['chat', 'general'] for cap in (m.capabilities or []))
                    ]
                    if preferred:
                        selected_model = preferred[0].model_name
                    else:
                        selected_model = chat_models[0].model_name
                    break
        
        if not selected_model or not selected_server:
            raise ValueError("No available model or server found")
        
        return selected_model, selected_server
    
    async def _get_system_prompt(self, context: ExecutionContext) -> Optional[str]:
        """Получить system prompt для запроса"""
        try:
            # Использовать PromptManager из контекста
            if context.prompt_manager:
                prompt = await context.prompt_manager.get_prompt_for_stage("planning")
                if prompt:
                    return prompt.prompt_text
            else:
                # Если PromptManager не установлен, создать его
                from app.core.prompt_manager import PromptManager
                context.set_prompt_manager(PromptManager(context))
                prompt = await context.prompt_manager.get_prompt_for_stage("planning")
                if prompt:
                    return prompt.prompt_text
        except Exception as e:
            logger.warning(f"Failed to get system prompt: {e}")
        
        return None
    
    def _extract_plan_results(self, plan) -> str:
        """Извлечь результаты выполнения плана"""
        if not plan:
            return "План не найден"
        
        steps = plan.steps or []
        results = []
        
        for i, step in enumerate(steps, 1):
            step_result = step.get("result")
            step_output = step.get("output")
            
            if step_output:
                results.append(f"Шаг {i}: {step_output}")
            elif step_result:
                if isinstance(step_result, dict):
                    result_text = step_result.get("output") or step_result.get("result") or str(step_result)
                else:
                    result_text = str(step_result)
                
                if result_text and result_text != "None":
                    results.append(f"Шаг {i}: {result_text}")
        
        if results:
            return "\n\n".join(results)
        
        if plan.status == "completed":
            return f"План выполнен успешно. Выполнено шагов: {len(steps)}"
        
        return f"План в процессе выполнения. Статус: {plan.status}"
