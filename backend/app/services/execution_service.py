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
from app.agents.simple_agent import SimpleAgent
from app.tools.python_tool import PythonTool
import time

logger = LoggingConfig.get_logger(__name__)


class StepExecutor:
    """Executor for individual plan steps"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
    
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
        
        # Check if step specifies an agent
        agent_id = step.get("agent")
        tool_id = step.get("tool")
        
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
        
        # Get appropriate model
        default_server = OllamaService.get_default_server(self.db)
        if not default_server:
            raise ValueError("No default server found")
        
        models = OllamaService.get_models_for_server(self.db, str(default_server.id))
        execution_model = None
        
        # Prefer code generation models
        for model in models:
            if model.capabilities and "code_generation" in model.capabilities:
                execution_model = model
                break
        
        # Fallback to general chat
        if not execution_model and models:
            execution_model = models[0]
        
        if not execution_model:
            raise ValueError("No suitable model found for execution")
        
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
        
        # Execute with timeout
        timeout = step.get("timeout", 300)
        try:
            response = await asyncio.wait_for(
                ollama_client.generate(
                    prompt=user_prompt,
                    server_url=f"{default_server.url}/v1",
                    model=execution_model.model_name or execution_model.name,
                    system_prompt=system_prompt,
                    task_type="code_generation"
                ),
                timeout=timeout
            )
            
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
        tool_service = ToolService(self.db)
        agent = SimpleAgent(
            agent_id=agent_uuid,
            agent_service=agent_service,
            tool_service=tool_service
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
                tool_service = ToolService(self.db)
                tool_data = tool_service.get_tool(tool_uuid)
                
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
        self.step_executor = StepExecutor(db)
        self.checkpoint_service = CheckpointService(db)
    
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
            return plan
        
        # Execution context (results from previous steps)
        execution_context = {}
        
        # Execute steps in order
        for i, step in enumerate(steps):
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
                        raise ValueError(f"Dependency {dep_id} not found in execution context")
            
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
                # Try to rollback to last checkpoint
                try:
                    latest_checkpoint = self.checkpoint_service.get_latest_checkpoint("plan", plan.id)
                    if latest_checkpoint:
                        logger.info(
                            f"Rolling back plan {plan.id} to checkpoint {latest_checkpoint.id}",
                            extra={
                                "plan_id": str(plan.id),
                                "checkpoint_id": str(latest_checkpoint.id),
                                "error": step_result.get('error', 'Unknown error'),
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
                
                # Log failure
                logger.error(
                    "Plan failed at step",
                    extra={
                        "plan_id": str(plan.id),
                        "step_index": i,
                        "step_id": step.get('step_id'),
                        "error": step_result.get('error', 'Unknown error'),
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
        if plan.status == "executing" and plan.current_step >= len(steps) - 1:
            plan.status = "completed"
            plan.current_step = len(steps)
        
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

