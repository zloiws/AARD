"""
Planning service for generating and managing task plans
"""
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timezone
import json
import re

from sqlalchemy.orm import Session
from typing import Union

from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.core.ollama_client import OllamaClient, TaskType
from app.core.execution_context import ExecutionContext
from app.services.ollama_service import OllamaService
from app.services.approval_service import ApprovalService
from app.services.prompt_service import PromptService
from app.services.project_metrics_service import ProjectMetricsService
from app.services.plan_template_service import PlanTemplateService
from app.services.plan_evaluation_service import PlanEvaluationService
from app.services.agent_team_service import AgentTeamService
from app.services.agent_team_coordination import AgentTeamCoordination
from app.services.agent_dialog_service import AgentDialogService
from app.services.planning_service_dialog_integration import (
    is_complex_task,
    initiate_agent_dialog_for_planning
)
from app.models.approval import ApprovalRequestType
from app.models.prompt import PromptType
from app.core.tracing import get_tracer, add_span_attributes, get_current_trace_id
from app.services.request_logger import RequestLogger


class PlanningService:
    """Service for generating and managing task plans"""
    
    def __init__(self, db_or_context: Union[Session, ExecutionContext]):
        """
        Initialize PlanningService
        
        Args:
            db_or_context: Either a Session (for backward compatibility) or ExecutionContext
        """
        # Support both ExecutionContext and Session for backward compatibility
        if isinstance(db_or_context, ExecutionContext):
            self.context = db_or_context
            self.db = db_or_context.db
            self.workflow_id = db_or_context.workflow_id
        else:
            # Backward compatibility: create minimal context from Session
            self.db = db_or_context
            self.context = ExecutionContext.from_db_session(db_or_context)
            self.workflow_id = self.context.workflow_id
        
        self.tracer = get_tracer(__name__)
        self.model_logs = []  # Collect model interaction logs for this planning session
        self.current_task_id = None  # Track current task_id for real-time log saving
        # Use WorkflowEngine from context instead of direct WorkflowTracker
        # self.workflow_engine is accessed via self.context.workflow_engine
        self.prompt_service = PromptService(self.db)  # Prompt management service
        self.metrics_service = ProjectMetricsService(self.db)  # Project metrics service
        self.plan_template_service = PlanTemplateService(self.db)  # Plan template service
        self.plan_evaluation_service = PlanEvaluationService(self.db)  # Plan evaluation service for A/B testing
        self.agent_team_service = AgentTeamService(self.db)  # Agent team service
        self.agent_team_coordination = AgentTeamCoordination(self.db)  # Agent team coordination service
        self.agent_dialog_service = AgentDialogService(self.db)  # Agent dialog service for complex tasks
        from app.services.agent_service import AgentService
        self.agent_service = AgentService(self.db)  # Agent service for PlannerAgent
        
        # DecisionRouter for automatic selection of tools and agents for plan steps
        from app.services.decision_router import DecisionRouter
        self.decision_router = DecisionRouter(self.db)
        
        # Task lifecycle manager for workflow transitions
        from app.services.task_lifecycle_manager import TaskLifecycleManager, TaskRole
        self.task_lifecycle_manager = TaskLifecycleManager(self.db)
        # OllamaClient will be created dynamically when needed
        # to use database-backed server/model selection
        
        # Lazy initialization of PlannerAgent
        self._planner_agent = None
    
    def _get_planner_agent(self):
        """
        Get or create PlannerAgent instance
        
        Returns:
            PlannerAgent instance
        """
        if self._planner_agent is None:
            from app.agents.planner_agent import PlannerAgent
            from uuid import uuid4
            
            # Try to find existing PlannerAgent in database
            planner_agent_db = self.agent_service.get_agent_by_name("PlannerAgent")
            
            if not planner_agent_db:
                # Create PlannerAgent if not exists
                planner_agent_db = self.agent_service.create_agent(
                    name="PlannerAgent",
                    description="Planner Agent for task analysis and decomposition",
                    capabilities=["planning", "reasoning", "task_analysis"],
                    model_preference=None,  # Will use planning model from ModelSelector
                    created_by="system"
                )
            
            # Activate the agent if not already active (для тестов - в реальной системе нужно пройти через waiting_approval)
            if planner_agent_db.status != "active":
                planner_agent_db.status = "active"
                self.db.commit()
                self.db.refresh(planner_agent_db)
            
            # Create PlannerAgent instance
            self._planner_agent = PlannerAgent(
                agent_id=planner_agent_db.id,
                agent_service=self.agent_service,
                db_session=self.db
            )
        
        return self._planner_agent
    
    async def generate_alternative_plans(
        self,
        task_description: str,
        task_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
        num_alternatives: int = 3
    ) -> List[Plan]:
        """
        Generate multiple alternative plans for a task using different strategies.
        
        This method generates 2-3 alternative plans in parallel, each with a different
        strategic approach:
        - Plan 1: Conservative approach (minimal risk, more steps)
        - Plan 2: Balanced approach (moderate risk, optimal steps)
        - Plan 3: Aggressive approach (higher risk, fewer steps, faster execution)
        
        Args:
            task_description: Description of the task
            task_id: Optional task ID to link plans to
            context: Additional context (existing artifacts, constraints, etc.)
            num_alternatives: Number of alternative plans to generate (2-3, default: 3)
            
        Returns:
            List of alternative plans in DRAFT status
        """
        import asyncio
        
        # Limit number of alternatives to 2-3
        num_alternatives = max(2, min(3, num_alternatives))
        
        # Define different strategies for each alternative
        strategies = [
            {
                "name": "conservative",
                "description": "Conservative approach: minimal risk, thorough execution",
                "approach": "Take a careful, step-by-step approach with extensive validation at each stage",
                "focus": "reliability and correctness",
                "risk_tolerance": "low"
            },
            {
                "name": "balanced",
                "description": "Balanced approach: optimal trade-off between speed and quality",
                "approach": "Balance efficiency with thoroughness, optimize for common cases",
                "focus": "practicality and efficiency",
                "risk_tolerance": "medium"
            },
            {
                "name": "aggressive",
                "description": "Aggressive approach: maximize speed, accept higher risk",
                "approach": "Prioritize speed and efficiency, minimize steps, assume best-case scenarios",
                "focus": "speed and minimal steps",
                "risk_tolerance": "high"
            }
        ]
        
        # Use only requested number of strategies
        strategies = strategies[:num_alternatives]
        
        # Create enhanced context with strategy information
        enhanced_context = context.copy() if context else {}
        
        # Generate plans in parallel
        async def generate_single_alternative(strategy_info: Dict[str, Any], index: int) -> Plan:
            """Generate a single alternative plan with specific strategy"""
            try:
                # Create strategy-specific context
                strategy_context = {
                    **enhanced_context,
                    "strategy": strategy_info,
                    "alternative_index": index,
                    "alternative_name": strategy_info["name"]
                }
                
                # Generate plan with strategy context (disable alternatives to prevent recursion)
                plan = await self.generate_plan(
                    task_description=task_description,
                    task_id=task_id,
                    context=strategy_context,
                    generate_alternatives=False
                )
                
                # Mark plan as alternative and add strategy metadata
                # Get current strategy and alternatives
                current_strategy = plan.strategy if isinstance(plan.strategy, dict) else {}
                current_alternatives = plan.alternatives if isinstance(plan.alternatives, dict) else {}
                
                # Add alternative metadata to strategy (preserve existing fields)
                updated_strategy = {**current_strategy}
                updated_strategy["alternative_strategy"] = strategy_info["name"]
                updated_strategy["alternative_description"] = strategy_info["description"]
                updated_strategy["alternative_approach"] = strategy_info["approach"]
                updated_strategy["alternative_focus"] = strategy_info["focus"]
                updated_strategy["alternative_risk_tolerance"] = strategy_info["risk_tolerance"]
                
                # Add alternative metadata to alternatives
                updated_alternatives = {**current_alternatives}
                updated_alternatives["is_alternative"] = True
                updated_alternatives["alternative_index"] = index
                updated_alternatives["alternative_name"] = strategy_info["name"]
                
                # Update via ORM (SQLAlchemy should handle JSON fields correctly)
                plan.strategy = updated_strategy
                plan.alternatives = updated_alternatives
                
                self.db.commit()
                self.db.refresh(plan)
                
                # Verify metadata was saved (re-apply if needed)
                if plan.strategy and isinstance(plan.strategy, dict):
                    if "alternative_strategy" not in plan.strategy:
                        # Re-apply if not saved
                        plan.strategy.update({
                            "alternative_strategy": strategy_info["name"],
                            "alternative_description": strategy_info["description"],
                            "alternative_approach": strategy_info["approach"],
                            "alternative_focus": strategy_info["focus"],
                            "alternative_risk_tolerance": strategy_info["risk_tolerance"]
                        })
                        if plan.alternatives and isinstance(plan.alternatives, dict):
                            plan.alternatives.update({
                                "is_alternative": True,
                                "alternative_index": index,
                                "alternative_name": strategy_info["name"]
                            })
                        self.db.commit()
                        self.db.refresh(plan)
                
                logger = self._get_logger()
                if logger:
                    logger.info(
                        f"Generated alternative plan {index + 1} ({strategy_info['name']})",
                        extra={
                            "plan_id": str(plan.id),
                            "strategy": strategy_info["name"],
                            "alternative_index": index
                        }
                    )
                
                return plan
                
            except Exception as e:
                logger = self._get_logger()
                if logger:
                    logger.error(
                        f"Failed to generate alternative plan {index + 1} ({strategy_info.get('name', 'unknown')}): {e}",
                        exc_info=True,
                        extra={
                            "strategy": strategy_info.get("name"),
                            "alternative_index": index
                        }
                    )
                return None
        
        # Generate all alternatives in parallel
        tasks = [
            generate_single_alternative(strategy, i)
            for i, strategy in enumerate(strategies)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        alternative_plans = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger = self._get_logger()
                if logger:
                    logger.error(
                        f"Exception generating alternative plan {i + 1}: {result}",
                        exc_info=True
                    )
            elif result is not None:
                alternative_plans.append(result)
        
        logger = self._get_logger()
        if logger:
            logger.info(
                f"Generated {len(alternative_plans)} alternative plans out of {num_alternatives} requested",
                extra={
                    "requested": num_alternatives,
                    "generated": len(alternative_plans),
                    "task_id": str(task_id) if task_id else None
                }
            )
        
        return alternative_plans
    
    def _add_model_log(
        self, 
        log_type: str, 
        model: str, 
        content: Any, 
        metadata: Optional[Dict[str, Any]] = None,
        stage: Optional[str] = None
    ):
        """
        Add a model interaction log entry
        
        Log types:
        - 'user_request': Запрос от пользователя
        - 'request_analysis': Разбор запроса, определение действий
        - 'action_start': Начало действия
        - 'action_progress': Прогресс действия с изменениями
        - 'action_end': Завершение действия
        - 'request': Запрос к модели
        - 'response': Ответ от модели
        - 'thinking': Промежуточные мысли модели
        - 'result': Финальный результат
        - 'error': Ошибка выполнения
        
        Stages (для workflow):
        - 'user_input': Получен запрос от пользователя
        - 'analysis': Анализ запроса и определение действий
        - 'execution': Выполнение действий
        - 'completion': Завершение операции
        """
        from datetime import datetime, timezone
        
        log_entry = {
            "type": log_type,
            "model": model,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if stage:
            log_entry["stage"] = stage
        
        self.model_logs.append(log_entry)
        
        # Save log to Digital Twin context in real-time if task_id is known
        if self.current_task_id:
            try:
                from app.models.task import Task
                task = self.db.query(Task).filter(Task.id == self.current_task_id).first()
                if task:
                    context = task.get_context()
                    model_logs = context.get("model_logs", [])
                    model_logs.append(log_entry)
                    context["model_logs"] = model_logs
                    task.update_context(context, merge=False)
                    self.db.commit()
            except Exception as e:
                # Don't fail if real-time save fails, just log it
                logger = self._get_logger()
                if logger:
                    logger.warning(f"Failed to save log to Digital Twin in real-time: {e}", exc_info=True)
        
        # Also log to standard logger
        logger = self._get_logger()
        if logger:
            extra_data = {
                "log_type": log_type,
                "model": model,
                "content_preview": str(content)[:100] if content else None,
            }
            if metadata:
                extra_data.update(metadata)
            logger.debug(
                f"Model {log_type}",
                extra=extra_data
            )
        
        return log_entry
    
    def _get_logger(self):
        """Get logger instance, return None if not available"""
        try:
            from app.core.logging_config import LoggingConfig
            return LoggingConfig.get_logger(__name__)
        except:
            return None
    
    def _get_analysis_prompt(self) -> str:
        """Get prompt for task analysis from database or fallback to default
        
        Returns:
            System prompt for task analysis
        """
        # Default fallback prompt
        DEFAULT_ANALYSIS_PROMPT = """You are an expert at task analysis and strategic planning.
Analyze the task and create a strategy that includes:
1. approach: General approach to solving the task
2. assumptions: List of assumptions made
3. constraints: List of constraints and limitations
4. success_criteria: List of criteria for successful completion

Return a JSON object with these fields. Only return valid JSON, no additional text."""
        
        try:
            prompt = self.prompt_service.get_active_prompt(
                name="task_analysis",
                prompt_type=PromptType.SYSTEM,
                level=0
            )
            
            if prompt:
                logger = self._get_logger()
                if logger:
                    logger.debug(
                        f"Using prompt from database: task_analysis (id: {prompt.id})",
                        extra={"prompt_id": str(prompt.id), "prompt_name": "task_analysis"}
                    )
                return prompt.prompt_text
            else:
                logger = self._get_logger()
                if logger:
                    logger.warning(
                        "Prompt 'task_analysis' not found in database, using fallback",
                        extra={"prompt_name": "task_analysis"}
                    )
                return DEFAULT_ANALYSIS_PROMPT
        except Exception as e:
            logger = self._get_logger()
            if logger:
                logger.warning(
                    f"Error loading prompt from database, using fallback: {e}",
                    exc_info=True
                )
            return DEFAULT_ANALYSIS_PROMPT
    
    def _get_decomposition_prompt(self) -> str:
        """Get prompt for task decomposition from database or fallback to default
        
        Returns:
            System prompt for task decomposition
        """
        # Default fallback prompt
        DEFAULT_DECOMPOSITION_PROMPT = """You are an expert at breaking down complex tasks into executable steps.
Create a detailed plan with steps. Each step should have:
- step_id: unique identifier (e.g., "step_1", "step_2")
- description: clear description of what to do
- type: one of "action", "decision", "validation", "approval"
- inputs: what inputs are needed (object)
- expected_outputs: what outputs are expected (object)
- timeout: timeout in seconds (integer)
- retry_policy: {max_attempts: 3, delay: 10}
- dependencies: list of step_ids that must complete first (array)
- approval_required: boolean
- risk_level: "low", "medium", or "high"
- function_call: (optional) if step requires code execution, include function call in format:
  {
    "function": "code_execution_tool",
    "parameters": {
      "code": "python code here",
      "language": "python"
    }
  }

IMPORTANT: For steps that require code execution, use function_call instead of generating code directly.
This ensures safe execution in a sandboxed environment.

Return a JSON array of steps."""
        
        try:
            prompt = self.prompt_service.get_active_prompt(
                name="task_decomposition",
                prompt_type=PromptType.SYSTEM,
                level=0
            )
            
            if prompt:
                logger = self._get_logger()
                if logger:
                    logger.debug(
                        f"Using prompt from database: task_decomposition (id: {prompt.id})",
                        extra={"prompt_id": str(prompt.id), "prompt_name": "task_decomposition"}
                    )
                return prompt.prompt_text
            else:
                logger = self._get_logger()
                if logger:
                    logger.warning(
                        "Prompt 'task_decomposition' not found in database, using fallback",
                        extra={"prompt_name": "task_decomposition"}
                    )
                return DEFAULT_DECOMPOSITION_PROMPT
        except Exception as e:
            logger = self._get_logger()
            if logger:
                logger.warning(
                    f"Error loading prompt from database, using fallback: {e}",
                    exc_info=True
                )
            return DEFAULT_DECOMPOSITION_PROMPT
    
    def _add_and_save_workflow_event(
        self,
        stage,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        plan_id: Optional[UUID] = None
    ):
        """
        Add event to WorkflowEngine and save to DB simultaneously
        
        Args:
            stage: WorkflowStage from WorkflowTracker (for compatibility)
            message: Event message
            details: Event details
            duration_ms: Duration in milliseconds
            plan_id: Plan ID if available
        """
        # Add to WorkflowEngine (for real-time display and state management)
        workflow_engine = self.context.workflow_engine if self.context else None
        if workflow_engine:
            # WorkflowEngine uses WorkflowState, not WorkflowStage
            # Map WorkflowStage to WorkflowState if needed
            from app.core.workflow_engine import WorkflowState
            from app.core.workflow_tracker import WorkflowStage
            
            # Map WorkflowStage to WorkflowState
            stage_mapping = {
                WorkflowStage.USER_REQUEST: WorkflowState.INITIALIZED,
                WorkflowStage.REQUEST_PARSING: WorkflowState.PARSING,
                WorkflowStage.ACTION_DETERMINATION: WorkflowState.PLANNING,
                WorkflowStage.EXECUTION: WorkflowState.EXECUTING,
                WorkflowStage.RESULT: WorkflowState.COMPLETED,
                WorkflowStage.ERROR: WorkflowState.FAILED
            }
            
            workflow_state = stage_mapping.get(stage, None)
            # Only transition if state mapping exists and state is different
            if workflow_state and workflow_engine.get_current_state() != workflow_state:
                # Check if transition is allowed
                if workflow_engine.can_transition_to(workflow_state):
                    workflow_engine.transition_to(
                        workflow_state,
                        message,
                        metadata=details or {}
                    )
                else:
                    # If transition not allowed, just add event to tracker
                    workflow_engine.tracker.add_event(
                        stage=stage,
                        message=message,
                        details=details or {}
                    )
            else:
                # Just add event to tracker without state change
                workflow_engine.tracker.add_event(
                    stage=stage,
                    message=message,
                    details=details or {}
                )
        
        # Save to DB (for persistence)
        self._save_workflow_event_to_db(
            stage=stage,
            message=message,
            details=details,
            duration_ms=duration_ms,
            plan_id=plan_id
        )
    
    def _save_workflow_event_to_db(
        self,
        stage,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        event_type: Optional[str] = None,
        event_source: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        trace_id: Optional[str] = None,
        plan_id: Optional[UUID] = None
    ):
        """
        Save workflow event to database for persistence
        
        Args:
            stage: WorkflowStage from WorkflowTracker
            message: Event message
            details: Event details
            event_type: EventType (defaults to inferred from stage)
            event_source: EventSource (defaults to PLANNER_AGENT)
            duration_ms: Duration in milliseconds
            trace_id: OpenTelemetry trace ID
            plan_id: Plan ID if available
        """
        if not self.workflow_id:
            return  # No workflow ID, skip saving
        
        try:
            from app.services.workflow_event_service import WorkflowEventService
            from app.models.workflow_event import (
                EventSource as DBEventSource,
                EventType as DBEventType,
                EventStatus,
                WorkflowStage as DBWorkflowStage
            )
            from app.core.workflow_tracker import WorkflowStage as TrackerStage
            
            event_service = WorkflowEventService(self.db)
            
            # Map tracker stage to DB workflow stage
            db_stage = event_service.map_tracker_stage_to_workflow_stage(stage)
            
            # Determine event type and source
            if not event_type:
                # Infer from stage
                if stage == TrackerStage.USER_REQUEST:
                    event_type = DBEventType.USER_INPUT
                elif stage == TrackerStage.REQUEST_PARSING or stage == TrackerStage.ACTION_DETERMINATION:
                    event_type = DBEventType.EXECUTION_STEP
                elif stage == TrackerStage.EXECUTION:
                    event_type = DBEventType.EXECUTION_STEP
                elif stage == TrackerStage.RESULT:
                    event_type = DBEventType.COMPLETION
                elif stage == TrackerStage.ERROR:
                    event_type = DBEventType.ERROR
                else:
                    event_type = DBEventType.EXECUTION_STEP
            
            if not event_source:
                event_source = DBEventSource.PLANNER_AGENT
            
            # Get trace ID if not provided
            if not trace_id:
                from app.core.tracing import get_current_trace_id
                trace_id = get_current_trace_id()
            
            # Prepare event data and metadata
            # event_data takes priority, then merge with details (details go to metadata)
            final_event_data = event_data or {}
            
            # Merge details into event_data if event_data was not provided explicitly
            if not event_data and details:
                final_event_data = details.copy()
            elif event_data and details:
                # Merge details into event_data (event_data takes priority)
                final_event_data = {**event_data, **details}
            
            metadata = {
                "planning_service": True,
                "task_id": str(self.current_task_id) if self.current_task_id else None
            }
            
            # Save event
            event_service.save_event(
                workflow_id=self.workflow_id,
                event_type=event_type,
                event_source=event_source,
                stage=db_stage,
                message=message,
                event_data=final_event_data,
                metadata=metadata,
                task_id=self.current_task_id,
                plan_id=plan_id,
                trace_id=trace_id,
                duration_ms=duration_ms,
                status=EventStatus.COMPLETED if stage == TrackerStage.RESULT else EventStatus.IN_PROGRESS
            )
        except Exception as e:
            # Don't fail if DB save fails, just log it
            logger = self._get_logger()
            if logger:
                logger.warning(f"Failed to save workflow event to DB: {e}", exc_info=True)
    
    async def generate_plan(
        self,
        task_description: str,
        task_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
        generate_alternatives: bool = False,
        num_alternatives: int = 3,
        evaluation_weights: Optional[Dict[str, float]] = None
    ) -> Plan:
        """
        Generate a plan for a task using LLM
        
        Workflow logging (HITL observation mode):
        1. user_request: Запрос от пользователя
        2. request_analysis: Разбор запроса, определение действий
        3. action_start/action_progress/action_end: Действия от и до со всеми изменениями
        4. result: Финальный результат
        
        Args:
            task_description: Description of the task
            task_id: Optional task ID to link plan to
            context: Additional context (existing artifacts, constraints, etc.)
            generate_alternatives: If True, generate multiple alternative plans and select the best one (A/B testing)
            num_alternatives: Number of alternative plans to generate (2-3, default: 3). Only used if generate_alternatives=True
            evaluation_weights: Optional weights for plan evaluation criteria. Only used if generate_alternatives=True.
                Default weights: execution_time=0.25, approval_points=0.20, risk_level=0.25, efficiency=0.30
            
        Returns:
            Created plan in DRAFT status (or best plan if generate_alternatives=True)
            All alternative plans are saved in database for comparison
        """
        
        # 0. Try to apply procedural memory patterns (successful plan templates)
        procedural_pattern = None
        agent_id = None
        selected_agent = None
        team_id = None
        selected_team = None
        
        # Get team_id or agent_id from context if provided
        if context and isinstance(context, dict):
            # Check for team_id first (teams take precedence)
            team_id_str = context.get("team_id")
            if team_id_str:
                try:
                    team_id = UUID(team_id_str)
                    selected_team = self.agent_team_service.get_team(team_id)
                    if selected_team and selected_team.status == "active":
                        logger = self._get_logger()
                        if logger:
                            logger.info(
                                f"Using agent team {selected_team.name} for planning",
                                extra={"team_id": str(team_id), "team_name": selected_team.name}
                            )
                    else:
                        team_id = None  # Invalid or inactive team
                except (ValueError, TypeError):
                    pass
            
            # Get agent_id from context if no team specified
            if not team_id:
                agent_id_str = context.get("agent_id")
                if agent_id_str:
                    try:
                        agent_id = UUID(agent_id_str)
                        # Get agent info if agent_id was provided
                        try:
                            from app.services.agent_service import AgentService
                            agent_service = AgentService(self.db)
                            selected_agent = agent_service.get_agent(agent_id)
                        except Exception:
                            pass
                    except (ValueError, TypeError):
                        pass
        
        # If no agent_id or team_id provided, try to select an agent automatically
        if not agent_id and not team_id:
            try:
                from app.services.agent_service import AgentService
                from app.models.agent import AgentCapability
                
                agent_service = AgentService(self.db)
                
                # Determine required capabilities based on task description
                # For now, default to planning capability
                required_capabilities = [AgentCapability.PLANNING.value]
                
                # Simple heuristic: check task description for keywords
                task_lower = task_description.lower()
                if any(keyword in task_lower for keyword in ["code", "program", "script", "function"]):
                    required_capabilities.append(AgentCapability.CODE_GENERATION.value)
                if any(keyword in task_lower for keyword in ["analyze", "review", "check", "test"]):
                    required_capabilities.append(AgentCapability.CODE_ANALYSIS.value)
                
                # Select best agent for task
                selected_agent = agent_service.select_agent_for_task(
                    required_capabilities=required_capabilities
                )
                
                if selected_agent:
                    agent_id = selected_agent.id
                    logger = self._get_logger()
                    if logger:
                        logger.info(
                            f"Auto-selected agent {selected_agent.name} for task",
                            extra={
                                "agent_id": str(agent_id),
                                "agent_name": selected_agent.name,
                                "required_capabilities": required_capabilities
                            }
                        )
            except Exception as e:
                # Don't fail if agent selection fails
                logger = self._get_logger()
                if logger:
                    logger.warning(f"Failed to auto-select agent: {e}", exc_info=True)
        
        if agent_id:
            procedural_pattern = await self._apply_procedural_memory_patterns(
                task_description,
                agent_id
            )
        
        # Get or create task for Digital Twin context and real-time logging
        task = None
        digital_twin_context = {}
        if task_id:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if task:
                digital_twin_context = task.get_context()
        else:
            # Create task first for real-time logging if not provided
            # Get autonomy level from context or use default
            autonomy_level = context.get("autonomy_level", 2) if context else 2
            if autonomy_level not in [0, 1, 2, 3, 4]:
                autonomy_level = 2
            
            task = Task(
                description=task_description[:500],  # Truncate if too long
                status=TaskStatus.PENDING,
                created_by_role="planner",
                autonomy_level=autonomy_level
            )
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            task_id = task.id
        
        # Set current_task_id for real-time log saving
        self.current_task_id = task_id
        
        # Use WorkflowEngine from context for real-time monitoring and state management
        # Use task_id as workflow_id for consistency (so events can be found by task_id)
        from app.core.workflow_engine import WorkflowState
        from app.core.workflow_tracker import WorkflowStage
        
        # Ensure workflow_id matches task_id
        if self.context.workflow_id != str(task_id):
            # Update context workflow_id to match task_id
            self.context.workflow_id = str(task_id)
            # Recreate WorkflowEngine with new workflow_id
            from app.core.workflow_engine import WorkflowEngine
            self.context.set_workflow_engine(WorkflowEngine(self.context))
        
        # Initialize WorkflowEngine if not already initialized
        workflow_engine = self.context.workflow_engine
        if workflow_engine:
            # Start workflow in INITIALIZED state
            workflow_engine.transition_to(
                WorkflowState.INITIALIZED,
                f"Начало планирования задачи: {task_description[:100]}...",
                metadata={"task_id": str(task_id), "task_description": task_description}
            )
        
        # Check if task is complex and needs agent dialog
        conversation_id = None
        dialog_context = {}
        if is_complex_task(task_description, context):
            logger = self._get_logger()
            if logger:
                logger.info(
                    "Task is complex, initiating agent dialog",
                    extra={"task_id": str(task_id), "task_description": task_description[:100]}
                )
            
            # Initiate dialog between agents for complex tasks
            conversation_id, dialog_context = await initiate_agent_dialog_for_planning(
                db=self.db,
                task_description=task_description,
                task_id=task_id,
                context=context
            )
            
            # Save dialog context to Digital Twin
            if conversation_id and task:
                digital_twin_context["agent_dialog"] = {
                    "conversation_id": str(conversation_id),
                    "context": dialog_context,
                    "initiated_at": datetime.now(timezone.utc).isoformat()
                }
                task.update_context(digital_twin_context, merge=False)
                self.db.commit()
        
        # Use dialog context if available for plan generation
        if dialog_context and "discussion_summary" in dialog_context:
            # Enhance task description with dialog insights
            enhanced_task_description = f"{task_description}\n\n[Insights from agent discussion]: {dialog_context.get('discussion_summary', '')}"
            if context:
                context["agent_dialog_insights"] = dialog_context
        else:
            enhanced_task_description = task_description
        
        # Transition to PARSING state
        workflow_engine = self.context.workflow_engine
        if workflow_engine:
            workflow_engine.transition_to(
                WorkflowState.PARSING,
                f"Анализ требований задачи: {task_description[:100]}...",
                metadata={"task_id": str(task_id), "task_description": task_description}
            )
        
        # Save initial workflow start event to DB
        self._add_and_save_workflow_event(
            WorkflowStage.USER_REQUEST,
            f"Начало планирования задачи: {task_description[:100]}...",
            details={"task_description": task_description}
        )
        
        self._add_and_save_workflow_event(
            WorkflowStage.REQUEST_PARSING,
            f"Анализ требований задачи: {task_description[:100]}...",
            details={"task_description": task_description}
        )
        
        # Transition to PLANNING state
        if workflow_engine:
            workflow_engine.transition_to(
                WorkflowState.PLANNING,
                f"Задача создана (ID: {str(task_id)[:8]}...), анализ требований...",
                metadata={"task_id": str(task_id)}
            )
        
        # Search for matching plan templates
        matching_template = None
        try:
            templates = self.plan_template_service.find_matching_templates(
                task_description=task_description,
                limit=1,
                min_success_rate=0.7,
                use_vector_search=True
            )
            if templates:
                matching_template = templates[0]
                logger = self._get_logger()
                if logger:
                    logger.info(
                        f"Found matching plan template: {matching_template.name}",
                        extra={
                            "template_id": str(matching_template.id),
                            "template_name": matching_template.name,
                            "template_category": matching_template.category,
                            "template_success_rate": matching_template.success_rate
                        }
                    )
                self._add_and_save_workflow_event(
                    WorkflowStage.ACTION_DETERMINATION,
                    f"Найден подходящий шаблон плана: {matching_template.name}",
                    details={
                        "template_id": str(matching_template.id),
                        "template_name": matching_template.name,
                        "template_category": matching_template.category
                    }
                )
        except Exception as e:
            logger = self._get_logger()
            if logger:
                logger.warning(f"Failed to search for plan templates: {e}", exc_info=True)
        
        # Merge Digital Twin context with provided context
        enhanced_context = {**(context or {}), **digital_twin_context}
        if procedural_pattern:
            enhanced_context["procedural_pattern"] = procedural_pattern
        if matching_template:
            enhanced_context["plan_template"] = {
                "template_id": str(matching_template.id),
                "template_name": matching_template.name,
                "goal_pattern": matching_template.goal_pattern,
                "strategy_template": matching_template.strategy_template,
                "steps_template": matching_template.steps_template,
                "alternatives_template": matching_template.alternatives_template,
                "category": matching_template.category,
                "tags": matching_template.tags
            }
            # Update template usage count
            self.plan_template_service.update_template_usage(matching_template.id)
        
        # 1. Analyze task and decompose in one optimized request (with Digital Twin context and template)
        self._add_and_save_workflow_event(
            WorkflowStage.EXECUTION,
            "Анализ задачи и декомпозиция (оптимизированный запрос)...",
            details={"stage": "optimized_analysis_and_decomposition"}
        )
        # Use enhanced task description if dialog was conducted
        task_description_for_planning = enhanced_task_description if 'enhanced_task_description' in locals() else task_description
        
        # Optimized: combine analysis and decomposition in one LLM call
        strategy, steps = await self._analyze_and_decompose_task_optimized(
            task_description_for_planning, 
            enhanced_context, 
            task_id
        )
        
        self._add_and_save_workflow_event(
            WorkflowStage.EXECUTION,
            f"Стратегия и шаги созданы (оптимизированный запрос)",
            details={"stage": "optimized_planning_complete", "strategy_created": True, "steps_count": len(steps) if steps else 0}
        )
        
        # Assign selected agent or team to steps if available
        if team_id and selected_team and steps:
            # Assign team to steps - distribution will happen during execution
            for step in steps:
                if not step.get("agent") and not step.get("team_id"):
                    step["team_id"] = str(team_id)
                    # Optionally assign specific agent from team based on step requirements
                    step_role = step.get("role") or step.get("required_role")
                    if step_role:
                        # Try to find agent with matching role in team
                        role_agents = self.agent_team_service.get_agents_by_role(team_id, step_role)
                        if role_agents:
                            step["agent"] = str(role_agents[0].id)
        elif agent_id and steps:
            # Assign single agent to steps
            for step in steps:
                if not step.get("agent"):
                    step["agent"] = str(agent_id)
        
        self._add_and_save_workflow_event(
            WorkflowStage.EXECUTION,
            f"Задача декомпозирована на {len(steps)} шаг(ов), оценка рисков...",
            details={"stage": "risk_assessment", "steps_count": len(steps)}
        )
        
        # 3. Assess risks
        risks = await self._assess_risks(steps, strategy)
        
        self._add_and_save_workflow_event(
            WorkflowStage.EXECUTION,
            f"Риски оценены, создание альтернатив...",
            details={"stage": "alternatives_creation"}
        )
        
        # 4. Create alternatives if needed
        alternatives = await self._create_alternatives(steps, strategy, risks)
        
        # 5. Create plan object (task should already exist from step above)
        
        plan = Plan(
            task_id=task_id,
            version=1,
            goal=task_description,
            strategy=strategy,
            steps=steps,
            alternatives=alternatives,
            status="draft",  # Use lowercase string to match DB constraint
            current_step=0,
            estimated_duration=self._estimate_duration(steps)
        )
        
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        
        # Update Digital Twin context with plan data
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            # Get agent selection info
            agent_selection_info = {
                "available_agents": [],
                "selected_agents": [],
                "selected_agent_id": str(agent_id) if agent_id else None,
                "reasons": {}
            }
            
            # Add template info if template was used
            template_info = None
            if matching_template:
                template_info = {
                    "template_id": str(matching_template.id),
                    "template_name": matching_template.name,
                    "goal_pattern": matching_template.goal_pattern,
                    "strategy_template": matching_template.strategy_template,
                    "steps_template": matching_template.steps_template,
                    "alternatives_template": matching_template.alternatives_template,
                    "category": matching_template.category,
                    "tags": matching_template.tags
                }
            
            # If we have agent_id but not selected_agent object, fetch it
            if agent_id and not selected_agent:
                try:
                    from app.services.agent_service import AgentService
                    agent_service = AgentService(self.db)
                    selected_agent = agent_service.get_agent(agent_id)
                except Exception:
                    pass
            
            if selected_agent:
                agent_selection_info["selected_agents"] = [{
                    "agent_id": str(selected_agent.id),
                    "agent_name": selected_agent.name,
                    "capabilities": selected_agent.capabilities or [],
                    "reason": "Auto-selected based on task requirements" if agent_id == selected_agent.id else "Provided in context"
                }]
            
            # Initialize context if empty
            context_updates = {
                "original_user_request": task_description,
                "active_todos": [
                    {
                        "step_id": step.get("step_id", f"step_{i}"),
                        "description": step.get("description", ""),
                        "status": "pending",
                        "completed": False
                    }
                    for i, step in enumerate(steps)
                ],
                "plan": {
                    "plan_id": str(plan.id),
                    "version": plan.version,
                    "goal": plan.goal,
                    "strategy": strategy,
                    "steps_count": len(steps),
                    "status": plan.status,
                    "created_at": plan.created_at.isoformat() if plan.created_at else None
                },
                "artifacts": [],
                "execution_logs": [],
                "interaction_history": [],
                "model_logs": self.model_logs.copy(),  # Save model interaction logs
                
                # Branching information for observability
                "planning_decisions": {
                    "strategies_considered": [],  # Will be populated if alternatives exist
                    "alternatives": alternatives if alternatives else [],
                    "replanning_history": []  # Will be populated on replanning
                },
                "agent_selection": agent_selection_info,
                "prompt_usage": {
                    "prompts_used": []  # Will track which prompts were used
                },
                "tool_selection": {
                    "available_tools": [],
                    "selected_tools": [],
                    "reasons": {}
                },
                "memory_storage": {
                    "episodic": [],
                    "procedural": [],
                    "what_stored": "",
                    "why_stored": ""
                },
                
                "metadata": {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "task_id": str(task_id),
                    "plan_id": str(plan.id)
                }
            }
            
            # Add template info if template was used
            if matching_template:
                context_updates["plan_template"] = {
                    "template_id": str(matching_template.id),
                    "template_name": matching_template.name,
                    "goal_pattern": matching_template.goal_pattern,
                    "strategy_template": matching_template.strategy_template,
                    "steps_template": matching_template.steps_template,
                    "alternatives_template": matching_template.alternatives_template,
                    "category": matching_template.category,
                    "tags": matching_template.tags
                }
            
            task.update_context(context_updates, merge=False)
            self.db.commit()
            self.db.refresh(task)
        
        # Stage 4: Log final result (HITL observation)
        self._add_model_log(
            log_type="result",
            model="system",
            content={
                "result_type": "plan_created",
                "plan_id": str(plan.id),
                "plan_version": plan.version,
                "steps_count": len(steps),
                "status": plan.status,
                "goal": plan.goal
            },
            metadata={
                "stage": "completion",
                "operation": "generate_plan",
                "task_id": str(task_id) if task_id else None
            },
            stage="completion"
        )
        
        # Complete workflow tracking
        workflow_engine = self.context.workflow_engine if self.context else None
        if workflow_engine:
            from app.core.workflow_tracker import WorkflowStage
            workflow_engine.tracker.add_event(
                WorkflowStage.EXECUTION,
                f"План создан: {len(steps)} шаг(ов), версия {plan.version}",
                details={
                    "plan_id": str(plan.id),
                    "steps_count": len(steps),
                    "version": plan.version
                },
                workflow_id=self.workflow_id
            )
            result_message = f"План успешно создан: {len(steps)} шаг(ов), план ID: {str(plan.id)[:8]}..."
            # Mark workflow as completed
            workflow_engine = self.context.workflow_engine if self.context else None
            if workflow_engine:
                workflow_engine.mark_completed(result=result_message)
            # Save final event to DB
            from app.models.workflow_event import EventType as DBEventType
            self._save_workflow_event_to_db(
                WorkflowStage.RESULT,
                result_message,
                details={
                    "plan_id": str(plan.id),
                    "steps_count": len(steps),
                    "version": plan.version
                },
                event_type=DBEventType.COMPLETION,
                plan_id=plan.id
            )
        
        # Save plan to episodic memory (history of plan changes)
        await self._save_plan_to_episodic_memory(plan, task_id, "plan_created")
        
        # Save active ToDo list to working memory
        await self._save_todo_to_working_memory(task_id, plan)
        
        # Automatically create approval request for the plan
        approval_request = await self._create_plan_approval_request(plan, risks)
        
        # Log request
        try:
            request_logger = RequestLogger(self.db)
            trace_id = get_current_trace_id()
            request_log = request_logger.log_request(
                request_type="plan_generation",
                request_data={
                    "task_description": task_description[:500],
                    "task_id": str(task_id) if task_id else None,
                },
                status="success",
                duration_ms=None,  # Could calculate if needed
                trace_id=trace_id,
            )
            
            # Add consequences
            request_logger.add_consequence(
                request_id=request_log.id,
                consequence_type="plan_created",
                entity_type="plan",
                entity_id=plan.id,
                impact_type="positive",
                impact_score=0.7,
            )
            
            if approval_request:
                request_logger.add_consequence(
                    request_id=request_log.id,
                    consequence_type="approval_created",
                    entity_type="approval",
                    entity_id=approval_request.id,
                    impact_type="positive",
                    impact_score=0.3,
                )
            
            # Update rank after adding consequences
            request_logger.update_rank(request_log.id)
        except Exception as e:
            from app.core.logging_config import LoggingConfig
            logger = LoggingConfig.get_logger(__name__)
            logger.warning(f"Failed to log plan generation: {e}", exc_info=True)
        
        # Track plan quality using PlanningMetricsService
        try:
            from app.services.planning_metrics_service import PlanningMetricsService
            metrics_service = PlanningMetricsService(self.db)
            quality_score = metrics_service.calculate_plan_quality_score(plan)
            
            # Store quality score in plan strategy if available
            if plan.strategy is None:
                plan.strategy = {}
            if isinstance(plan.strategy, dict):
                plan.strategy["quality_score"] = quality_score
                self.db.commit()
                self.db.refresh(plan)
            
            logger = self._get_logger()
            if logger:
                logger.debug(
                    f"Calculated quality score for plan {plan.id}",
                    extra={"plan_id": str(plan.id), "quality_score": quality_score}
                )
        except Exception as e:
            logger = self._get_logger()
            if logger:
                logger.warning(f"Failed to calculate plan quality score: {e}", exc_info=True)
        
        return plan
    
    async def generate_alternative_plans(
        self,
        task_description: str,
        task_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
        num_alternatives: int = 3
    ) -> List[Plan]:
        """
        Generate multiple alternative plans for a task using different strategies.
        
        This method generates 2-3 alternative plans in parallel, each with a different
        strategic approach:
        - Plan 1: Conservative approach (minimal risk, more steps)
        - Plan 2: Balanced approach (moderate risk, optimal steps)
        - Plan 3: Aggressive approach (higher risk, fewer steps, faster execution)
        
        Args:
            task_description: Description of the task
            task_id: Optional task ID to link plans to
            context: Additional context (existing artifacts, constraints, etc.)
            num_alternatives: Number of alternative plans to generate (2-3, default: 3)
            
        Returns:
            List of alternative plans in DRAFT status
        """
        import asyncio
        
        # Limit number of alternatives to 2-3
        num_alternatives = max(2, min(3, num_alternatives))
        
        # Define different strategies for each alternative
        strategies = [
            {
                "name": "conservative",
                "description": "Conservative approach: minimal risk, thorough execution",
                "approach": "Take a careful, step-by-step approach with extensive validation at each stage",
                "focus": "reliability and correctness",
                "risk_tolerance": "low"
            },
            {
                "name": "balanced",
                "description": "Balanced approach: optimal trade-off between speed and quality",
                "approach": "Balance efficiency with thoroughness, optimize for common cases",
                "focus": "practicality and efficiency",
                "risk_tolerance": "medium"
            },
            {
                "name": "aggressive",
                "description": "Aggressive approach: maximize speed, accept higher risk",
                "approach": "Prioritize speed and efficiency, minimize steps, assume best-case scenarios",
                "focus": "speed and minimal steps",
                "risk_tolerance": "high"
            }
        ]
        
        # Use only requested number of strategies
        strategies = strategies[:num_alternatives]
        
        # Create enhanced context with strategy information
        enhanced_context = context.copy() if context else {}
        
        # Generate plans in parallel
        async def generate_single_alternative(strategy_info: Dict[str, Any], index: int) -> Plan:
            """Generate a single alternative plan with specific strategy"""
            try:
                # Create strategy-specific context
                strategy_context = {
                    **enhanced_context,
                    "strategy": strategy_info,
                    "alternative_index": index,
                    "alternative_name": strategy_info["name"]
                }
                
                # Generate plan with strategy context (disable alternatives to prevent recursion)
                plan = await self.generate_plan(
                    task_description=task_description,
                    task_id=task_id,
                    context=strategy_context,
                    generate_alternatives=False
                )
                
                # Mark plan as alternative and add strategy metadata
                # Get current strategy and alternatives
                current_strategy = plan.strategy if isinstance(plan.strategy, dict) else {}
                current_alternatives = plan.alternatives if isinstance(plan.alternatives, dict) else {}
                
                # Add alternative metadata to strategy (preserve existing fields)
                updated_strategy = {**current_strategy}
                updated_strategy["alternative_strategy"] = strategy_info["name"]
                updated_strategy["alternative_description"] = strategy_info["description"]
                updated_strategy["alternative_approach"] = strategy_info["approach"]
                updated_strategy["alternative_focus"] = strategy_info["focus"]
                updated_strategy["alternative_risk_tolerance"] = strategy_info["risk_tolerance"]
                
                # Add alternative metadata to alternatives
                updated_alternatives = {**current_alternatives}
                updated_alternatives["is_alternative"] = True
                updated_alternatives["alternative_index"] = index
                updated_alternatives["alternative_name"] = strategy_info["name"]
                
                # Update via ORM (SQLAlchemy should handle JSON fields correctly)
                plan.strategy = updated_strategy
                plan.alternatives = updated_alternatives
                
                self.db.commit()
                self.db.refresh(plan)
                
                # Verify metadata was saved (re-apply if needed)
                if plan.strategy and isinstance(plan.strategy, dict):
                    if "alternative_strategy" not in plan.strategy:
                        # Re-apply if not saved
                        plan.strategy.update({
                            "alternative_strategy": strategy_info["name"],
                            "alternative_description": strategy_info["description"],
                            "alternative_approach": strategy_info["approach"],
                            "alternative_focus": strategy_info["focus"],
                            "alternative_risk_tolerance": strategy_info["risk_tolerance"]
                        })
                        if plan.alternatives and isinstance(plan.alternatives, dict):
                            plan.alternatives.update({
                                "is_alternative": True,
                                "alternative_index": index,
                                "alternative_name": strategy_info["name"]
                            })
                        self.db.commit()
                        self.db.refresh(plan)
                
                logger = self._get_logger()
                if logger:
                    logger.info(
                        f"Generated alternative plan {index + 1} ({strategy_info['name']})",
                        extra={
                            "plan_id": str(plan.id),
                            "strategy": strategy_info["name"],
                            "alternative_index": index
                        }
                    )
                
                return plan
                
            except Exception as e:
                logger = self._get_logger()
                if logger:
                    logger.error(
                        f"Failed to generate alternative plan {index + 1} ({strategy_info.get('name', 'unknown')}): {e}",
                        exc_info=True,
                        extra={
                            "strategy": strategy_info.get("name"),
                            "alternative_index": index
                        }
                    )
                return None
        
        # Generate all alternatives in parallel
        tasks = [
            generate_single_alternative(strategy, i)
            for i, strategy in enumerate(strategies)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        alternative_plans = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger = self._get_logger()
                if logger:
                    logger.error(
                        f"Exception generating alternative plan {i + 1}: {result}",
                        exc_info=True
                    )
            elif result is not None:
                alternative_plans.append(result)
        
        logger = self._get_logger()
        if logger:
            logger.info(
                f"Generated {len(alternative_plans)} alternative plans out of {num_alternatives} requested",
                extra={
                    "requested": num_alternatives,
                    "generated": len(alternative_plans),
                    "task_id": str(task_id) if task_id else None
                }
            )
        
        return alternative_plans
    
    async def _generate_plan_with_alternatives(
        self,
        task_description: str,
        task_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
        num_alternatives: int = 3,
        evaluation_weights: Optional[Dict[str, float]] = None
    ) -> Plan:
        """
        Generate multiple alternative plans, evaluate them, and return the best one.
        All alternatives are saved for comparison.
        
        Args:
            task_description: Description of the task
            task_id: Optional task ID to link plans to
            context: Additional context
            num_alternatives: Number of alternative plans to generate
            evaluation_weights: Optional weights for evaluation criteria
            
        Returns:
            Best plan based on evaluation
        """
        logger = self._get_logger()
        if logger:
            logger.info(
                f"Generating {num_alternatives} alternative plans for A/B testing",
                extra={
                    "task_description": task_description[:100],
                    "num_alternatives": num_alternatives
                }
            )
        
        # Generate alternative plans
        alternative_plans = await self.generate_alternative_plans(
            task_description=task_description,
            task_id=task_id,
            context=context,
            num_alternatives=num_alternatives
        )
        
        if not alternative_plans:
            # Fallback to single plan generation if alternatives failed
            if logger:
                logger.warning("Failed to generate alternatives, falling back to single plan")
            # Generate single plan without alternatives flag to avoid recursion
            return await self.generate_plan(
                task_description=task_description,
                task_id=task_id,
                context=context,
                generate_alternatives=False
            )
        
        # Evaluate all alternatives
        evaluation_results = self.plan_evaluation_service.evaluate_plans(
            plans=alternative_plans,
            weights=evaluation_weights
        )
        
        if not evaluation_results:
            # Fallback if evaluation failed
            if logger:
                logger.warning("Failed to evaluate alternatives, using first plan")
            return alternative_plans[0]
        
        # Get best plan (first in ranked list)
        best_result = evaluation_results[0]
        best_plan = best_result.plan
        
        # Mark best plan in alternatives metadata
        for plan in alternative_plans:
            if plan.id == best_plan.id:
                if not plan.alternatives:
                    plan.alternatives = {}
                elif not isinstance(plan.alternatives, dict):
                    plan.alternatives = {}
                plan.alternatives["is_best"] = True
                plan.alternatives["evaluation_score"] = best_result.total_score
                plan.alternatives["ranking"] = best_result.ranking
            else:
                if not plan.alternatives:
                    plan.alternatives = {}
                elif not isinstance(plan.alternatives, dict):
                    plan.alternatives = {}
                plan.alternatives["is_best"] = False
                # Find evaluation result for this plan
                for result in evaluation_results:
                    if result.plan_id == plan.id:
                        plan.alternatives["evaluation_score"] = result.total_score
                        plan.alternatives["ranking"] = result.ranking
                        break
        
        # Commit all plans
        self.db.commit()
        
        # Log evaluation results
        if logger:
            logger.info(
                f"Selected best plan from {len(alternative_plans)} alternatives",
                extra={
                    "best_plan_id": str(best_plan.id),
                    "best_plan_score": best_result.total_score,
                    "best_plan_ranking": best_result.ranking,
                    "total_alternatives": len(alternative_plans)
                }
            )
        
        # Add workflow event
        from app.core.workflow_tracker import WorkflowStage
        self._add_and_save_workflow_event(
            WorkflowStage.ACTION_DETERMINATION,
            f"Сгенерировано {len(alternative_plans)} альтернативных планов, выбран лучший (оценка: {best_result.total_score:.2f})",
            details={
                "alternatives_count": len(alternative_plans),
                "best_plan_id": str(best_plan.id),
                "best_plan_score": best_result.total_score,
                "evaluation_results": [
                    {
                        "plan_id": str(r.plan_id),
                        "score": r.total_score,
                        "ranking": r.ranking
                    }
                    for r in evaluation_results
                ]
            }
        )
        
        return best_plan
    
    async def _analyze_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]],
        task_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Analyze task and create strategy
        
        Records prompt metrics through PromptManager if available in ExecutionContext
        """
        """Analyze task and create strategy using Digital Twin context"""
        with self.tracer.start_as_current_span("planning.analyze_task") as span:
            add_span_attributes(
                task_description=task_description[:100],
            )
            
            # Get system prompt from database or fallback
            system_prompt = self._get_analysis_prompt()
            
            # Track which prompt was used
            prompt_used = None
            try:
                prompt_used = self.prompt_service.get_active_prompt(
                    name="task_analysis",
                    prompt_type=PromptType.SYSTEM,
                    level=0
                )
            except Exception:
                pass  # Already logged in _get_analysis_prompt
        
            # Build enhanced prompt with Digital Twin context and plan template
            user_prompt = self._build_enhanced_analysis_prompt(task_description, context, task_id)
            
            # If we have a plan template, add it to the prompt for strategy guidance
            if context and context.get("plan_template"):
                template = context["plan_template"]
                template_guidance = f"\n\n[PLAN TEMPLATE AVAILABLE]\n"
                template_guidance += f"Template: {template.get('template_name', 'Unknown')}\n"
                template_guidance += f"Category: {template.get('category', 'N/A')}\n"
                template_guidance += f"Goal Pattern: {template.get('goal_pattern', 'N/A')}\n"
                if template.get("strategy_template"):
                    template_guidance += f"Suggested Strategy Pattern: {json.dumps(template.get('strategy_template'), indent=2)}\n"
                template_guidance += "\nConsider using this template as a starting point, but adapt it to the specific task requirements.\n"
                user_prompt = user_prompt + template_guidance
            
            # Save used prompt ID to Digital Twin context
            if task_id and prompt_used:
                try:
                    task = self.db.query(Task).filter(Task.id == task_id).first()
                    if task:
                        task_context = task.get_context()
                        prompt_usage = task_context.get("prompt_usage", {})
                        if "prompts_used" not in prompt_usage:
                            prompt_usage["prompts_used"] = []
                        prompt_usage["prompts_used"].append({
                            "prompt_id": str(prompt_used.id),
                            "prompt_name": prompt_used.name,
                            "stage": "analysis",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        task_context["prompt_usage"] = prompt_usage
                        task.update_context(task_context, merge=False)
                        self.db.commit()
                except Exception as e:
                    logger = self._get_logger()
                    if logger:
                        logger.warning(f"Failed to save prompt usage to context: {e}", exc_info=True)
        
        try:
            # Use PlannerAgent for dual-model architecture
            planner_agent = self._get_planner_agent()
            
            # Get model info for logging
            from app.core.model_selector import ModelSelector
            model_selector = ModelSelector(self.db)
            planning_model = model_selector.get_planning_model()
            server = model_selector.get_server_for_model(planning_model) if planning_model else None
            
            # Log request to PlannerAgent
            self._add_model_log(
                log_type="request",
                model=planning_model.model_name if planning_model else "PlannerAgent",
                content={
                    "prompt": task_description[:500] + "..." if len(task_description) > 500 else task_description,
                    "task": "analyze_task",
                    "agent": "PlannerAgent"
                },
                metadata={
                    "server": server.name if server else None,
                    "server_url": server.get_api_url() if server else None,
                    "agent_id": str(planner_agent.agent_id)
                }
            )
            
            # Save workflow event with full prompts before request
            from app.core.workflow_tracker import WorkflowStage
            from app.models.workflow_event import EventType as DBEventType, EventSource as DBEventSource
            
            self._save_workflow_event_to_db(
                stage=WorkflowStage.EXECUTION,
                message=f"Отправка запроса к PlannerAgent для анализа задачи",
                details={
                    "agent": "PlannerAgent",
                    "agent_id": str(planner_agent.agent_id),
                    "model": planning_model.model_name if planning_model else None,
                    "server": server.name if server else None
                },
                event_type=DBEventType.MODEL_REQUEST,
                event_source=DBEventSource.PLANNER_AGENT,
                event_data={
                    "task_description": task_description,
                    "task_type": "analyze_task",
                    "context_used": bool(context),
                    "agent_id": str(planner_agent.agent_id),
                    "model": planning_model.model_name if planning_model else None
                }
            )
            
            # Add workflow event to tracker
            workflow_engine = self.context.workflow_engine if self.context else None
            if workflow_engine:
                workflow_engine.tracker.add_event(
                    WorkflowStage.EXECUTION,
                    f"Отправка запроса к PlannerAgent для анализа задачи...",
                    details={"agent": "PlannerAgent", "agent_id": str(planner_agent.agent_id)},
                    workflow_id=self.workflow_id
                )
            
            # IMPORTANT: Add timeout to prevent infinite loops
            from app.core.config import get_settings
            settings = get_settings()
            
            import asyncio
            import time
            start_time = time.time()
            try:
                # Use PlannerAgent to analyze task
                analysis_result = await asyncio.wait_for(
                    planner_agent.analyze_task(
                        task_description=task_description,
                        context=context
                    ),
                    timeout=float(settings.planning_timeout_seconds)
                )
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Convert PlannerAgent result to expected format
                response_text = json.dumps(analysis_result, ensure_ascii=False, indent=2)
                # Create mock response object for compatibility
                class MockResponse:
                    def __init__(self, text):
                        self.response = text
                response = MockResponse(response_text)
                
                # Record prompt usage metrics
                if prompt_used:
                    try:
                        self.prompt_service.record_usage(
                            prompt_id=prompt_used.id,
                            execution_time_ms=duration_ms
                        )
                    except Exception as e:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to record prompt usage metrics: {e}", exc_info=True)
                
                # Log response from PlannerAgent
                response_text = json.dumps(analysis_result, ensure_ascii=False)
                self._add_model_log(
                    log_type="response",
                    model=planning_model.model_name if planning_model else "PlannerAgent",
                    content={
                        "response": response_text[:2000] + "..." if len(response_text) > 2000 else response_text,
                        "full_length": len(response_text),
                        "analysis": analysis_result
                    },
                    metadata={
                        "duration_ms": duration_ms,
                        "task": "analyze_task",
                        "agent": "PlannerAgent"
                    }
                )
                
                # Save workflow event with full response
                self._save_workflow_event_to_db(
                    stage=WorkflowStage.EXECUTION,
                    message=f"Получен ответ от PlannerAgent",
                    details={
                        "agent": "PlannerAgent",
                        "agent_id": str(planner_agent.agent_id),
                        "duration_ms": duration_ms,
                        "response_length": len(response_text),
                        "model": planning_model.model_name if planning_model else None
                    },
                    event_type=DBEventType.MODEL_RESPONSE,
                    event_source=DBEventSource.PLANNER_AGENT,
                    duration_ms=duration_ms,
                    event_data={
                        "full_response": response_text,
                        "analysis_result": analysis_result,
                        "response_length": len(response_text),
                        "task_type": "analyze_task",
                        "agent_id": str(planner_agent.agent_id),
                        "model": planning_model.model_name if planning_model else None,
                        "duration_ms": duration_ms
                    }
                )
                
                # Add workflow event for model response
                workflow_engine = self.context.workflow_engine if self.context else None
                if workflow_engine:
                    workflow_engine.tracker.add_event(
                        WorkflowStage.EXECUTION,
                        f"Получен ответ от PlannerAgent ({duration_ms}ms), обработка стратегии...",
                        details={
                            "agent": "PlannerAgent",
                            "agent_id": str(planner_agent.agent_id),
                            "duration_ms": duration_ms,
                            "response_length": len(response_text)
                        },
                        workflow_id=self.workflow_id
                    )
            except asyncio.TimeoutError:
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                analysis_success = False
                
                # Record prompt failure through PromptManager if available
                if prompt_used and hasattr(self, 'context') and self.context.prompt_manager:
                    try:
                        await self.context.prompt_manager.record_prompt_usage(
                            prompt_id=prompt_used.id,
                            success=False,
                            execution_time_ms=duration_ms,
                            stage="planning_analysis"
                        )
                    except Exception as e:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to record prompt failure through PromptManager: {e}", exc_info=True)
                
                # Also record through PromptService for backward compatibility
                if prompt_used:
                    try:
                        self.prompt_service.record_usage(
                            prompt_id=prompt_used.id,
                            execution_time_ms=duration_ms
                        )
                        self.prompt_service.record_failure(prompt_used.id)
                    except Exception as e:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to record prompt failure metrics: {e}", exc_info=True)
                
                self._add_model_log(
                    log_type="error",
                    model=planning_model.model_name,
                    content="Strategy analysis timed out after 5 minutes",
                    metadata={
                        "duration_ms": duration_ms,
                        "task": "analyze_task",
                        "error_type": "timeout"
                    }
                )
                raise ValueError("Strategy analysis timed out after 5 minutes. Task may be too complex or model is stuck.")
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
                analysis_success = False
                
                # Record prompt failure through PromptManager if available
                if prompt_used and hasattr(self, 'context') and self.context.prompt_manager:
                    try:
                        await self.context.prompt_manager.record_prompt_usage(
                            prompt_id=prompt_used.id,
                            success=False,
                            execution_time_ms=duration_ms,
                            stage="planning_analysis"
                        )
                    except Exception:
                        pass  # Already logged above
                
                # Also record through PromptService for backward compatibility
                if prompt_used:
                    try:
                        self.prompt_service.record_usage(
                            prompt_id=prompt_used.id,
                            execution_time_ms=duration_ms
                        )
                        self.prompt_service.record_failure(prompt_used.id)
                    except Exception:
                        pass  # Already logged above
                
                raise
            
            # Stage 2: Convert PlannerAgent result to strategy format
            # PlannerAgent returns: {goal, requirements, constraints, success_criteria, complexity, estimated_steps}
            # We need: {approach, assumptions, constraints, success_criteria}
            
            # Convert analysis_result to strategy format
            strategy = {
                "approach": analysis_result.get("goal", "Standard approach"),
                "assumptions": analysis_result.get("requirements", []),
                "constraints": analysis_result.get("constraints", []),
                "success_criteria": analysis_result.get("success_criteria", []),
                "complexity": analysis_result.get("complexity", "medium"),
                "estimated_steps": analysis_result.get("estimated_steps", 3)
            }
            
            # Ensure required fields
            strategy.setdefault("approach", "Standard approach")
            strategy.setdefault("assumptions", [])
            strategy.setdefault("constraints", [])
            strategy.setdefault("success_criteria", [])
            
            # Record metrics for task analysis
            try:
                from datetime import timedelta
                from app.models.project_metric import MetricType, MetricPeriod
                
                now = datetime.now(timezone.utc)
                # Round to hour for consistent period boundaries
                period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                period_end = now.replace(minute=0, second=0, microsecond=0)
                
                self.metrics_service.record_metric(
                    metric_type=MetricType.PERFORMANCE,
                    metric_name="task_analysis_time",
                    value=duration_ms / 1000.0,  # Convert to seconds
                    period=MetricPeriod.HOUR,
                    period_start=period_start,
                    period_end=period_end,
                    count=1,
                    min_value=duration_ms / 1000.0,
                    max_value=duration_ms / 1000.0,
                    sum_value=duration_ms / 1000.0
                )
            except Exception as e:
                logger = self._get_logger()
                if logger:
                    logger.warning(f"Failed to record task analysis metrics: {e}", exc_info=True)
            
            # Log parsed strategy
            self._add_model_log(
                log_type="action_progress",
                model=planning_model.model_name if planning_model else "PlannerAgent",
                content={
                    "action": "strategy_parsed",
                    "strategy": strategy,
                    "analysis_result": analysis_result
                },
                metadata={
                    "stage": "analysis",
                    "operation": "analyze_task",
                    "agent": "PlannerAgent"
                },
                stage="analysis"
            )
            
            # Record success for prompt usage
            if prompt_used:
                try:
                    self.prompt_service.record_success(prompt_used.id)
                    
                    # Analyze prompt performance asynchronously (don't block)
                    try:
                        import asyncio
                        asyncio.create_task(
                            self.prompt_service.analyze_prompt_performance(
                                prompt_id=prompt_used.id,
                                task_description=task_description[:500],
                                result=strategy,
                                success=True,
                                execution_metadata={
                                    "duration_ms": duration_ms,
                                    "stage": "analysis",
                                    "response_length": len(response_text) if 'response_text' in locals() else 0,
                                    "agent": "PlannerAgent"
                                }
                            )
                        )
                    except Exception as e2:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to analyze prompt performance: {e2}", exc_info=True)
                except Exception as e:
                    logger = self._get_logger()
                    if logger:
                        logger.warning(f"Failed to record prompt success: {e}", exc_info=True)
            
            return strategy
            
        except Exception as e:
            # Record failure for prompt usage
            if prompt_used:
                try:
                    self.prompt_service.record_failure(prompt_used.id)
                    
                    # Analyze prompt performance asynchronously (don't block)
                    try:
                        import asyncio
                        asyncio.create_task(
                            self.prompt_service.analyze_prompt_performance(
                                prompt_id=prompt_used.id,
                                task_description=task_description[:500],
                                result=str(e),
                                success=False,
                                execution_metadata={
                                    "error_type": type(e).__name__,
                                    "stage": "analysis"
                                }
                            )
                        )
                    except Exception as e3:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to analyze prompt performance: {e3}", exc_info=True)
                except Exception as e2:
                    logger = self._get_logger()
                    if logger:
                        logger.warning(f"Failed to record prompt failure: {e2}", exc_info=True)
            
            # Fallback strategy
            return {
                "approach": "Standard step-by-step approach",
                "assumptions": ["All required resources are available"],
                "constraints": ["Must follow system constraints"],
                "success_criteria": ["Task completed successfully"]
            }
    
    async def _decompose_task(
        self,
        task_description: str,
        strategy: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        task_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Decompose task into executable steps"""
        with self.tracer.start_as_current_span("planning.decompose_task") as span:
            add_span_attributes(
                task_description=task_description[:100],
            )
            
            # Get system prompt from database or fallback
            system_prompt = self._get_decomposition_prompt()
            
            # Track which prompt was used
            prompt_used = None
            try:
                prompt_used = self.prompt_service.get_active_prompt(
                    name="task_decomposition",
                    prompt_type=PromptType.SYSTEM,
                    level=0
                )
            except Exception:
                pass  # Already logged in _get_decomposition_prompt
        
        # Build enhanced prompt with Digital Twin context
        strategy_str = json.dumps(strategy, indent=2, ensure_ascii=False)
        
        # Get Digital Twin context if task exists
        digital_twin_context = {}
        if task_id:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if task:
                digital_twin_context = task.get_context()
                
                # Save used prompt ID to Digital Twin context
                if prompt_used:
                    try:
                        prompt_usage = digital_twin_context.get("prompt_usage", {})
                        if "prompts_used" not in prompt_usage:
                            prompt_usage["prompts_used"] = []
                        prompt_usage["prompts_used"].append({
                            "prompt_id": str(prompt_used.id),
                            "prompt_name": prompt_used.name,
                            "stage": "decomposition",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        digital_twin_context["prompt_usage"] = prompt_usage
                        task.update_context(digital_twin_context, merge=False)
                        self.db.commit()
                    except Exception as e:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to save prompt usage to context: {e}", exc_info=True)
        
        # Build context sections
        sections = []
        
        # Add strategy
        sections.append(f"Strategy:\n{strategy_str}")
        
        # Add existing artifacts (useful for dependencies)
        artifacts = digital_twin_context.get("artifacts", [])
        if artifacts:
            sections.append(f"\nExisting Artifacts (available for use):\n{json.dumps(artifacts, indent=2, ensure_ascii=False)}")
        
        # Add context from parameters
        if context:
            filtered_context = {k: v for k, v in context.items() 
                              if k not in ["artifacts", "original_user_request"]}
            if filtered_context:
                sections.append(f"\nAdditional Context:\n{json.dumps(filtered_context, indent=2, ensure_ascii=False)}")
        
        context_str = "\n".join(sections)
        
        user_prompt = f"""Task: {task_description}

{context_str}

Break down this task into executable steps. Return only a valid JSON array."""
        
        try:
            # Use PlannerAgent for dual-model architecture
            planner_agent = self._get_planner_agent()
            
            # Get model info for logging
            from app.core.model_selector import ModelSelector
            model_selector = ModelSelector(self.db)
            planning_model = model_selector.get_planning_model()
            server = model_selector.get_server_for_model(planning_model) if planning_model else None
            
            # Log request to PlannerAgent
            self._add_model_log(
                log_type="request",
                model=planning_model.model_name if planning_model else "PlannerAgent",
                content={
                    "prompt": task_description[:500] + "..." if len(task_description) > 500 else task_description,
                    "task": "decompose_task",
                    "strategy": strategy,
                    "agent": "PlannerAgent"
                },
                metadata={
                    "server": server.name if server else None,
                    "server_url": server.get_api_url() if server else None,
                    "agent_id": str(planner_agent.agent_id)
                }
            )
            
            # Save workflow event with full prompts before request
            from app.core.workflow_tracker import WorkflowStage
            from app.models.workflow_event import EventType as DBEventType, EventSource as DBEventSource
            
            self._save_workflow_event_to_db(
                stage=WorkflowStage.EXECUTION,
                message=f"Декомпозиция задачи на шаги через PlannerAgent",
                details={
                    "agent": "PlannerAgent",
                    "agent_id": str(planner_agent.agent_id),
                    "model": planning_model.model_name if planning_model else None,
                    "server": server.name if server else None
                },
                event_type=DBEventType.MODEL_REQUEST,
                event_source=DBEventSource.PLANNER_AGENT,
                event_data={
                    "task_description": task_description,
                    "task_type": "decompose_task",
                    "strategy": strategy if isinstance(strategy, dict) else {"strategy": str(strategy)},
                    "context_used": bool(context),
                    "agent_id": str(planner_agent.agent_id)
                }
            )
            
            # Add workflow event for decomposition request
            workflow_engine = self.context.workflow_engine if self.context else None
            if workflow_engine:
                workflow_engine.tracker.add_event(
                    WorkflowStage.EXECUTION,
                    f"Декомпозиция задачи на шаги через PlannerAgent...",
                    details={"agent": "PlannerAgent", "agent_id": str(planner_agent.agent_id)},
                    workflow_id=self.workflow_id
                )
            
            # IMPORTANT: Add timeout to prevent infinite loops
            from app.core.config import get_settings
            settings = get_settings()
            
            import asyncio
            import time
            start_time = time.time()
            try:
                # Use PlannerAgent to decompose task
                steps_result = await asyncio.wait_for(
                    planner_agent.decompose_task(
                        task_description=task_description,
                        analysis=strategy,
                        context=context
                    ),
                    timeout=float(settings.planning_timeout_seconds)
                )
                duration_ms = int((time.time() - start_time) * 1000)
                decomposition_success = True
                
                # steps_result is already a list of steps from PlannerAgent
                steps = steps_result
                
                # Record prompt usage metrics through PromptManager if available
                if prompt_used and hasattr(self, 'context') and self.context.prompt_manager:
                    try:
                        await self.context.prompt_manager.record_prompt_usage(
                            prompt_id=prompt_used.id,
                            success=True,
                            execution_time_ms=duration_ms,
                            stage="planning_decomposition"
                        )
                    except Exception as e:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to record prompt usage through PromptManager: {e}", exc_info=True)
                
                # Also record through PromptService for backward compatibility
                if prompt_used:
                    try:
                        self.prompt_service.record_usage(
                            prompt_id=prompt_used.id,
                            execution_time_ms=duration_ms
                        )
                        self.prompt_service.record_success(prompt_used.id)
                    except Exception as e:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to record prompt usage metrics: {e}", exc_info=True)
                
                # Log response from PlannerAgent
                steps_count = len(steps) if isinstance(steps, list) else 0
                steps_json = json.dumps(steps, ensure_ascii=False, indent=2)
                
                self._add_model_log(
                    log_type="response",
                    model=planning_model.model_name if planning_model else "PlannerAgent",
                    content={
                        "response": steps_json[:2000] + "..." if len(steps_json) > 2000 else steps_json,
                        "full_length": len(steps_json),
                        "steps_count": steps_count,
                        "steps": steps[:3] if steps_count > 0 else []  # First 3 steps as sample
                    },
                    metadata={
                        "duration_ms": duration_ms,
                        "task": "decompose_task",
                        "agent": "PlannerAgent"
                    }
                )
                
                # Save workflow event with full response
                from app.core.workflow_tracker import WorkflowStage
                from app.models.workflow_event import EventType as DBEventType, EventSource as DBEventSource
                
                self._save_workflow_event_to_db(
                    stage=WorkflowStage.EXECUTION,
                    message=f"Получен ответ от PlannerAgent, декомпозировано на {steps_count} шаг(ов)",
                    details={
                        "agent": "PlannerAgent",
                        "agent_id": str(planner_agent.agent_id),
                        "duration_ms": duration_ms,
                        "steps_count": steps_count,
                        "model": planning_model.model_name if planning_model else None
                    },
                    event_type=DBEventType.MODEL_RESPONSE,
                    event_source=DBEventSource.PLANNER_AGENT,
                    duration_ms=duration_ms,
                    event_data={
                        "full_response": steps_json,
                        "steps": steps,
                        "response_length": len(steps_json),
                        "task_type": "decompose_task",
                        "steps_count": steps_count,
                        "agent_id": str(planner_agent.agent_id)
                    }
                )
                
                # Record metrics for task decomposition
                try:
                    from datetime import timedelta
                    from app.models.project_metric import MetricType, MetricPeriod
                    
                    now = datetime.now(timezone.utc)
                    # Round to hour for consistent period boundaries
                    period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                    period_end = now.replace(minute=0, second=0, microsecond=0)
                    
                    self.metrics_service.record_metric(
                        metric_type=MetricType.PERFORMANCE,
                        metric_name="task_decomposition_time",
                        value=duration_ms / 1000.0,  # Convert to seconds
                        period=MetricPeriod.HOUR,
                        period_start=period_start,
                        period_end=period_end,
                        count=1,
                        min_value=duration_ms / 1000.0,
                        max_value=duration_ms / 1000.0,
                        sum_value=duration_ms / 1000.0,
                        metric_metadata={"steps_count": steps_count}
                    )
                except Exception as e:
                    logger = self._get_logger()
                    if logger:
                        logger.warning(f"Failed to record task decomposition metrics: {e}", exc_info=True)
                
                # Add workflow event for decomposition response
                workflow_engine = self.context.workflow_engine if self.context else None
                if workflow_engine:
                    workflow_engine.tracker.add_event(
                        WorkflowStage.EXECUTION,
                        f"Получен ответ от PlannerAgent, декомпозировано на {steps_count} шаг(ов) ({duration_ms}ms)...",
                        details={
                            "agent": "PlannerAgent",
                            "agent_id": str(planner_agent.agent_id),
                            "duration_ms": duration_ms,
                            "steps_count": steps_count
                        },
                        workflow_id=self.workflow_id
                    )
                
                # Ensure it's a list
                if not isinstance(steps, list):
                    steps = []
                
                # Validate and fix steps, and create FunctionCall for each step
                validated_steps = []
                planner_agent = self._get_planner_agent()
                
                for i, step in enumerate(steps):
                    if not isinstance(step, dict):
                        continue
                    
                    # Ensure required fields
                    step.setdefault("step_id", f"step_{i+1}")
                    step.setdefault("description", f"Step {i+1}")
                    step.setdefault("type", "action")
                    step.setdefault("inputs", {})
                    step.setdefault("expected_outputs", {})
                    step.setdefault("timeout", 300)
                    step.setdefault("retry_policy", {"max_attempts": 3, "delay": 10})
                    step.setdefault("dependencies", [])
                    step.setdefault("approval_required", False)
                    step.setdefault("risk_level", "low")
                    step.setdefault("agent", None)
                    step.setdefault("tool", None)
                    
                    # Use DecisionRouter to automatically select tools and agents for steps if not specified
                    if not step.get("tool") and not step.get("agent") and step.get("type") == "action":
                        try:
                            routing_decision = await self.decision_router.route_task(
                                task_description=step.get("description", ""),
                                task_type=step.get("type", "action"),
                                requirements=step.get("requirements", {}),
                                context={
                                    "step_id": step.get("step_id"),
                                    "plan_context": context or {},
                                    "strategy": strategy
                                }
                            )
                            
                            # Assign selected tool or agent to step
                            if routing_decision.get("tool"):
                                step["tool"] = routing_decision["tool"].get("id") or routing_decision["tool"].get("name")
                                logger = self._get_logger()
                                if logger:
                                    logger.info(
                                        f"DecisionRouter selected tool {step['tool']} for step {step.get('step_id')}",
                                        extra={
                                            "step_id": step.get("step_id"),
                                            "tool": step["tool"],
                                            "reasoning": routing_decision.get("reasoning", "")
                                        }
                                    )
                            
                            if routing_decision.get("agent"):
                                step["agent"] = routing_decision["agent"].get("id") or routing_decision["agent"].get("name")
                                logger = self._get_logger()
                                if logger:
                                    logger.info(
                                        f"DecisionRouter selected agent {step['agent']} for step {step.get('step_id')}",
                                        extra={
                                            "step_id": step.get("step_id"),
                                            "agent": step["agent"],
                                            "reasoning": routing_decision.get("reasoning", "")
                                        }
                                    )
                        except Exception as e:
                            logger = self._get_logger()
                            if logger:
                                logger.warning(
                                    f"Failed to use DecisionRouter for step {step.get('step_id')}: {e}",
                                    exc_info=True
                                )
                            # Continue without tool/agent selection if DecisionRouter fails
                    
                    # Create FunctionCall for steps that require code execution
                    # Use PlannerAgent to create code prompt for CoderAgent
                    if step.get("type") == "action" and not step.get("tool") and not step.get("agent"):
                        try:
                            function_call = await planner_agent.create_code_prompt(
                                step=step,
                                plan_context={
                                    "task_description": task_description,
                                    "strategy": strategy,
                                    "context": context
                                }
                            )
                            # Add function_call to step
                            step["function_call"] = function_call.to_dict()
                        except Exception as e:
                            logger = self._get_logger()
                            if logger:
                                logger.warning(
                                    f"Failed to create function call for step {step.get('step_id')}: {e}",
                                    exc_info=True
                                )
                    
                    validated_steps.append(step)
                
                # If no steps generated, create a default one
                if not validated_steps:
                    validated_steps = [{
                        "step_id": "step_1",
                        "description": task_description,
                        "type": "action",
                        "inputs": {},
                        "expected_outputs": {},
                        "timeout": 300,
                        "retry_policy": {"max_attempts": 3, "delay": 10},
                        "dependencies": [],
                        "approval_required": False,
                        "risk_level": "medium",
                        "agent": None,
                        "tool": None
                    }]
                
                # Record success for prompt usage (if steps were successfully generated)
                if prompt_used and len(validated_steps) > 0:
                    try:
                        self.prompt_service.record_success(prompt_used.id)
                        
                        # Analyze prompt performance asynchronously (don't block)
                        try:
                            import asyncio
                            asyncio.create_task(
                                self.prompt_service.analyze_prompt_performance(
                                    prompt_id=prompt_used.id,
                                    task_description=task_description[:500],
                                    result={"steps_count": len(validated_steps), "steps": validated_steps[:3]},  # First 3 steps as sample
                                    success=True,
                                    execution_metadata={
                                        "duration_ms": duration_ms,
                                        "stage": "decomposition",
                                        "steps_count": len(validated_steps),
                                        "response_length": len(steps_json) if 'steps_json' in locals() else 0,
                                        "agent": "PlannerAgent"
                                    }
                                )
                            )
                        except Exception as e3:
                            logger = self._get_logger()
                            if logger:
                                logger.warning(f"Failed to analyze prompt performance: {e3}", exc_info=True)
                    except Exception as e2:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to record prompt success: {e2}", exc_info=True)
                
                return validated_steps
                
            except asyncio.TimeoutError:
                import time
                duration_ms = int((time.time() - start_time) * 1000)
                decomposition_success = False
                
                # Record prompt failure through PromptManager if available
                if prompt_used and hasattr(self, 'context') and self.context.prompt_manager:
                    try:
                        await self.context.prompt_manager.record_prompt_usage(
                            prompt_id=prompt_used.id,
                            success=False,
                            execution_time_ms=duration_ms,
                            stage="planning_decomposition"
                        )
                    except Exception as e:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to record prompt failure through PromptManager: {e}", exc_info=True)
                
                # Record failure for prompt usage
                if prompt_used:
                    try:
                        self.prompt_service.record_usage(
                            prompt_id=prompt_used.id,
                            execution_time_ms=duration_ms
                        )
                        self.prompt_service.record_failure(prompt_used.id)
                        
                        # Analyze prompt performance asynchronously (don't block)
                        try:
                            import asyncio
                            asyncio.create_task(
                                self.prompt_service.analyze_prompt_performance(
                                    prompt_id=prompt_used.id,
                                    task_description=task_description[:500],
                                    result="Task decomposition timed out after 5 minutes",
                                    success=False,
                                    execution_metadata={
                                        "error_type": "timeout",
                                        "stage": "decomposition",
                                        "duration_ms": duration_ms
                                    }
                                )
                            )
                        except Exception as e3:
                            logger = self._get_logger()
                            if logger:
                                logger.warning(f"Failed to analyze prompt performance: {e3}", exc_info=True)
                    except Exception as e2:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to record prompt failure: {e2}", exc_info=True)
                
                self._add_model_log(
                    log_type="error",
                    model=planning_model.model_name,
                    content="Task decomposition timed out after 5 minutes",
                    metadata={
                        "duration_ms": duration_ms,
                        "task": "decompose_task",
                        "error_type": "timeout"
                    }
                )
                raise ValueError("Task decomposition timed out after 5 minutes. Task may be too complex or model is stuck.")
            
        except Exception as e:
            # Record failure for prompt usage
            if prompt_used:
                try:
                    self.prompt_service.record_failure(prompt_used.id)
                    
                    # Analyze prompt performance asynchronously (don't block)
                    try:
                        import asyncio
                        asyncio.create_task(
                            self.prompt_service.analyze_prompt_performance(
                                prompt_id=prompt_used.id,
                                task_description=task_description[:500],
                                result=str(e),
                                success=False,
                                execution_metadata={
                                    "error_type": type(e).__name__,
                                    "stage": "decomposition"
                                }
                            )
                        )
                    except Exception as e3:
                        logger = self._get_logger()
                        if logger:
                            logger.warning(f"Failed to analyze prompt performance: {e3}", exc_info=True)
                except Exception as e2:
                    logger = self._get_logger()
                    if logger:
                        logger.warning(f"Failed to record prompt failure: {e2}", exc_info=True)
            
            # Fallback to single step
            return [{
                "step_id": "step_1",
                "description": task_description,
                "type": "action",
                "inputs": {},
                "expected_outputs": {},
                "timeout": 300,
                "retry_policy": {"max_attempts": 3, "delay": 10},
                "dependencies": [],
                "approval_required": False,
                "risk_level": "medium",
                "agent": None,
                "tool": None
            }]
    
    async def _assess_risks(
        self,
        steps: List[Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risks for the plan"""
        
        # Simple risk assessment based on steps
        high_risk_steps = [s for s in steps if s.get("risk_level") == "high"]
        approval_steps = [s for s in steps if s.get("approval_required")]
        
        # Calculate overall risk as float (0.0 to 1.0)
        if high_risk_steps:
            overall_risk = 0.8  # High risk
        elif approval_steps:
            overall_risk = 0.5  # Medium risk
        else:
            overall_risk = 0.2  # Low risk
        
        return {
            "overall_risk": overall_risk,
            "identified_risks": [f"Step {s.get('step_id', 'unknown')} requires approval" for s in approval_steps],
            "mitigation_strategies": ["Review high-risk steps before execution"] if high_risk_steps else [],
            "high_risk_steps": len(high_risk_steps),
            "approval_points": len(approval_steps),
            "total_steps": len(steps)
        }
    
    async def _create_alternatives(
        self,
        steps: List[Dict[str, Any]],
        strategy: Dict[str, Any],
        risks: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create alternative approaches if needed"""
        
        # For now, return empty alternatives
        # Can be enhanced with LLM-based alternative generation
        return []
    
    def _estimate_duration(self, steps: List[Dict[str, Any]]) -> int:
        """Estimate total duration in seconds"""
        total = 0
        for step in steps:
            total += step.get("timeout", 300)
        return total
    
    def _build_enhanced_analysis_prompt(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]],
        task_id: Optional[UUID] = None
    ) -> str:
        """Build enhanced prompt with Digital Twin context"""
        
        # Get Digital Twin context if task exists
        digital_twin_context = {}
        if task_id:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if task:
                digital_twin_context = task.get_context()
        
        # Build structured context sections
        sections = []
        
        # Original request from Digital Twin
        if digital_twin_context.get("original_user_request"):
            sections.append(f"Original Request:\n{digital_twin_context['original_user_request']}")
        
        # Previous plans (if any) - show last 2 versions
        historical_todos = digital_twin_context.get("historical_todos", [])
        if historical_todos:
            recent_history = historical_todos[-2:] if len(historical_todos) > 2 else historical_todos
            sections.append(f"\nPrevious Plans (for reference):\n{json.dumps(recent_history, indent=2, ensure_ascii=False)}")
        
        # Existing artifacts
        artifacts = digital_twin_context.get("artifacts", [])
        if artifacts:
            # Include only relevant artifacts (last 5)
            recent_artifacts = artifacts[-5:] if len(artifacts) > 5 else artifacts
            sections.append(f"\nExisting Artifacts:\n{json.dumps(recent_artifacts, indent=2, ensure_ascii=False)}")
        
        # Recent interactions (last 3)
        interaction_history = digital_twin_context.get("interaction_history", [])
        if interaction_history:
            recent_interactions = interaction_history[-3:]
            sections.append(f"\nRecent Interactions:\n{json.dumps(recent_interactions, indent=2, ensure_ascii=False)}")
        
        # Additional context from parameters
        if context:
            # Filter out internal fields
            filtered_context = {k: v for k, v in context.items() 
                              if k not in ["original_user_request", "artifacts", "interaction_history", "historical_todos"]}
            if filtered_context:
                sections.append(f"\nAdditional Context:\n{json.dumps(filtered_context, indent=2, ensure_ascii=False)}")
        
        # Build final prompt
        context_str = "\n".join(sections) if sections else ""
        
        if context_str:
            return f"""Task: {task_description}

{context_str}

Analyze this task considering the context above and create a strategic plan. Return only valid JSON."""
        else:
            return f"""Task: {task_description}

Analyze this task and create a strategic plan. Return only valid JSON."""
    
    def _parse_and_validate_json(
        self,
        response_text: str,
        expected_keys: Optional[List[str]] = None,
        expected_structure: Optional[str] = None  # "dict" or "list"
    ) -> Any:
        """Parse JSON from response with validation and error recovery"""
        json_data = None
        
        # Method 1: Try to find JSON object/array in response
        json_match = re.search(r'\{.*\}|\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                json_data = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Method 2: Try to parse entire response
        if not json_data:
            try:
                json_data = json.loads(response_text)
            except json.JSONDecodeError:
                pass
        
        # Method 3: Try to fix common JSON errors
        if not json_data:
            try:
                # Fix trailing commas
                fixed_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
                json_data = json.loads(fixed_text)
            except json.JSONDecodeError:
                pass
        
        # Method 4: Try to extract JSON from markdown code blocks
        if not json_data:
            code_block_match = re.search(r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```', response_text, re.DOTALL)
            if code_block_match:
                try:
                    json_data = json.loads(code_block_match.group(1))
                except json.JSONDecodeError:
                    pass
        
        # Validate structure
        if expected_structure == "list":
            if not isinstance(json_data, list):
                json_data = []
        elif expected_structure == "dict":
            if not isinstance(json_data, dict):
                json_data = {}
        
        # Validate required keys for dict
        if isinstance(json_data, dict) and expected_keys:
            for key in expected_keys:
                if key not in json_data:
                    json_data[key] = None  # Set default value
        
        return json_data if json_data is not None else ({} if expected_structure == "dict" else [])
    
    def _parse_json_from_response(self, response_text: str) -> Any:
        """Parse JSON from LLM response (legacy method, use _parse_and_validate_json instead)"""
        return self._parse_and_validate_json(response_text)
    
    async def _create_plan_approval_request(self, plan: Plan, risks: Dict[str, Any]):
        """Create an approval request for a newly created plan"""
        from app.services.approval_service import ApprovalService
        from app.services.adaptive_approval_service import AdaptiveApprovalService
        from app.models.task import Task, TaskStatus
        
        approval_service = ApprovalService(self.db)
        adaptive_approval = AdaptiveApprovalService(self.db)
        
        # Get the task associated with this plan
        task = self.db.query(Task).filter(Task.id == plan.task_id).first()
        
        # Detect critical steps that require mandatory approval
        steps = plan.steps if isinstance(plan.steps, list) else []
        critical_info = adaptive_approval.detect_critical_steps(
            steps=steps,
            task_description=plan.goal
        )
        
        # Check if approval is actually required using adaptive logic
        # Try to get agent_id from plan context if available
        agent_id = None
        agent_metadata = getattr(plan, 'agent_metadata', None) or (plan.strategy if isinstance(plan.strategy, dict) else None)
        if agent_metadata and isinstance(agent_metadata, dict):
            agent_id_str = agent_metadata.get("agent_id")
            if agent_id_str:
                try:
                    from uuid import UUID
                    agent_id = UUID(agent_id_str)
                except (ValueError, TypeError):
                    pass
        
        # Get task autonomy level if task exists
        task_autonomy_level = None
        if task_id:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if task:
                task_autonomy_level = task.autonomy_level
        
        # Use adaptive approval service to determine if approval is needed
        requires_approval, decision_metadata = adaptive_approval.should_require_approval(
            plan=plan,
            agent_id=agent_id,
            task_risk_level=risks.get("overall_risk"),
            task_autonomy_level=task_autonomy_level
        )
        
        # If critical steps detected, mandatory approval is required
        if critical_info["requires_mandatory_approval"]:
            requires_approval = True
            decision_metadata["reason"] = "critical_steps_detected"
            decision_metadata["critical_types"] = critical_info["critical_types"]
            logger = self._get_logger()
            if logger:
                logger.info(
                    f"Plan {plan.id} requires mandatory approval due to critical steps",
                    extra={
                        "plan_id": str(plan.id),
                        "critical_types": critical_info["critical_types"],
                        "critical_steps_count": len(critical_info["critical_steps"])
                    }
                )
        
        # Update task status to PENDING_APPROVAL if approval is required
        if requires_approval and task:
            if task.status == TaskStatus.DRAFT:
                # Use TaskLifecycleManager for status transition
                from app.services.task_lifecycle_manager import TaskRole
                self.task_lifecycle_manager.transition(
                    task=task,
                    new_status=TaskStatus.PENDING_APPROVAL,
                    role=TaskRole.PLANNER,
                    reason="Plan created, requires approval",
                    metadata={"plan_id": str(plan.id)}
                )
                self.db.commit()
                self.db.refresh(task)
                logger = self._get_logger()
                if logger:
                    logger.info(
                        f"Task {task.id} transitioned from DRAFT to PENDING_APPROVAL",
                        extra={
                            "task_id": str(task.id),
                            "plan_id": str(plan.id),
                            "reason": decision_metadata.get("reason", "approval_required")
                        }
                    )
        
        # If approval is not required, skip creating approval request
        if not requires_approval:
            logger = self._get_logger()
            if logger:
                logger.info(
                    f"Plan {plan.id} does not require approval based on adaptive logic",
                    extra={
                        "plan_id": str(plan.id),
                        "agent_id": str(agent_id) if agent_id else None,
                        "decision_metadata": decision_metadata
                    }
                )
            # Mark plan as auto-approved
            plan.status = "approved"
            plan.approved_at = datetime.now(timezone.utc)
            # Also update task status if it's in DRAFT
            if task and task.status == TaskStatus.DRAFT:
                # Use TaskLifecycleManager for status transition
                from app.services.task_lifecycle_manager import TaskRole
                self.task_lifecycle_manager.transition(
                    task=task,
                    new_status=TaskStatus.APPROVED,
                    role=TaskRole.SYSTEM,
                    reason="Auto-approved: low risk, high trust",
                    metadata={"plan_id": str(plan.id), "auto_approved": True}
                )
                self.db.commit()
                self.db.refresh(task)
            self.db.commit()
            self.db.refresh(plan)
            return None
        
        # Prepare request data
        request_data = {
            "plan_id": str(plan.id),
            "goal": plan.goal,
            "version": plan.version,
            "total_steps": len(plan.steps) if isinstance(plan.steps, list) else 0,
            "estimated_duration": plan.estimated_duration,
            "adaptive_decision": decision_metadata  # Include decision metadata
        }
        
        # Prepare risk assessment - ensure overall_risk is a float
        overall_risk = risks.get("overall_risk", 0.5)
        if isinstance(overall_risk, str):
            try:
                overall_risk = float(overall_risk)
            except (ValueError, TypeError):
                overall_risk = 0.5
        elif not isinstance(overall_risk, (int, float)):
            overall_risk = 0.5
        
        risk_assessment = {
            "rating": overall_risk,
            "risks": risks.get("identified_risks", []),
            "recommendations": risks.get("mitigation_strategies", []),
            "adaptive_metadata": decision_metadata
        }
        
        # Create recommendation with adaptive information
        recommendation = f"План '{plan.goal[:100]}...' требует утверждения. "
        if overall_risk > 0.7:
            recommendation += "⚠️ Высокий уровень риска."
        elif overall_risk > 0.4:
            recommendation += "⚠️ Средний уровень риска."
        else:
            recommendation += "✅ Низкий уровень риска."
        
        # Add trust score info if available
        if decision_metadata.get("agent_trust_score") is not None:
            trust_score = decision_metadata["agent_trust_score"]
            recommendation += f" Trust score агента: {trust_score:.2f}."
        
        # Create approval request
        approval_request = approval_service.create_approval_request(
            request_type=ApprovalRequestType.PLAN_APPROVAL,
            request_data=request_data,
            plan_id=plan.id,
            task_id=plan.task_id,
            risk_assessment=risk_assessment,
            recommendation=recommendation,
            timeout_hours=48  # Plans can wait longer
        )
        
        return approval_request
    
    def get_plan(self, plan_id: UUID) -> Optional[Plan]:
        """Get plan by ID"""
        return self.db.query(Plan).filter(Plan.id == plan_id).first()
    
    def get_plans_for_task(self, task_id: UUID) -> List[Plan]:
        """Get all plans for a task"""
        return self.db.query(Plan).filter(Plan.task_id == task_id).order_by(
            Plan.version.desc()
        ).all()
    
    def approve_plan(self, plan_id: UUID) -> Plan:
        """Approve a plan"""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        plan.status = "approved"  # Use lowercase string to match DB constraint
        plan.approved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(plan)
        
        return plan
    
    def start_execution(self, plan_id: UUID) -> Plan:
        """Start plan execution"""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        if plan.status != "approved":  # Use lowercase string
            raise ValueError(f"Plan must be approved before execution")
        
        plan.status = "executing"  # Use lowercase string to match DB constraint
        plan.current_step = 0
        self.db.commit()
        self.db.refresh(plan)
        
        return plan
    
    async def replan(
        self,
        plan_id: UUID,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """Create a new version of the plan based on feedback"""
        original_plan = self.get_plan(plan_id)
        if not original_plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Get task
        task = self.db.query(Task).filter(Task.id == original_plan.task_id).first()
        if not task:
            raise ValueError(f"Task {original_plan.task_id} not found")
        
        # Search for similar situations in memory to learn from past replanning
        similar_replanning = None
        if context and context.get("error"):
            try:
                from app.services.memory_service import MemoryService
                memory_service = MemoryService(self.db)
                
                # Search for similar error situations
                error_message = context.get("error", {}).get("message", "")
                if error_message:
                    similar_memories = memory_service.search_memories(
                        query=f"error: {error_message[:100]} replanning",
                        memory_types=["episodic"],
                        limit=3
                    )
                    
                    if similar_memories:
                        similar_replanning = {
                            "count": len(similar_memories),
                            "examples": [
                                {
                                    "plan_id": m.get("metadata", {}).get("plan_id"),
                                    "solution": m.get("content", {}).get("solution"),
                                    "success": m.get("content", {}).get("status") == "completed"
                                }
                                for m in similar_memories[:2]
                            ]
                        }
            except Exception as e:
                logger = self._get_logger()
                if logger:
                    logger.debug(f"Could not search for similar replanning situations: {e}")
        
        # Prepare enhanced context with memory insights
        enhanced_context = {
            **(context or {}),
            "previous_plan": {
                "version": original_plan.version,
                "steps": original_plan.steps,
                "goal": original_plan.goal,
                "strategy": original_plan.strategy,
                "reason_for_replan": reason
            }
        }
        
        if similar_replanning:
            enhanced_context["similar_replanning"] = similar_replanning
        
        # Create new plan version using PlannerAgent (via generate_plan)
        new_plan = await self.generate_plan(
            task_description=task.description,
            task_id=task.id,
            context=enhanced_context
        )
        
        # Increment version
        new_plan.version = original_plan.version + 1
        
        self.db.commit()
        self.db.refresh(new_plan)
        
        # Transition task to PENDING_APPROVAL for the new plan (as per plan requirements)
        # The new plan needs approval before execution
        try:
            task = self.db.query(Task).filter(Task.id == original_plan.task_id).first()
            if task:
                # Use TaskLifecycleManager to transition task status
                # New plan requires approval, so task should be in PENDING_APPROVAL
                if task.status != TaskStatus.PENDING_APPROVAL:
                    # Only transition if not already in PENDING_APPROVAL
                    # Check if transition is allowed
                    if self.task_lifecycle_manager.can_transition(
                        task=task,
                        new_status=TaskStatus.PENDING_APPROVAL,
                        role=TaskRole.PLANNER
                    ):
                        self.task_lifecycle_manager.transition(
                            task=task,
                            new_status=TaskStatus.PENDING_APPROVAL,
                            role=TaskRole.PLANNER,
                            reason=f"New plan created after replanning (version {new_plan.version})",
                            metadata={
                                "original_plan_id": str(original_plan.id),
                                "new_plan_id": str(new_plan.id),
                                "replan_reason": reason
                            }
                        )
                        logger = self._get_logger()
                        if logger:
                            logger.info(
                                f"Task {task.id} transitioned to PENDING_APPROVAL after replanning",
                                extra={
                                    "task_id": str(task.id),
                                    "original_plan_id": str(original_plan.id),
                                    "new_plan_id": str(new_plan.id),
                                    "new_version": new_plan.version
                                }
                            )
        except Exception as e:
            logger = self._get_logger()
            if logger:
                logger.warning(
                    f"Failed to transition task to PENDING_APPROVAL after replanning: {e}",
                    exc_info=True
                )
            # Continue even if transition fails
        
        # Save replan to episodic memory
        await self._save_plan_to_episodic_memory(
            new_plan,
            original_plan.task_id,
            "plan_replanned",
            context={
                "original_plan_id": str(original_plan.id),
                "original_version": original_plan.version,
                "reason": reason,
                **(context or {})
            }
        )
        
        # Update Digital Twin context with replanning history
        task = self.db.query(Task).filter(Task.id == original_plan.task_id).first()
        if task:
            task_context = task.get_context()
            
            # Initialize replanning_history if not exists
            if "planning_decisions" not in task_context:
                task_context["planning_decisions"] = {}
            if "replanning_history" not in task_context["planning_decisions"]:
                task_context["planning_decisions"]["replanning_history"] = []
            
            # Add replanning entry
            replanning_entry = {
                "from_version": original_plan.version,
                "to_version": new_plan.version,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "original_plan_id": str(original_plan.id),
                "new_plan_id": str(new_plan.id),
                "changes": {
                    "steps_before": len(original_plan.steps) if original_plan.steps else 0,
                    "steps_after": len(new_plan.steps) if new_plan.steps else 0
                }
            }
            
            task_context["planning_decisions"]["replanning_history"].append(replanning_entry)
            task_context["plan"] = {
                "plan_id": str(new_plan.id),
                "version": new_plan.version,
                "goal": new_plan.goal,
                "strategy": new_plan.strategy,
                "steps_count": len(new_plan.steps) if new_plan.steps else 0,
                "status": new_plan.status,
                "created_at": new_plan.created_at.isoformat() if new_plan.created_at else None
            }
            
            task.update_context(task_context, merge=False)
            self.db.commit()
        
        # Update working memory with new plan
        await self._save_todo_to_working_memory(original_plan.task_id, new_plan)
        
        return new_plan
    
    async def auto_replan_on_error(
        self,
        plan_id: UUID,
        error_message: str,
        error_severity: Optional[str] = None,
        error_category: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        failed_at_step: Optional[int] = None
    ) -> Optional[Plan]:
        """
        Automatically replan on error with error classification context
        
        This method is called automatically by ExecutionService when a critical
        or high severity error is detected during plan execution.
        
        Args:
            plan_id: ID of the failed plan
            error_message: Error message
            error_severity: Error severity (CRITICAL, HIGH, etc.)
            error_category: Error category (ENVIRONMENT, DEPENDENCY, etc.)
            execution_context: Execution context at time of failure
            failed_at_step: Step index where failure occurred
            
        Returns:
            New plan if replanning was successful, None otherwise
        """
        from app.core.execution_error_types import ExecutionErrorDetector, ErrorSeverity
        
        logger = self._get_logger()
        
        try:
            # Classify error if not already classified
            if not error_severity:
                error_detector = ExecutionErrorDetector()
                classified_error = error_detector.detect_error(
                    error_message,
                    context={
                        "plan_id": str(plan_id),
                        "failed_at_step": failed_at_step,
                        **(execution_context or {})
                    }
                )
                error_severity = classified_error.severity.value
                error_category = classified_error.category.value
            
            logger.info(
                f"Auto-replanning plan {plan_id} due to {error_severity} error: {error_category}",
                extra={
                    "plan_id": str(plan_id),
                    "error_severity": error_severity,
                    "error_category": error_category,
                    "failed_at_step": failed_at_step,
                    "error_message": error_message[:200]
                }
            )
            
            # Prepare replanning context with error information
            replan_context = {
                "auto_replan": True,
                "error": {
                    "message": error_message,
                    "severity": error_severity,
                    "category": error_category,
                    "failed_at_step": failed_at_step
                },
                **(execution_context or {})
            }
            
            # Create reason for replanning
            reason = f"Автоматическое перепланирование из-за ошибки ({error_severity}/{error_category}): {error_message[:100]}"
            
            # Call replan with error context
            new_plan = await self.replan(
                plan_id=plan_id,
                reason=reason,
                context=replan_context
            )
            
            logger.info(
                f"Auto-replanning successful: created plan {new_plan.id} (version {new_plan.version})",
                extra={
                    "original_plan_id": str(plan_id),
                    "new_plan_id": str(new_plan.id),
                    "new_version": new_plan.version,
                    "error_severity": error_severity,
                    "error_category": error_category
                }
            )
            
            return new_plan
            
        except Exception as e:
            logger.error(
                f"Auto-replanning failed for plan {plan_id}: {e}",
                exc_info=True,
                extra={
                    "plan_id": str(plan_id),
                    "error_message": error_message,
                    "error_severity": error_severity,
                    "error_category": error_category
                }
            )
            return None
    
    async def _save_todo_to_working_memory(
        self,
        task_id: UUID,
        plan: Plan
    ) -> None:
        """
        Save active ToDo list to working memory
        
        Args:
            task_id: Task ID
            plan: Current plan
        """
        try:
            from app.services.memory_service import MemoryService
            from app.models.task import Task
            from app.models.agent import Agent
            
            # Get task to find agent_id if available
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return
            
            # For working memory, we need an agent_id
            # Try to get from plan metadata or use a system agent
            agent_id = None
            agent_metadata = getattr(plan, 'agent_metadata', None) or (plan.strategy if isinstance(plan.strategy, dict) else None)
            if agent_metadata and isinstance(agent_metadata, dict):
                agent_id_str = agent_metadata.get("agent_id")
                if agent_id_str:
                    try:
                        agent_id = UUID(agent_id_str)
                    except (ValueError, TypeError):
                        pass
            
            # If no agent_id, we can't save to working memory (requires agent)
            if not agent_id:
                # Skip working memory save if no agent_id
                return
            
            memory_service = MemoryService(self.db)
            
            # Get steps as ToDo list
            steps = plan.steps if isinstance(plan.steps, list) else []
            todo_list = [
                {
                    "step_id": step.get("step_id", f"step_{i}"),
                    "description": step.get("description", ""),
                    "status": "pending",
                    "completed": False
                }
                for i, step in enumerate(steps)
            ]
            
            # Save to working memory using task_id as session
            context_key = f"task_{task_id}_todo"
            memory_service.save_context(
                agent_id=agent_id,
                context_key=context_key,
                content={
                    "task_id": str(task_id),
                    "plan_id": str(plan.id),
                    "plan_version": plan.version,
                    "todo_list": todo_list,
                    "total_steps": len(todo_list),
                    "completed_steps": 0,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                },
                session_id=str(task_id),
                ttl_seconds=86400 * 7  # 7 days
            )
            
            # Logging is optional - skip if logger not available
            try:
                from app.core.logging_config import LoggingConfig
                logger = LoggingConfig.get_logger(__name__)
                logger.debug(
                    f"Saved ToDo list to working memory for task {task_id}",
                    extra={"task_id": str(task_id), "plan_id": str(plan.id), "steps_count": len(todo_list)}
                )
            except:
                pass
            
        except Exception as e:
            # Logging is optional - skip if logger not available
            try:
                from app.core.logging_config import LoggingConfig
                logger = LoggingConfig.get_logger(__name__)
                logger.warning(f"Error saving ToDo to working memory: {e}", exc_info=True)
            except:
                pass
    
    async def _save_plan_to_episodic_memory(
        self,
        plan: Plan,
        task_id: UUID,
        event_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save plan change to episodic memory (history of plan changes)
        
        Args:
            plan: Plan to save
            task_id: Task ID
            event_type: Type of event (plan_created, plan_updated, plan_replanned, etc.)
            context: Additional context
        """
        try:
            from app.services.memory_service import MemoryService
            from app.models.task import Task
            from app.models.agent_memory import MemoryType
            
            # Get task
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return
            
            # Get agent_id from plan metadata if available
            agent_id = None
            agent_metadata = getattr(plan, 'agent_metadata', None) or (plan.strategy if isinstance(plan.strategy, dict) else None)
            if agent_metadata and isinstance(agent_metadata, dict):
                agent_id_str = agent_metadata.get("agent_id")
                if agent_id_str:
                    try:
                        agent_id = UUID(agent_id_str)
                    except (ValueError, TypeError):
                        pass
            
            # If no agent_id, we can't save to episodic memory (requires agent)
            if not agent_id:
                # Skip episodic memory save if no agent_id
                return
            
            memory_service = MemoryService(self.db)
            
            # Save plan snapshot to episodic memory
            episodic_content = {
                "plan_id": str(plan.id),
                "plan_version": plan.version,
                "task_id": str(task_id),
                "task_description": task.description,
                "event_type": event_type,
                "plan_goal": plan.goal,
                "plan_steps": plan.steps if isinstance(plan.steps, list) else [],
                "plan_status": plan.status,
                "strategy": plan.strategy,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(context or {})
            }
            
            memory_service.save_memory(
                agent_id=agent_id,
                memory_type=MemoryType.EXPERIENCE.value,  # Use EXPERIENCE for episodic memory
                content=episodic_content,
                summary=f"Plan {event_type}: {plan.goal[:100]}",
                importance=0.7,  # High importance for plan history
                tags=["plan", "episodic", event_type, f"task_{task_id}"],
                source=f"task_{task_id}"
            )
            
            # Logging is optional - skip if logger not available
            try:
                from app.core.logging_config import LoggingConfig
                logger = LoggingConfig.get_logger(__name__)
                logger.debug(
                    f"Saved plan to episodic memory",
                    extra={
                        "plan_id": str(plan.id),
                        "task_id": str(task_id),
                        "event_type": event_type,
                        "agent_id": str(agent_id)
                    }
                )
            except:
                pass
            
        except Exception as e:
            # Logging is optional - skip if logger not available
            try:
                from app.core.logging_config import LoggingConfig
                logger = LoggingConfig.get_logger(__name__)
                logger.warning(f"Error saving plan to episodic memory: {e}", exc_info=True)
            except:
                pass
    
    async def _apply_procedural_memory_patterns(
        self,
        task_description: str,
        agent_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Apply procedural memory patterns (successful plan templates) for similar tasks
        
        Args:
            task_description: Task description
            agent_id: Optional agent ID
            
        Returns:
            Pattern data if found, None otherwise
        """
        try:
            from app.services.memory_service import MemoryService
            from app.services.meta_learning_service import MetaLearningService
            from app.models.agent_memory import MemoryType
            
            if not agent_id:
                return None
            
            memory_service = MemoryService(self.db)
            meta_learning = MetaLearningService(self.db)
            
            # Search for similar successful plan patterns
            similar_patterns = memory_service.search_memories(
                agent_id=agent_id,
                query_text=task_description,
                memory_type=MemoryType.PATTERN.value,
                limit=5
            )
            
            # Also get patterns from MetaLearningService (if method exists)
            learning_patterns = []
            try:
                # Try different method names that might exist
                if hasattr(meta_learning, 'get_learning_patterns'):
                    learning_patterns = meta_learning.get_learning_patterns(
                        agent_id=agent_id,
                        pattern_type="strategy",
                        limit=5
                    )
                elif hasattr(meta_learning, 'get_patterns_for_task'):
                    # Use get_patterns_for_task if available
                    from app.models.learning_pattern import PatternType
                    patterns = meta_learning.get_patterns_for_task(
                        task_category=task_description[:50],  # Use first 50 chars as category
                        pattern_type=PatternType.STRATEGY
                    )
                    learning_patterns = [p.to_dict() if hasattr(p, 'to_dict') else p for p in patterns[:5]]
            except (AttributeError, Exception) as e:
                logger.debug(f"Could not get learning patterns from MetaLearningService: {e}")
                learning_patterns = []
            
            # Combine and rank patterns
            all_patterns = []
            
            # Add memory patterns
            for pattern in similar_patterns:
                if pattern.content and pattern.content.get("success_rate", 0) > 0.7:
                    all_patterns.append({
                        "source": "memory",
                        "pattern": pattern.content,
                        "importance": pattern.importance,
                        "success_rate": pattern.content.get("success_rate", 0)
                    })
            
            # Add learning patterns
            for pattern in learning_patterns:
                if pattern.success_rate > 0.7:
                    all_patterns.append({
                        "source": "meta_learning",
                        "pattern": pattern.pattern_data,
                        "importance": 0.8,  # High importance for learned patterns
                        "success_rate": pattern.success_rate
                    })
            
            # Sort by success rate and importance
            all_patterns.sort(key=lambda x: x["success_rate"] * x["importance"], reverse=True)
            
            # Return best matching pattern
            if all_patterns:
                best_pattern = all_patterns[0]
                logger = self._get_logger()
                if logger:
                    logger.info(
                        f"Found procedural memory pattern for task",
                        extra={
                            "agent_id": str(agent_id),
                            "pattern_source": best_pattern["source"],
                            "success_rate": best_pattern["success_rate"]
                        }
                    )
                return best_pattern["pattern"]
            
            return None
            
        except Exception as e:
            logger = self._get_logger()
            if logger:
                logger.warning(f"Error applying procedural memory patterns: {e}", exc_info=True)
            return None
    
    async def _adapt_template_to_task(
        self,
        template,
        task_description: str,
        strategy: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Adapt a plan template to a specific task using LLM.
        
        This method uses LLM to intelligently adapt template steps to the specific task,
        replacing placeholders and adjusting steps based on task requirements.
        
        Args:
            template: PlanTemplate object to adapt
            task_description: Description of the current task
            strategy: Strategy dict for the task
            context: Additional context
            
        Returns:
            List of adapted steps
        """
        template_steps = template.steps_template if isinstance(template.steps_template, list) else []
        
        if not template_steps:
            # If template has no steps, fall back to standard decomposition
            return await self._decompose_task(task_description, strategy, context)
        
        # Use LLM to adapt the template steps to the specific task
        try:
            from app.core.model_selector import ModelSelector
            
            model_selector = ModelSelector(self.db)
            planning_model = model_selector.get_planning_model()
            
            if not planning_model:
                # Fallback to basic adaptation if no model available
                return self._basic_template_adaptation(template_steps, task_description)
            
            server = model_selector.get_server_for_model(planning_model)
            if not server:
                return self._basic_template_adaptation(template_steps, task_description)
            
            # Build prompt for LLM adaptation
            template_steps_json = json.dumps(template_steps, indent=2, ensure_ascii=False)
            strategy_json = json.dumps(strategy, indent=2, ensure_ascii=False)
            
            system_prompt = """You are a planning assistant. Your task is to adapt a plan template to a specific task.
Replace placeholders (like <TASK_DESCRIPTION>, <GOAL>, <MODULE_NAME>, etc.) with concrete details from the task.
Adjust step descriptions to match the specific task requirements while maintaining the overall structure.
Return only a valid JSON array of steps, maintaining the same structure as the template."""
            
            user_prompt = f"""Task: {task_description}

Strategy:
{strategy_json}

Template Steps (to adapt):
{template_steps_json}

Adapt these template steps to the specific task. Replace all placeholders with concrete details.
Maintain the step structure but make descriptions specific to the task.
Return only a valid JSON array of adapted steps."""
            
            # Call LLM
            from app.core.ollama_client import OllamaClient, TaskType
            ollama_client = OllamaClient()
            
            response = ollama_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                task_type=TaskType.PLANNING,
                model=planning_model.model_name,
                base_url=server.base_url,
                temperature=0.3,  # Lower temperature for more consistent adaptation
                response_format={"type": "json_object"}
            )
            
            if response and response.get("response"):
                # Parse adapted steps from LLM response
                # LLM might return {"steps": [...]} or just [...]
                response_data = self._parse_json_from_response(response["response"])
                
                if isinstance(response_data, dict) and "steps" in response_data:
                    adapted_steps = response_data["steps"]
                elif isinstance(response_data, list):
                    adapted_steps = response_data
                else:
                    adapted_steps = None
                
                if isinstance(adapted_steps, list) and len(adapted_steps) > 0:
                    # Ensure all steps have required fields
                    for i, step in enumerate(adapted_steps):
                        if not isinstance(step, dict):
                            continue
                        step.setdefault("step", i + 1)
                        step.setdefault("type", "code")
                        step.setdefault("estimated_time", 600)
                    
                    logger = self._get_logger()
                    if logger:
                        logger.info(
                            f"Successfully adapted template {template.name} to task using LLM",
                            extra={
                                "template_id": str(template.id),
                                "original_steps_count": len(template_steps),
                                "adapted_steps_count": len(adapted_steps)
                            }
                        )
                    
                    return adapted_steps
            
            # If LLM adaptation failed, fall back to basic adaptation
            logger = self._get_logger()
            if logger:
                logger.warning("LLM template adaptation failed, using basic adaptation")
            return self._basic_template_adaptation(template_steps, task_description)
            
        except Exception as e:
            logger = self._get_logger()
            if logger:
                logger.warning(f"Error in LLM template adaptation: {e}", exc_info=True)
            # Fallback to basic adaptation
            return self._basic_template_adaptation(template_steps, task_description)
    
    def _basic_template_adaptation(
        self,
        template_steps: List[Dict[str, Any]],
        task_description: str
    ) -> List[Dict[str, Any]]:
        """
        Basic template adaptation without LLM (fallback method).
        
        Args:
            template_steps: Template steps to adapt
            task_description: Task description
            
        Returns:
            List of adapted steps
        """
        adapted_steps = []
        for i, step in enumerate(template_steps):
            adapted_step = step.copy() if isinstance(step, dict) else {}
            
            # Replace common placeholders
            if isinstance(adapted_step.get("description"), str):
                description = adapted_step["description"]
                # Replace generic placeholders with task-specific details
                description = description.replace("<TASK_DESCRIPTION>", task_description[:100])
                description = description.replace("<GOAL>", task_description[:100])
                adapted_step["description"] = description
            
            # Ensure step has required fields
            adapted_step.setdefault("step", i + 1)
            adapted_step.setdefault("type", "code")
            adapted_step.setdefault("estimated_time", 600)
            
            adapted_steps.append(adapted_step)
        
        return adapted_steps

