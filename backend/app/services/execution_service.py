"""
Execution service for plan execution
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import json
import asyncio

from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.core.ollama_client import OllamaClient
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes
from app.core.metrics import (
    plan_executions_total,
    plan_execution_duration_seconds,
    plan_steps_total,
    plan_step_duration_seconds
)
from app.services.ollama_service import OllamaService
from app.services.checkpoint_service import CheckpointService
from app.services.agent_service import AgentService
from app.services.tool_service import ToolService
from app.services.project_metrics_service import ProjectMetricsService
from app.agents.simple_agent import SimpleAgent
from app.tools.python_tool import PythonTool
from app.core.execution_error_types import (
    ExecutionErrorDetector,
    ExecutionError,
    ErrorSeverity,
    ErrorCategory,
    requires_replanning,
    detect_execution_error
)
from app.core.config import get_settings
import time

logger = LoggingConfig.get_logger(__name__)
settings = get_settings()


class StepExecutor:
    """Executor for individual plan steps"""
    
    def __init__(self, db: Session, metrics_service=None):
        self.db = db
        self.tracer = get_tracer(__name__)
        self.metrics_service = metrics_service  # Может быть None, если не передан
    
    async def execute_step(
        self,
        step: Dict[str, Any],
        plan: Plan,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single plan step
        
        Args:
            step: Step definition from plan
            plan: Plan being executed
            context: Execution context (results from previous steps)
            
        Returns:
            Execution result with status, output, and metadata
        """
        step_id = step.get("step_id", "unknown")
        step_type = step.get("type", "action")
        description = step.get("description", "")
        
        # Start metrics tracking
        step_start_time = time.time()
        
        result = {
            "step_id": step_id,
            "status": "pending",
            "started_at": datetime.utcnow(),
            "output": None,
            "error": None,
            "duration": None
        }
        
        try:
            logger.info(
                "Executing plan step",
                extra={
                    "step_id": step_id,
                    "step_type": step_type,
                    "plan_id": str(plan.id),
                }
            )
            
            # Check if step requires approval
            if step.get("approval_required", False):
                # Create approval request for this step
                from app.services.approval_service import ApprovalService
                from app.models.approval import ApprovalRequestType
                
                approval_service = ApprovalService(self.db)
                approval = approval_service.create_approval_request(
                    request_type=ApprovalRequestType.EXECUTION_STEP,
                    request_data={
                        "plan_id": str(plan.id),
                        "step_id": step_id,
                        "description": description,
                        "step": step
                    },
                    plan_id=plan.id,
                    task_id=plan.task_id,
                    recommendation=f"Шаг '{description[:100]}...' требует утверждения перед выполнением"
                )
                
                result["status"] = "waiting_approval"
                result["approval_id"] = str(approval.id)
                result["message"] = "Ожидает утверждения"
                return result
            
            # Execute based on step type
            if step_type == "action":
                result = await self._execute_action_step(step, plan, context, result)
            elif step_type == "decision":
                result = await self._execute_decision_step(step, plan, context, result)
            elif step_type == "validation":
                result = await self._execute_validation_step(step, plan, context, result)
            else:
                result["status"] = "skipped"
                result["message"] = f"Unknown step type: {step_type}"
            
            result["completed_at"] = datetime.utcnow()
            if result["started_at"]:
                result["duration"] = (result["completed_at"] - result["started_at"]).total_seconds()
            
            # Record step metrics
            step_duration = time.time() - step_start_time
            step_status = result.get("status", "unknown")
            plan_steps_total.labels(
                step_type=step_type,
                status=step_status
            ).inc()
            plan_step_duration_seconds.labels(
                step_type=step_type
            ).observe(step_duration)
            
            # Record project metrics for step execution
            try:
                from datetime import timedelta
                from app.models.project_metric import MetricType, MetricPeriod
                
                now = datetime.utcnow()
                # Round to hour for consistent period boundaries
                period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                period_end = now.replace(minute=0, second=0, microsecond=0)
                
                self.metrics_service.record_metric(
                    metric_type=MetricType.EXECUTION_TIME,
                    metric_name="step_execution_time",
                    value=step_duration,
                    period=MetricPeriod.HOUR,
                    period_start=period_start,
                    period_end=period_end,
                    count=1,
                    min_value=step_duration,
                    max_value=step_duration,
                    sum_value=step_duration,
                    metric_metadata={
                        "step_type": step_type,
                        "status": step_status,
                        "plan_id": str(plan.id)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to record step execution metrics: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(
                "Exception in step execution",
                exc_info=True,
                extra={
                    "step_id": step_id,
                    "step_type": step_type,
                    "plan_id": str(plan.id),
                    "error": str(e),
                }
            )
            
            result["status"] = "failed"
            result["error"] = str(e)
            result["completed_at"] = datetime.utcnow()
            if result["started_at"]:
                result["duration"] = (result["completed_at"] - result["started_at"]).total_seconds()
            
            # Record failed step metrics
            step_duration = time.time() - step_start_time
            plan_steps_total.labels(
                step_type=step_type,
                status="failed"
            ).inc()
            plan_step_duration_seconds.labels(
                step_type=step_type
            ).observe(step_duration)
        
        return result
    
    async def _execute_action_step(
        self,
        step: Dict[str, Any],
        plan: Plan,
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an action step"""
        description = step.get("description", "")
        
        # Check if step specifies a team or agent
        team_id = step.get("team_id")
        agent_id = step.get("agent")
        tool_id = step.get("tool")
        
        # If team is specified, use team coordination to execute the step
        if team_id:
            try:
                return await self._execute_with_team(step, plan, context, result, team_id, tool_id)
            except Exception as e:
                logger.warning(
                    f"Failed to execute step with team {team_id}, falling back to agent/LLM: {e}",
                    extra={
                        "step_id": step.get("step_id"),
                        "team_id": team_id,
                        "error": str(e)
                    }
                )
                # Fall back to agent or LLM execution
        
        # If agent is specified, use agent to execute the step
        if agent_id:
            try:
                return await self._execute_with_agent(step, plan, context, result, agent_id, tool_id)
            except Exception as e:
                logger.warning(
                    f"Failed to execute step with agent {agent_id}, falling back to LLM: {e}",
                    extra={
                        "step_id": step.get("step_id"),
                        "agent_id": agent_id,
                        "error": str(e)
                    }
                )
                # Fall back to LLM execution
        
        # If tool is specified without agent, use tool directly
        if tool_id and not agent_id:
            try:
                return await self._execute_with_tool(step, plan, context, result, tool_id)
            except Exception as e:
                logger.warning(
                    f"Failed to execute step with tool {tool_id}, falling back to LLM: {e}",
                    extra={
                        "step_id": step.get("step_id"),
                        "tool_id": tool_id,
                        "error": str(e)
                    }
                )
                # Fall back to LLM execution
        
        # Default: use LLM to execute the step
        
        # Use ModelSelector for dual-model architecture (code generation model)
        from app.core.model_selector import ModelSelector
        
        model_selector = ModelSelector(self.db)
        execution_model = model_selector.get_code_model()
        
        if not execution_model:
            raise ValueError("No suitable model found for code execution")
        
        # Get server for the model
        server = model_selector.get_server_for_model(execution_model)
        if not server:
            raise ValueError("No server found for code model")
        
        # Create OllamaClient
        ollama_client = OllamaClient()
        
        # Prepare prompt
        context_str = ""
        if context:
            # Convert datetime objects to strings for JSON serialization
            def json_serial(obj):
                """JSON serializer for objects not serializable by default json code"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            try:
                context_str = f"\n\nКонтекст выполнения:\n{json.dumps(context, indent=2, ensure_ascii=False, default=json_serial)}"
            except (TypeError, ValueError) as e:
                # Fallback: convert to string representation
                context_str = f"\n\nКонтекст выполнения:\n{str(context)}"
        
        # Check if step has a function_call (from planning model)
        function_call_data = step.get("function_call")
        if function_call_data:
            # Process function call using FunctionCallProtocol
            from app.core.function_calling import FunctionCallProtocol
            
            # Parse function call
            if isinstance(function_call_data, dict):
                function_call = FunctionCallProtocol.create_function_call(
                    function_name=function_call_data.get("function", ""),
                    parameters=function_call_data.get("parameters", {}),
                    validation_schema=function_call_data.get("validation_schema"),
                    safety_checks=function_call_data.get("safety_checks", True)
                )
            elif isinstance(function_call_data, str):
                # Try to parse from string
                function_call = FunctionCallProtocol.parse_function_call_from_llm(function_call_data)
            else:
                function_call = None
            
            if function_call:
                # Validate function call
                is_valid, issues = FunctionCallProtocol.validate_function_call(function_call)
                
                if not is_valid:
                    result["status"] = "failed"
                    result["error"] = f"Function call validation failed: {', '.join(issues)}"
                    return result
                
                # Execute function call using CodeExecutionSandbox
                if function_call.function == "code_execution_tool":
                    from app.services.code_execution_sandbox import CodeExecutionSandbox
                    
                    sandbox = CodeExecutionSandbox()
                    code = function_call.parameters.get("code", "")
                    language = function_call.parameters.get("language", "python")
                    constraints = {
                        "timeout": function_call.parameters.get("timeout", 30),
                        "memory_limit": function_call.parameters.get("memory_limit", 512)
                    }
                    
                    execution_result = sandbox.execute_code_safely(
                        code=code,
                        language=language,
                        constraints=constraints
                    )
                    
                    # Map sandbox result to execution result
                    result["status"] = "completed" if execution_result["status"] == "success" else "failed"
                    result["output"] = execution_result.get("output", "")
                    if execution_result.get("error"):
                        result["error"] = execution_result["error"]
                    result["metadata"] = {
                        "execution_method": "code_execution_sandbox",
                        "function": function_call.function,
                        "language": language,
                        "return_code": execution_result.get("return_code")
                    }
                    
                    logger.info(
                        f"Executed function call '{function_call.function}' via sandbox",
                        extra={
                            "function": function_call.function,
                            "status": result["status"],
                            "language": language
                        }
                    )
                    
                    return result
                else:
                    # Other function types - store for later execution
                    result["function_call"] = function_call.to_dict()
                    result["metadata"] = {
                        "execution_method": "function_call",
                        "function": function_call.function,
                        "validation_passed": True
                    }
                    result["status"] = "pending_function_call"
                    result["message"] = f"Function call '{function_call.function}' validated but execution not yet implemented"
                    return result
        
        # Fallback to LLM-based execution if no function call
        system_prompt = """You are an execution engine for task plans.
Execute the given step and return the result in JSON format:
{
    "status": "completed|failed",
    "output": "result of execution",
    "metadata": {}
}"""
        
        user_prompt = f"""Выполни следующий шаг плана:

{description}{context_str}

Верни результат выполнения в формате JSON."""
        
        # Execute with timeout - использовать глобальные ограничения (стопоры)
        # Использовать таймаут из шага, если указан, иначе из конфигурации
        timeout = step.get("timeout", settings.execution_timeout_seconds)
        try:
            _coro = ollama_client.generate(
                prompt=user_prompt,
                server_url=server.get_api_url(),
                model=execution_model.model_name or execution_model.name,
                system_prompt=system_prompt,
                task_type="code_generation"
            )
            response = await asyncio.wait_for(_coro, timeout=float(timeout))
            
            # Parse response - OllamaResponse has .response attribute
            response_text = response.response if hasattr(response, "response") else str(response)
            
            # Try to extract JSON from response
            try:
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    step_result = json.loads(json_match.group())
                    result["status"] = step_result.get("status", "completed")
                    result["output"] = step_result.get("output", response_text)
                    result["metadata"] = step_result.get("metadata", {})
                else:
                    result["status"] = "completed"
                    result["output"] = response_text
            except json.JSONDecodeError:
                result["status"] = "completed"
                result["output"] = response_text
            
        except asyncio.TimeoutError:
            result["status"] = "failed"
            result["error"] = f"Step execution timeout after {timeout} seconds"
        
        return result
    
    async def _execute_with_agent(
        self,
        step: Dict[str, Any],
        plan: Plan,
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any],
        agent_id: str,
        tool_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute step using an agent, optionally with a tool
        
        Args:
            step: Step definition
            plan: Plan being executed
            context: Execution context
            result: Result dictionary to update
            agent_id: Agent ID to use
            tool_id: Optional tool ID to use
            
        Returns:
            Updated result dictionary
        """
        from uuid import UUID
        
        try:
            agent_uuid = UUID(agent_id) if isinstance(agent_id, str) else agent_id
        except (ValueError, TypeError):
            result["status"] = "failed"
            result["error"] = f"Invalid agent_id: {agent_id}"
            return result
        
        agent_service = AgentService(self.db)
        agent_data = agent_service.get_agent(agent_uuid)
        
        if not agent_data:
            result["status"] = "failed"
            result["error"] = f"Agent {agent_id} not found"
            return result
        
        if agent_data.status != "active":
            result["status"] = "failed"
            result["error"] = f"Agent {agent_data.name} is not active (status: {agent_data.status})"
            return result
        
        # Create agent instance
        # BaseAgent создает tool_service сам, не нужно передавать
        agent = SimpleAgent(
            agent_id=agent_uuid,
            agent_service=agent_service,
            db_session=self.db  # Передаем db_session для создания tool_service внутри BaseAgent
        )
        
        # Prepare task description
        task_description = step.get("description", "")
        if context:
            # Add context to task description
            context_str = "\n\nContext from previous steps:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
            task_description = f"{task_description}{context_str}"
        
        # Prepare inputs from step
        step_inputs = step.get("inputs", {})
        
        # Execute with agent
        if tool_id:
            # Use specific tool
            try:
                tool_uuid = UUID(tool_id) if isinstance(tool_id, str) else tool_id
                # agent уже имеет tool_service через BaseAgent
                tool_data = agent.tool_service.get_tool(tool_uuid)
                
                if not tool_data:
                    result["status"] = "failed"
                    result["error"] = f"Tool {tool_id} not found"
                    return result
                
                # Execute with tool
                agent_result = await agent.execute(
                    task_description=task_description,
                    context=context,
                    tool_name=tool_data.name,
                    tool_params={**step_inputs, **step.get("tool_params", {})}
                )
            except Exception as e:
                logger.error(
                    f"Error executing step with agent and tool: {e}",
                    exc_info=True,
                    extra={
                        "agent_id": agent_id,
                        "tool_id": tool_id,
                        "step_id": step.get("step_id")
                    }
                )
                result["status"] = "failed"
                result["error"] = f"Tool execution error: {str(e)}"
                return result
        else:
            # Execute with agent only (may use tools automatically)
            use_tools = step.get("use_tools", False)
            agent_result = await agent.execute(
                task_description=task_description,
                context=context,
                use_tools=use_tools,
                **step_inputs
            )
        
        # Update result
        if agent_result["status"] == "success":
            result["status"] = "completed"
            result["output"] = agent_result.get("result")
            result["message"] = agent_result.get("message", "Step completed successfully")
            
            # Add metadata
            if "metadata" in agent_result:
                result["metadata"] = agent_result["metadata"]
                if "tool_used" in agent_result["metadata"]:
                    result["tool_used"] = agent_result["metadata"]["tool_used"]
        else:
            result["status"] = "failed"
            result["error"] = agent_result.get("message", "Agent execution failed")
            result["output"] = agent_result.get("result")
        
        return result
    
    async def _execute_with_tool(
        self,
        step: Dict[str, Any],
        plan: Plan,
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any],
        tool_id: str
    ) -> Dict[str, Any]:
        """
        Execute step using a tool directly (without agent)
        
        Args:
            step: Step definition
            plan: Plan being executed
            context: Execution context
            result: Result dictionary to update
            tool_id: Tool ID to use
            
        Returns:
            Updated result dictionary
        """
        from uuid import UUID
        
        try:
            tool_uuid = UUID(tool_id) if isinstance(tool_id, str) else tool_id
        except (ValueError, TypeError):
            result["status"] = "failed"
            result["error"] = f"Invalid tool_id: {tool_id}"
            return result
        
        tool_service = ToolService(self.db)
        tool_data = tool_service.get_tool(tool_uuid)
        
        if not tool_data:
            result["status"] = "failed"
            result["error"] = f"Tool {tool_id} not found"
            return result
        
        if tool_data.status != "active":
            result["status"] = "failed"
            result["error"] = f"Tool {tool_data.name} is not active (status: {tool_data.status})"
            return result
        
        # Create tool instance
        tool = PythonTool(
            tool_id=tool_uuid,
            tool_service=tool_service
        )
        
        # Prepare inputs
        step_inputs = step.get("inputs", {})
        context_dict = context or {}
        tool_params = {**step_inputs, **step.get("tool_params", {}), **context_dict}
        
        # Execute tool
        tool_result = await tool.execute(**tool_params)
        
        # Update result
        if tool_result["status"] == "success":
            result["status"] = "completed"
            result["output"] = tool_result.get("result")
            result["message"] = tool_result.get("message", "Tool executed successfully")
            result["tool_used"] = tool_data.name
        else:
            result["status"] = "failed"
            result["error"] = tool_result.get("message", "Tool execution failed")
            result["output"] = tool_result.get("result")
        
        return result
    
    async def _execute_decision_step(
        self,
        step: Dict[str, Any],
        plan: Plan,
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a decision step"""
        # Decision steps require LLM reasoning
        # Similar to action but focused on decision making
        
        result["status"] = "completed"
        result["output"] = "Decision made"
        result["message"] = "Decision step executed (placeholder)"
        
        return result
    
    async def _execute_validation_step(
        self,
        step: Dict[str, Any],
        plan: Plan,
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a validation step"""
        # Validation steps check if conditions are met
        
        result["status"] = "completed"
        result["output"] = "Validation passed"
        result["message"] = "Validation step executed (placeholder)"
        
        return result


class ExecutionService:
    """Service for executing plans"""
    
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = ProjectMetricsService(db)
        self.step_executor = StepExecutor(db, metrics_service=self.metrics_service)
        self.checkpoint_service = CheckpointService(db)
        self.error_detector = ExecutionErrorDetector()
    
    def _is_critical_error(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if an error is critical and requires replanning
        
        Args:
            error_message: Error message
            error_type: Optional error type/class name
            context: Optional context (step, plan info, etc.)
            
        Returns:
            True if error is critical and requires replanning
        """
        return self.error_detector.requires_replanning(error_message, error_type, context)
    
    def _classify_error(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionError:
        """
        Classify an execution error
        
        Args:
            error_message: Error message
            error_type: Optional error type/class name
            context: Optional context
            
        Returns:
            Classified ExecutionError
        """
        return self.error_detector.detect_error(error_message, error_type, context)
    
    def _should_trigger_replanning(
        self,
        classified_error: ExecutionError,
        plan: Plan,
        execution_context: Dict[str, Any]
    ) -> bool:
        """
        Determine if automatic replanning should be triggered based on configuration
        
        Args:
            classified_error: Classified execution error
            plan: Current plan
            execution_context: Execution context
            
        Returns:
            True if replanning should be triggered
        """
        # Check if auto-replanning is enabled
        if not settings.enable_auto_replanning:
            return False
        
        # Check severity trigger settings
        severity = classified_error.severity
        if severity == ErrorSeverity.CRITICAL:
            if not settings.auto_replanning_trigger_critical:
                return False
        elif severity == ErrorSeverity.HIGH:
            if not settings.auto_replanning_trigger_high:
                return False
        elif severity == ErrorSeverity.MEDIUM:
            if not settings.auto_replanning_trigger_medium:
                return False
        else:
            # LOW severity errors don't trigger replanning
            return False
        
        # Check replanning attempts limit
        task = self.db.query(Task).filter(Task.id == plan.task_id).first()
        if task:
            context = task.get_context()
            planning_decisions = context.get("planning_decisions", {})
            replanning_history = planning_decisions.get("replanning_history", [])
            
            # Count replanning attempts
            replan_count = len(replanning_history)
            
            if replan_count >= settings.auto_replanning_max_attempts:
                logger.warning(
                    f"Replanning limit reached for task {task.id}: {replan_count} attempts",
                    extra={
                        "task_id": str(task.id),
                        "plan_id": str(plan.id),
                        "replan_count": replan_count,
                        "max_attempts": settings.auto_replanning_max_attempts
                    }
                )
                return False
            
            # Check if human intervention is required
            if replan_count >= settings.auto_replanning_require_human_intervention_after:
                logger.warning(
                    f"Human intervention required after {replan_count} replanning attempts",
                    extra={
                        "task_id": str(task.id),
                        "plan_id": str(plan.id),
                        "replan_count": replan_count
                    }
                )
                # Still allow replanning, but this should trigger notification
                # In future, this could return False to require human approval
        
        return True
    
    async def execute_plan(self, plan_id: UUID) -> Plan:
        """
        Execute a plan step by step
        
        Args:
            plan_id: ID of the plan to execute
            
        Returns:
            Updated plan with execution results
        """
        from app.services.planning_service import PlanningService
        
        planning_service = PlanningService(self.db)
        plan = planning_service.get_plan(plan_id)
        
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        if plan.status != "approved":
            raise ValueError(f"Plan must be approved before execution (current: {plan.status})")
        
        # Start execution and metrics tracking
        plan_start_time = time.time()
        plan.status = "executing"
        plan.current_step = 0
        self.db.commit()
        self.db.refresh(plan)
        
        # ГЛОБАЛЬНОЕ ОГРАНИЧЕНИЕ: Общий таймаут выполнения плана (стопор)
        max_total_time = settings.execution_max_total_timeout_seconds
        
        # Parse steps
        steps = plan.steps
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except:
                steps = []
        
        if not steps:
            plan.status = "failed"
            # Record failed plan metrics
            plan_duration = time.time() - plan_start_time
            plan_executions_total.labels(status="failed").inc()
            plan_execution_duration_seconds.labels(status="failed").observe(plan_duration)
            self.db.commit()
            
            # Automatic replanning on failure
            await self._handle_plan_failure(plan, "Plan has no steps", {})
            return plan
        
        # Execution context (results from previous steps)
        execution_context = {}
        
        # Execute steps in order с проверкой общего таймаута
        for i, step in enumerate(steps):
            # Проверка общего таймаута (стопор)
            elapsed_time = time.time() - plan_start_time
            if elapsed_time > max_total_time:
                logger.warning(
                    f"Plan execution timeout exceeded: {elapsed_time:.1f}s > {max_total_time}s",
                    extra={
                        "plan_id": str(plan.id),
                        "elapsed_time": elapsed_time,
                        "max_total_time": max_total_time,
                        "step_index": i
                    }
                )
                plan.status = "failed"
                plan.current_step = i
                self.db.commit()
                error_msg = f"Plan execution timeout: exceeded {max_total_time}s limit"
                await self._handle_plan_failure(plan, error_msg, execution_context)
                return plan
            # Create checkpoint before each step
            try:
                checkpoint = self.checkpoint_service.create_plan_checkpoint(
                    plan,
                    reason=f"Checkpoint before step {i + 1}: {step.get('description', 'unknown')[:50]}"
                )
                logger.debug(
                    f"Created checkpoint before step {i + 1}",
                    extra={
                        "checkpoint_id": str(checkpoint.id),
                        "plan_id": str(plan.id),
                        "step": i + 1,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to create checkpoint: {e}", exc_info=True)
            
            plan.current_step = i
            self.db.commit()
            self.db.refresh(plan)
            
            # Check dependencies
            dependencies = step.get("dependencies", [])
            if dependencies:
                # Verify all dependencies are completed
                for dep_id in dependencies:
                    if dep_id not in execution_context:
                        plan.status = "failed"
                        plan.current_step = i
                        self.db.commit()
                        error_msg = f"Dependency {dep_id} not found in execution context"
                        
                        # Classify dependency error (should be critical)
                        error_context = {
                            "step_id": step.get("step_id"),
                            "step_index": i,
                            "plan_id": str(plan.id),
                            "dependency_id": dep_id
                        }
                        classified_error = self._classify_error(
                            error_message=error_msg,
                            error_type="DependencyError",
                            context=error_context
                        )
                        
                        # Automatic replanning on critical dependency error
                        if classified_error.requires_replanning:
                            await self._handle_plan_failure(
                                plan,
                                error_msg,
                                execution_context,
                                classified_error=classified_error
                            )
                        raise ValueError(error_msg)
            
            # Execute step
            try:
                step_result = await self.step_executor.execute_step(
                    step=step,
                    plan=plan,
                    context=execution_context
                )
            except Exception as e:
                # Log error and mark step as failed
                logger.error(
                    "Error executing step",
                    exc_info=True,
                    extra={
                        "step_id": step.get('step_id'),
                        "plan_id": str(plan.id),
                        "error": str(e),
                    }
                )
                
                step_result = {
                    "step_id": step.get("step_id"),
                    "status": "failed",
                    "error": str(e),
                    "started_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow()
                }
            
            # Store result in context
            execution_context[step.get("step_id")] = step_result
            
            # Check if step failed
            if step_result.get("status") == "failed":
                error_message = step_result.get('error', 'Unknown error')
                
                # Classify the error
                error_context = {
                    "step_id": step.get("step_id"),
                    "step_index": i,
                    "plan_id": str(plan.id),
                    "plan_version": plan.version,
                    "total_steps": len(steps)
                }
                classified_error = self._classify_error(
                    error_message=error_message,
                    error_type=step_result.get('error_type'),
                    context=error_context
                )
                
                logger.warning(
                    f"Step failed: {classified_error.severity.value} error - {classified_error.category.value}",
                    extra={
                        "plan_id": str(plan.id),
                        "step_index": i,
                        "step_id": step.get('step_id'),
                        "error": error_message,
                        "error_severity": classified_error.severity.value,
                        "error_category": classified_error.category.value,
                        "requires_replanning": classified_error.requires_replanning
                    }
                )
                
                # Try to rollback to last checkpoint
                try:
                    latest_checkpoint = self.checkpoint_service.get_latest_checkpoint("plan", plan.id)
                    if latest_checkpoint:
                        logger.info(
                            f"Rolling back plan {plan.id} to checkpoint {latest_checkpoint.id}",
                            extra={
                                "plan_id": str(plan.id),
                                "checkpoint_id": str(latest_checkpoint.id),
                                "error": error_message,
                            }
                        )
                        self.checkpoint_service.rollback_entity("plan", plan.id, latest_checkpoint.id)
                        plan = self.db.query(Plan).filter(Plan.id == plan.id).first()
                except Exception as rollback_error:
                    logger.error(
                        f"Failed to rollback plan: {rollback_error}",
                        exc_info=True
                    )
                
                plan.status = "failed"
                plan.current_step = i
                self.db.commit()
                
                # Log failure with classification
                logger.error(
                    "Plan failed at step",
                    extra={
                        "plan_id": str(plan.id),
                        "step_index": i,
                        "step_id": step.get('step_id'),
                        "error": error_message,
                        "error_severity": classified_error.severity.value,
                        "error_category": classified_error.category.value,
                        "requires_replanning": classified_error.requires_replanning
                    }
                )
                
                # Check if auto-replanning should be triggered based on configuration
                should_replan = self._should_trigger_replanning(
                    classified_error,
                    plan,
                    execution_context
                )
                
                if should_replan:
                    logger.info(
                        f"Triggering automatic replanning due to {classified_error.severity.value} error",
                        extra={
                            "plan_id": str(plan.id),
                            "error_severity": classified_error.severity.value,
                            "error_category": classified_error.category.value
                        }
                    )
                    await self._handle_plan_failure(
                        plan,
                        error_message,
                        execution_context,
                        classified_error=classified_error
                    )
                else:
                    logger.info(
                        f"Skipping replanning for {classified_error.severity.value} error (disabled or limit reached)",
                        extra={
                            "plan_id": str(plan.id),
                            "error_severity": classified_error.severity.value,
                            "auto_replanning_enabled": settings.enable_auto_replanning
                        }
                    )
                break
            
            # Check if step is waiting for approval
            if step_result.get("status") == "waiting_approval":
                plan.status = "executing"
                plan.current_step = i
                self.db.commit()
                # Plan will continue after approval
                break
            
            # Step completed successfully
            # Continue to next step
        
        # Check if all steps completed
        plan_just_completed = False
        if plan.status == "executing" and plan.current_step >= len(steps) - 1:
            plan.status = "completed"
            plan.current_step = len(steps)
            plan_just_completed = True
        
        # Calculate actual duration
        if plan.created_at:
            plan.actual_duration = int((datetime.utcnow() - plan.created_at).total_seconds())
        
        # Record plan execution metrics
        plan_duration = time.time() - plan_start_time
        plan_status = plan.status
        plan_executions_total.labels(
            status=plan_status
        ).inc()
        plan_execution_duration_seconds.labels(
            status=plan_status
        ).observe(plan_duration)
        
        self.db.commit()
        self.db.refresh(plan)
        
        # Track plan execution using PlanningMetricsService
        try:
            from app.services.planning_metrics_service import PlanningMetricsService
            metrics_service = PlanningMetricsService(self.db)
            
            # Calculate execution time
            execution_time_ms = None
            if plan.actual_duration:
                execution_time_ms = plan.actual_duration * 1000
            
            # Determine success based on plan status
            success = plan.status == "completed"
            
            metrics_service.track_plan_execution_success(
                plan_id=plan.id,
                success=success,
                execution_time_ms=execution_time_ms
            )
        except Exception as e:
            logger.warning(f"Failed to track plan execution: {e}", exc_info=True)
        
        # Extract template from successfully completed plan
        if plan_just_completed and plan.status == "completed":
            try:
                self._extract_template_from_completed_plan(plan)
            except Exception as e:
                logger.warning(f"Failed to extract template from completed plan {plan.id}: {e}", exc_info=True)
        
        # Record project metrics for plan execution
        try:
            from datetime import timedelta
            from app.models.project_metric import MetricType, MetricPeriod
            
            now = datetime.utcnow()
            # Round to hour for consistent period boundaries
            period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
            period_end = now.replace(minute=0, second=0, microsecond=0)
            
            # Record execution time
            if plan.actual_duration:
                self.metrics_service.record_metric(
                    metric_type=MetricType.EXECUTION_TIME,
                    metric_name="plan_execution_time",
                    value=plan.actual_duration,
                    period=MetricPeriod.HOUR,
                    period_start=period_start,
                    period_end=period_end,
                    count=1,
                    min_value=plan.actual_duration,
                    max_value=plan.actual_duration,
                    sum_value=plan.actual_duration,
                    metric_metadata={
                        "plan_id": str(plan.id),
                        "status": plan.status,
                        "steps_count": len(steps) if steps else 0
                    }
                )
            
            # Record success/failure
            success_value = 1.0 if plan.status == "completed" else 0.0
            self.metrics_service.record_metric(
                metric_type=MetricType.TASK_SUCCESS,
                metric_name="plan_execution_success",
                value=success_value,
                period=MetricPeriod.HOUR,
                period_start=period_start,
                period_end=period_end,
                count=1,
                metric_metadata={
                    "plan_id": str(plan.id),
                    "status": plan.status
                }
            )
        except Exception as e:
            logger.warning(f"Failed to record plan execution metrics: {e}", exc_info=True)
        
        return plan
    
    def get_execution_status(self, plan_id: UUID) -> Dict[str, Any]:
        """Get current execution status of a plan"""
        from app.services.planning_service import PlanningService
        
        planning_service = PlanningService(self.db)
        plan = planning_service.get_plan(plan_id)
        
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Parse steps
        steps = plan.steps
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except:
                steps = []
        
        total_steps = len(steps) if steps else 0
        progress = (plan.current_step / total_steps * 100) if total_steps > 0 else 0
        
        return {
            "plan_id": str(plan.id),
            "status": plan.status,
            "current_step": plan.current_step,
            "total_steps": total_steps,
            "progress": progress,
            "estimated_duration": plan.estimated_duration,
            "actual_duration": plan.actual_duration
        }
    
    async def _handle_plan_failure(
        self,
        plan: Plan,
        error_message: str,
        execution_context: Dict[str, Any],
        classified_error: Optional[ExecutionError] = None
    ) -> Optional[Plan]:
        """
        Handle plan failure by analyzing error and automatically replanning
        
        Args:
            plan: Failed plan
            error_message: Error message
            execution_context: Execution context at time of failure
            classified_error: Optional pre-classified error (if not provided, will be classified)
            
        Returns:
            New plan if replanning was successful, None otherwise
        """
        from app.services.planning_service import PlanningService
        from app.services.reflection_service import ReflectionService
        from app.services.memory_service import MemoryService
        from app.models.task import Task, TaskStatus
        
        try:
            # Classify error if not already classified
            if not classified_error:
                error_context = {
                    "plan_id": str(plan.id),
                    "plan_version": plan.version,
                    "current_step": plan.current_step,
                    "total_steps": len(plan.steps) if isinstance(plan.steps, list) else 0
                }
                classified_error = self._classify_error(
                    error_message=error_message,
                    context=error_context
                )
            
            logger.info(
                f"Handling plan failure for plan {plan.id}",
                extra={
                    "plan_id": str(plan.id),
                    "error": error_message,
                    "current_step": plan.current_step,
                    "error_severity": classified_error.severity.value,
                    "error_category": classified_error.category.value,
                    "requires_replanning": classified_error.requires_replanning
                }
            )
            
            # Get task
            task = self.db.query(Task).filter(Task.id == plan.task_id).first()
            if not task:
                logger.warning(f"Task {plan.task_id} not found for failed plan {plan.id}")
                return None
            
            # Update task status to FAILED
            task.status = TaskStatus.FAILED
            self.db.commit()
            
            # Analyze failure using ReflectionService
            reflection_service = ReflectionService(self.db)
            
            # Get agent_id from plan if available
            agent_id = None
            agent_metadata = getattr(plan, 'agent_metadata', None)
            if agent_metadata and isinstance(agent_metadata, dict):
                agent_id_str = agent_metadata.get("agent_id")
                if agent_id_str:
                    try:
                        agent_id = UUID(agent_id_str)
                    except (ValueError, TypeError):
                        pass
            
            # Analyze the failure
            reflection_result = await reflection_service.analyze_failure(
                task_description=task.description,
                error=error_message,
                context={
                    "plan_id": str(plan.id),
                    "plan_version": plan.version,
                    "current_step": plan.current_step,
                    "execution_context": execution_context,
                    "steps": plan.steps if isinstance(plan.steps, list) else []
                },
                agent_id=agent_id
            )
            
            # Generate fix suggestion
            fix_suggestion = await reflection_service.generate_fix(
                task_description=task.description,
                error=error_message,
                analysis=reflection_result.analysis,
                context={
                    "plan_id": str(plan.id),
                    "current_step": plan.current_step,
                    "execution_context": execution_context
                },
                similar_situations=reflection_result.similar_situations
            )
            
            # Save learning pattern to memory
            if agent_id:
                await reflection_service.learn_from_mistake(
                    agent_id=agent_id,
                    task_description=task.description,
                    error=error_message,
                    fix=fix_suggestion,
                    analysis=reflection_result.analysis
                )
            
            # Create new plan using auto_replan_on_error (specialized for automatic replanning)
            planning_service = PlanningService(self.db)
            
            # Prepare execution context with reflection results
            enhanced_context = {
                "error_analysis": reflection_result.analysis,
                "fix_suggestion": fix_suggestion,
                "similar_situations": reflection_result.similar_situations,
                **(execution_context or {})
            }
            
            # Use auto_replan_on_error with classified error information
            error_severity = classified_error.severity.value if classified_error else None
            error_category = classified_error.category.value if classified_error else None
            
            new_plan = await planning_service.auto_replan_on_error(
                plan_id=plan.id,
                error_message=error_message,
                error_severity=error_severity,
                error_category=error_category,
                execution_context=enhanced_context,
                failed_at_step=plan.current_step
            )
            
            logger.info(
                f"Created new plan {new_plan.id} (version {new_plan.version}) after failure",
                extra={
                    "original_plan_id": str(plan.id),
                    "new_plan_id": str(new_plan.id),
                    "new_version": new_plan.version,
                    "error_type": reflection_result.analysis.get("error_type", "unknown")
                }
            )
            
            # The new plan will automatically go through approval process
            # (handled by _create_plan_approval_request in PlanningService)
            # If critical steps detected, task will transition to PENDING_APPROVAL
            
            return new_plan
            
        except Exception as e:
            logger.error(
                f"Error handling plan failure: {e}",
                exc_info=True,
                extra={
                    "plan_id": str(plan.id),
                    "error": error_message
                }
            )
            return None

    def _extract_template_from_completed_plan(self, plan: Plan):
        """
        Extract a template from a successfully completed plan if it meets quality criteria.
        
        Criteria for template extraction:
        - Plan must be completed successfully
        - Plan must have at least minimum number of steps (configurable, default: 2)
        - Plan execution should be within reasonable time (not too fast = likely incomplete, not too slow = likely inefficient)
        - Plan should have a clear structure (goal, steps, strategy)
        
        Args:
            plan: The completed plan to extract template from
        """
        from app.services.plan_template_service import PlanTemplateService
        from app.core.config import get_settings
        
        settings = get_settings()
        
        # Check if template extraction is enabled
        if not getattr(settings, 'enable_plan_template_extraction', True):
            logger.debug(f"Plan template extraction is disabled, skipping plan {plan.id}")
            return
        
        # Quality criteria
        min_steps = getattr(settings, 'plan_template_min_steps', 2)
        min_duration_seconds = getattr(settings, 'plan_template_min_duration', 10)  # At least 10 seconds
        max_duration_seconds = getattr(settings, 'plan_template_max_duration', 86400)  # Not more than 24 hours
        
        # Validate plan structure
        if not plan.goal:
            logger.debug(f"Plan {plan.id} has no goal, skipping template extraction")
            return
        
        steps = plan.steps if isinstance(plan.steps, list) else []
        if len(steps) < min_steps:
            logger.debug(f"Plan {plan.id} has only {len(steps)} steps (minimum: {min_steps}), skipping template extraction")
            return
        
        # Validate execution time
        if plan.actual_duration:
            if plan.actual_duration < min_duration_seconds:
                logger.debug(f"Plan {plan.id} completed too quickly ({plan.actual_duration}s), likely incomplete, skipping template extraction")
                return
            if plan.actual_duration > max_duration_seconds:
                logger.debug(f"Plan {plan.id} took too long ({plan.actual_duration}s), likely inefficient, skipping template extraction")
                return
        
        # Check if plan already has a template extracted
        template_service = PlanTemplateService(self.db)
        existing_templates = template_service.list_templates(limit=1000)
        for template in existing_templates:
            if template.source_plan_ids and plan.id in template.source_plan_ids:
                logger.debug(f"Template already exists for plan {plan.id}, skipping extraction")
                return
        
        # Extract template
        logger.info(
            f"Extracting template from completed plan {plan.id}",
            extra={
                "plan_id": str(plan.id),
                "steps_count": len(steps),
                "duration": plan.actual_duration
            }
        )
        
        # Extract template (synchronous call, but may have async operations inside)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to handle this differently
                # For now, create a task
                template = template_service.extract_template_from_plan(
                    plan_id=plan.id,
                    template_name=None,  # Auto-generate name
                    category=None,  # Auto-infer category
                    tags=None  # Auto-infer tags
                )
            else:
                template = template_service.extract_template_from_plan(
                    plan_id=plan.id,
                    template_name=None,  # Auto-generate name
                    category=None,  # Auto-infer category
                    tags=None  # Auto-infer tags
                )
        except RuntimeError:
            # No event loop, call directly
            template = template_service.extract_template_from_plan(
                plan_id=plan.id,
                template_name=None,  # Auto-generate name
                category=None,  # Auto-infer category
                tags=None  # Auto-infer tags
            )
        
        if template:
            logger.info(
                f"Successfully extracted template {template.id} from plan {plan.id}",
                extra={
                    "template_id": str(template.id),
                    "template_name": template.name,
                    "plan_id": str(plan.id)
                }
            )
        else:
            logger.warning(f"Failed to extract template from plan {plan.id}")

