"""
Planning service for generating and managing task plans
"""
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import json
import re

from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.core.ollama_client import OllamaClient, TaskType
from app.services.ollama_service import OllamaService
from app.services.approval_service import ApprovalService
from app.models.approval import ApprovalRequestType
from app.core.tracing import get_tracer, add_span_attributes, get_current_trace_id
from app.services.request_logger import RequestLogger


class PlanningService:
    """Service for generating and managing task plans"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
        self.model_logs = []  # Collect model interaction logs for this planning session
        self.current_task_id = None  # Track current task_id for real-time log saving
        # OllamaClient will be created dynamically when needed
        # to use database-backed server/model selection
    
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
        from datetime import datetime
        
        log_entry = {
            "type": log_type,
            "model": model,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
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
    
    async def generate_plan(
        self,
        task_description: str,
        task_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None
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
            
        Returns:
            Created plan in DRAFT status
        """
        
        # 0. Try to apply procedural memory patterns (successful plan templates)
        procedural_pattern = None
        agent_id = None
        if context and isinstance(context, dict):
            agent_id_str = context.get("agent_id")
            if agent_id_str:
                try:
                    agent_id = UUID(agent_id_str)
                except (ValueError, TypeError):
                    pass
        
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
                # Set current_task_id for real-time log saving
                self.current_task_id = task_id
        else:
            # Create task first for real-time logging if not provided
            task = Task(
                description=task_description[:500],  # Truncate if too long
                status=TaskStatus.PENDING,
                created_by_role="planner"
            )
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            task_id = task.id
            self.current_task_id = task_id  # Set for real-time log saving
        
        # Merge Digital Twin context with provided context
        enhanced_context = {**(context or {}), **digital_twin_context}
        if procedural_pattern:
            enhanced_context["procedural_pattern"] = procedural_pattern
        
        # 1. Analyze task and create strategy (with Digital Twin context)
        strategy = await self._analyze_task(task_description, enhanced_context, task_id)
        
        # 2. Decompose task into steps (use procedural pattern if available)
        steps = await self._decompose_task(
            task_description,
            strategy,
            enhanced_context,
            task_id=task_id
        )
        
        # 3. Assess risks
        risks = await self._assess_risks(steps, strategy)
        
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
                "agent_selection": {
                    "available_agents": [],
                    "selected_agents": [],
                    "reasons": {}
                },
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
                    "created_at": datetime.utcnow().isoformat(),
                    "task_id": str(task_id),
                    "plan_id": str(plan.id)
                }
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
    
    async def _analyze_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]],
        task_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Analyze task and create strategy using Digital Twin context"""
        with self.tracer.start_as_current_span("planning.analyze_task") as span:
            add_span_attributes(
                task_description=task_description[:100],
            )
            
            system_prompt = """You are an expert at task analysis and strategic planning.
Analyze the task and create a strategy that includes:
1. approach: General approach to solving the task
2. assumptions: List of assumptions made
3. constraints: List of constraints and limitations
4. success_criteria: List of criteria for successful completion

