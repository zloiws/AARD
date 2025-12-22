"""
Decision Pipeline for multi-stage task execution
Combines: Planner → Router → Executor → Critic → Reflection
"""
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.core.tracing import add_span_attributes, get_tracer
from app.services.critic_service import CriticService
from app.services.decision_router import DecisionRouter
from app.services.execution_service import ExecutionService
from app.services.memory_service import MemoryService
from app.services.planning_service import PlanningService
from app.services.reflection_service import ReflectionService
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class DecisionPipeline:
    """Multi-stage decision pipeline for task execution"""
    
    def __init__(self, db: Session = None):
        """
        Initialize Decision Pipeline
        
        Args:
            db: Database session (optional)
        """
        self.db = db or SessionLocal()
        self.planner = PlanningService(self.db)
        self.router = DecisionRouter(self.db)
        self.executor = ExecutionService(self.db)
        self.critic = CriticService(self.db)
        self.reflection = ReflectionService(self.db)
        self.memory_service = MemoryService(self.db)
        self.tracer = get_tracer(__name__)
    
    async def execute_task(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        requirements: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        agent_id: Optional[UUID] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Execute task through full decision pipeline
        
        Pipeline flow:
        1. Planner: Break down task into steps
        2. Router: Select appropriate tools/agents/prompts
        3. Executor: Execute each step
        4. Critic: Validate results
        5. Reflection: Analyze failures and retry if needed
        
        Args:
            task_description: Task description
            task_type: Task type
            requirements: Task requirements
            context: Additional context
            agent_id: Optional agent ID
            max_retries: Maximum retry attempts
            
        Returns:
            Execution result with pipeline metadata
        """
        with self.tracer.start_as_current_span(
            "decision_pipeline.execute_task",
            attributes={
                "task_type": task_type or "unknown",
                "agent_id": str(agent_id) if agent_id else None
            }
        ) as span:
            pipeline_start_time = time.time()
            
            try:
                # Stage 1: Planning
                plan_result = await self._planning_stage(
                    task_description, task_type, requirements, context
                )
                
                if not plan_result.get("success"):
                    return {
                        "status": "failed",
                        "stage": "planning",
                        "result": None,
                        "message": plan_result.get("error", "Planning failed"),
                        "pipeline_metadata": {
                            "stages_completed": ["planning"],
                            "total_time": time.time() - pipeline_start_time
                        }
                    }
                
                plan = plan_result.get("plan")
                steps = plan_result.get("steps", [])
                
                # Stage 2: Routing
                routing_results = []
                for step in steps:
                    routing_result = await self._routing_stage(
                        step, task_type, requirements, context
                    )
                    routing_results.append(routing_result)
                
                # Stage 3: Execution
                execution_results = []
                for i, (step, routing) in enumerate(zip(steps, routing_results)):
                    execution_result = await self._execution_stage(
                        step, routing, context, agent_id
                    )
                    execution_results.append(execution_result)
                    
                    # Stage 4: Critic (validate result)
                    validation_result = await self._critic_stage(
                        execution_result, step, requirements
                    )
                    execution_result["validation"] = validation_result.to_dict()
                    
                    # If validation fails and we have retries, go to reflection
                    if not validation_result.is_valid and i < max_retries:
                        # Stage 5: Reflection (analyze and retry)
                        reflection_result = await self._reflection_stage(
                            step, execution_result, validation_result, agent_id
                        )
                        execution_result["reflection"] = reflection_result.to_dict()
                        
                        # Retry with fix if available
                        if reflection_result.suggested_fix:
                            fix = reflection_result.suggested_fix
                            logger.info(f"Retrying step {i} with fix: {fix.get('message')}")
                            
                            # Apply fix and retry
                            retry_result = await self._execution_stage(
                                step, routing, context, agent_id, fix=fix
                            )
                            retry_validation = await self._critic_stage(
                                retry_result, step, requirements
                            )
                            
                            if retry_validation.is_valid:
                                execution_result = retry_result
                                execution_result["validation"] = retry_validation.to_dict()
                                execution_result["retried"] = True
                            else:
                                execution_result["retry_failed"] = True
                
                # Aggregate results
                all_valid = all(
                    r.get("validation", {}).get("is_valid", False)
                    for r in execution_results
                )
                
                final_result = {
                    "status": "success" if all_valid else "partial",
                    "result": execution_results,
                    "message": "Task completed" if all_valid else "Task completed with issues",
                    "pipeline_metadata": {
                        "stages_completed": ["planning", "routing", "execution", "critic", "reflection"],
                        "total_time": time.time() - pipeline_start_time,
                        "steps_count": len(steps),
                        "all_valid": all_valid
                    }
                }
                
                if span:
                    add_span_attributes(
                        pipeline_success=all_valid,
                        pipeline_steps=len(steps),
                        pipeline_time=time.time() - pipeline_start_time
                    )
                
                return final_result
                
            except Exception as e:
                if span:
                    add_span_attributes(pipeline_error=str(e))
                logger.error(f"Pipeline execution error: {e}", exc_info=True)
                return {
                    "status": "failed",
                    "result": None,
                    "message": f"Pipeline error: {str(e)}",
                    "pipeline_metadata": {
                        "stages_completed": [],
                        "total_time": time.time() - pipeline_start_time,
                        "error": str(e)
                    }
                }
    
    async def _planning_stage(
        self,
        task_description: str,
        task_type: Optional[str],
        requirements: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Stage 1: Planning - break down task into steps"""
        try:
            # Use existing planning service
            plan_obj = await self.planner.generate_plan(
                task_description=task_description,
                context=context or {}
            )
            
            # Convert plan to dict format
            plan = {
                "id": str(plan_obj.id),
                "goal": plan_obj.goal,
                "steps": plan_obj.steps or [],
                "strategy": plan_obj.strategy
            }
            
            steps = plan.get("steps", [])
            
            return {
                "success": True,
                "plan": plan,
                "steps": steps
            }
        except Exception as e:
            logger.error(f"Planning stage error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _routing_stage(
        self,
        step: Dict[str, Any],
        task_type: Optional[str],
        requirements: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Stage 2: Routing - select tools/agents/prompts"""
        try:
            step_description = step.get("description", step.get("action", ""))
            
            routing_decision = await self.router.route_task(
                task_description=step_description,
                task_type=task_type,
                requirements=requirements,
                context=context
            )
            
            return routing_decision
        except Exception as e:
            logger.error(f"Routing stage error: {e}", exc_info=True)
            return {
                "tool": None,
                "agent": None,
                "prompt": None,
                "reasoning": f"Routing error: {e}"
            }
    
    async def _execution_stage(
        self,
        step: Dict[str, Any],
        routing: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        agent_id: Optional[UUID],
        fix: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Stage 3: Execution - execute the step"""
        try:
            step_description = step.get("description", step.get("action", ""))
            
            # Apply fix if provided
            if fix:
                step_description = f"{step_description}\n\nFix applied: {fix.get('message', '')}"
                if fix.get("suggested_changes"):
                    changes = "\n".join([
                        f"- {ch.get('action')}: {ch.get('reason')}"
                        for ch in fix.get("suggested_changes", [])
                    ])
                    step_description = f"{step_description}\n\nChanges:\n{changes}"
            
            # Use selected tool if available
            if routing.get("tool"):
                tool_name = routing["tool"].get("name")
                tool_result = await self.executor._execute_with_tool(
                    step_description,
                    tool_id=routing["tool"].get("id"),
                    context=context
                )
                return {
                    "status": "success" if tool_result.get("status") == "success" else "failed",
                    "result": tool_result.get("result"),
                    "message": tool_result.get("message"),
                    "metadata": {
                        "execution_method": "tool",
                        "tool_name": tool_name,
                        **tool_result.get("metadata", {})
                    }
                }
            
            # Use selected agent if available
            if routing.get("agent"):
                agent_id = UUID(routing["agent"].get("id"))
                agent_result = await self.executor._execute_with_agent(
                    step_description,
                    agent_id=agent_id,
                    context=context
                )
                return {
                    "status": "success" if agent_result.get("status") == "success" else "failed",
                    "result": agent_result.get("result"),
                    "message": agent_result.get("message"),
                    "metadata": {
                        "execution_method": "agent",
                        "agent_id": str(agent_id),
                        **agent_result.get("metadata", {})
                    }
                }
            
            # Fallback to LLM execution
            llm_result = await self.executor._execute_action_step(
                step_description,
                context=context
            )
            return {
                "status": "success" if llm_result.get("status") == "success" else "failed",
                "result": llm_result.get("result"),
                "message": llm_result.get("message"),
                "metadata": {
                    "execution_method": "llm",
                    **llm_result.get("metadata", {})
                }
            }
            
        except Exception as e:
            logger.error(f"Execution stage error: {e}", exc_info=True)
            return {
                "status": "failed",
                "result": None,
                "message": f"Execution error: {str(e)}",
                "metadata": {"error": str(e)}
            }
    
    async def _critic_stage(
        self,
        execution_result: Dict[str, Any],
        step: Dict[str, Any],
        requirements: Optional[Dict[str, Any]]
    ) -> Any:
        """Stage 4: Critic - validate execution result"""
        try:
            result = execution_result.get("result")
            step_description = step.get("description", step.get("action", ""))
            
            validation = await self.critic.validate_result(
                result=result,
                requirements=requirements,
                task_description=step_description
            )
            
            return validation
        except Exception as e:
            logger.error(f"Critic stage error: {e}", exc_info=True)
            from app.services.critic_service import ValidationResult
            return ValidationResult(
                is_valid=False,
                score=0.0,
                issues=[f"Validation error: {str(e)}"],
                validation_type="error"
            )
    
    async def _reflection_stage(
        self,
        step: Dict[str, Any],
        execution_result: Dict[str, Any],
        validation_result: Any,
        agent_id: Optional[UUID]
    ) -> Any:
        """Stage 5: Reflection - analyze failures and generate fixes"""
        try:
            step_description = step.get("description", step.get("action", ""))
            error = execution_result.get("message", "Validation failed")
            
            # Analyze failure
            reflection = await self.reflection.analyze_failure(
                task_description=step_description,
                error=error,
                context=execution_result.get("metadata", {}),
                agent_id=agent_id
            )
            
            # Generate fix
            if not validation_result.is_valid:
                fix = await self.reflection.generate_fix(
                    task_description=step_description,
                    error=error,
                    analysis=reflection.analysis,
                    context=execution_result.get("metadata", {}),
                    similar_situations=reflection.similar_situations
                )
                reflection.suggested_fix = fix
                
                # Learn from mistake
                if agent_id:
                    await self.reflection.learn_from_mistake(
                        agent_id=agent_id,
                        task_description=step_description,
                        error=error,
                        fix=fix,
                        analysis=reflection.analysis
                    )
            
            return reflection
            
        except Exception as e:
            logger.error(f"Reflection stage error: {e}", exc_info=True)
            from app.services.reflection_service import ReflectionResult
            return ReflectionResult(
                analysis={"error": str(e)},
                suggested_fix=None,
                similar_situations=[],
                improvements=[]
            )