Return a JSON object with these fields. Only return valid JSON, no additional text."""
        
            # Build enhanced prompt with Digital Twin context
        user_prompt = self._build_enhanced_analysis_prompt(task_description, context, task_id)
        
        try:
            # Use ModelSelector for dual-model architecture
            from app.core.model_selector import ModelSelector
            
            model_selector = ModelSelector(self.db)
            planning_model = model_selector.get_planning_model()
            
            if not planning_model:
                raise ValueError("No suitable model found for planning")
            
            # Get server for the model
            server = model_selector.get_server_for_model(planning_model)
            if not server:
                raise ValueError("No server found for planning model")
            
            # Log request to model
            self._add_model_log(
                log_type="request",
                model=planning_model.model_name,
                content={
                    "prompt": user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt,
                    "system_prompt": system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt,
                    "task": "analyze_task"
                },
                metadata={
                    "server": server.name,
                    "server_url": server.get_api_url(),
                    "model_id": str(planning_model.id) if hasattr(planning_model, 'id') else None
                }
            )
            
            # Create OllamaClient
            ollama_client = OllamaClient()
            
            # IMPORTANT: Add timeout to prevent infinite loops
            import asyncio
            import time
            start_time = time.time()
            try:
                response = await asyncio.wait_for(
                    ollama_client.generate(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        task_type=TaskType.PLANNING,
                        model=planning_model.model_name,
                        server_url=server.get_api_url()
                    ),
                    timeout=300.0  # 5 minutes max for strategy analysis
                )
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log response from model
                self._add_model_log(
                    log_type="response",
                    model=planning_model.model_name,
                    content={
                        "response": response.response[:2000] + "..." if len(response.response) > 2000 else response.response,
                        "full_length": len(response.response)
                    },
                    metadata={
                        "duration_ms": duration_ms,
                        "task": "analyze_task"
                    }
                )
            except asyncio.TimeoutError:
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
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
            
            # Stage 2: Log request analysis (HITL observation)
            self._add_model_log(
                log_type="request_analysis",
                model=planning_model.model_name,
                content={
                    "analysis_type": "strategy_generation",
                    "response_preview": response.response[:500] + "..." if len(response.response) > 500 else response.response
                },
                metadata={
                    "stage": "analysis",
                    "operation": "analyze_task",
                    "duration_ms": duration_ms
                },
                stage="analysis"
            )
            
            # Parse JSON from response with validation
            strategy = self._parse_and_validate_json(
                response.response,
                expected_keys=["approach", "assumptions", "constraints", "success_criteria"]
            )
            
            # Ensure required fields
            if not isinstance(strategy, dict):
                strategy = {}
            
            strategy.setdefault("approach", "Standard approach")
            strategy.setdefault("assumptions", [])
            strategy.setdefault("constraints", [])
            strategy.setdefault("success_criteria", [])
            
            # Log parsed strategy
            self._add_model_log(
                log_type="action_progress",
                model=planning_model.model_name,
                content={
                    "action": "strategy_parsed",
                    "strategy": strategy
                },
                metadata={
                    "stage": "analysis",
                    "operation": "analyze_task"
                },
                stage="analysis"
            )
            
            return strategy
            
        except Exception as e:
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
            
            system_prompt = """You are an expert at breaking down complex tasks into executable steps.
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
        
        # Build enhanced prompt with Digital Twin context
        strategy_str = json.dumps(strategy, indent=2, ensure_ascii=False)
        
        # Get Digital Twin context if task exists
        digital_twin_context = {}
        if task_id:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if task:
                digital_twin_context = task.get_context()
        
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
            # Use ModelSelector for dual-model architecture
            from app.core.model_selector import ModelSelector
            
            model_selector = ModelSelector(self.db)
            planning_model = model_selector.get_planning_model()
            
            if not planning_model:
                raise ValueError("No suitable model found for planning")
            
            # Get server for the model
            server = model_selector.get_server_for_model(planning_model)
            if not server:
                raise ValueError("No server found for planning model")
            
            # Log request to model
            self._add_model_log(
                log_type="request",
                model=planning_model.model_name,
                content={
                    "prompt": user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt,
                    "system_prompt": system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt,
                    "task": "decompose_task",
                    "strategy": strategy
                },
                metadata={
                    "server": server.name,
                    "server_url": server.get_api_url(),
                    "model_id": str(planning_model.id) if hasattr(planning_model, 'id') else None
                }
            )
            
            # Create OllamaClient
            ollama_client = OllamaClient()
            
            # IMPORTANT: Add timeout to prevent infinite loops
            import asyncio
            import time
            start_time = time.time()
            try:
                response = await asyncio.wait_for(
                    ollama_client.generate(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        task_type=TaskType.PLANNING,
                        model=planning_model.model_name,
                        server_url=server.get_api_url()
                    ),
                    timeout=300.0  # 5 minutes max for task decomposition
                )
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log response from model
                self._add_model_log(
                    log_type="response",
                    model=planning_model.model_name,
                    content={
                        "response": response.response[:2000] + "..." if len(response.response) > 2000 else response.response,
                        "full_length": len(response.response),
                        "steps_count": len(json.loads(response.response)) if isinstance(json.loads(response.response), list) else 0
                    },
                    metadata={
                        "duration_ms": duration_ms,
                        "task": "decompose_task"
                    }
                )
            except asyncio.TimeoutError:
                import time
                duration_ms = int((time.time() - start_time) * 1000)
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
            
            # Parse JSON from response with validation
            steps = self._parse_and_validate_json(response.response, expected_structure="list")
            
            # Ensure it's a list
            if not isinstance(steps, list):
                steps = []
            
            # Validate and fix steps
            validated_steps = []
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
            
            return validated_steps
            
        except Exception as e:
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
        
        # Use adaptive approval service to determine if approval is needed
        requires_approval, decision_metadata = adaptive_approval.should_require_approval(
            plan=plan,
            agent_id=agent_id,
            task_risk_level=risks.get("overall_risk")
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
                task.status = TaskStatus.PENDING_APPROVAL
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
            plan.approved_at = datetime.utcnow()
            # Also update task status if it's in DRAFT
            if task and task.status == TaskStatus.DRAFT:
                task.status = TaskStatus.APPROVED
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
        plan.approved_at = datetime.utcnow()
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
        
        # Create new plan version
        new_plan = await self.generate_plan(
            task_description=task.description,
            task_id=task.id,
            context={
                **(context or {}),
                "previous_plan": {
                    "version": original_plan.version,
                    "steps": original_plan.steps,
                    "reason_for_replan": reason
                }
            }
        )
        
        # Increment version
        new_plan.version = original_plan.version + 1
        
        self.db.commit()
        self.db.refresh(new_plan)
        
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
                "timestamp": datetime.utcnow().isoformat(),
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
                    "updated_at": datetime.utcnow().isoformat()
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
                "timestamp": datetime.utcnow().isoformat(),
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
            
            # Also get patterns from MetaLearningService
            learning_patterns = meta_learning.get_learning_patterns(
                agent_id=agent_id,
                pattern_type="strategy",
                limit=5
            )
            
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

