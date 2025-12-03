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
        # OllamaClient will be created dynamically when needed
        # to use database-backed server/model selection
    
    async def generate_plan(
        self,
        task_description: str,
        task_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """
        Generate a plan for a task using LLM
        
        Args:
            task_description: Description of the task
            task_id: Optional task ID to link plan to
            context: Additional context (existing artifacts, constraints, etc.)
            
        Returns:
            Created plan in DRAFT status
        """
        
        # 1. Analyze task and create strategy
        strategy = await self._analyze_task(task_description, context)
        
        # 2. Decompose task into steps
        steps = await self._decompose_task(task_description, strategy, context)
        
        # 3. Assess risks
        risks = await self._assess_risks(steps, strategy)
        
        # 4. Create alternatives if needed
        alternatives = await self._create_alternatives(steps, strategy, risks)
        
        # 5. Create plan object
        if not task_id:
            # Create a task if not provided
            task = Task(
                description=task_description,
                status=TaskStatus.DRAFT,  # Start as DRAFT, will transition to PENDING_APPROVAL if needed
                created_by_role="planner"  # Created by planner agent
            )
            self.db.add(task)
            self.db.flush()
            task_id = task.id
        
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
            
            # Store quality score in plan metadata if available
            if plan.agent_metadata is None:
                plan.agent_metadata = {}
            if isinstance(plan.agent_metadata, dict):
                plan.agent_metadata["quality_score"] = quality_score
                self.db.commit()
                self.db.refresh(plan)
            
            logger.debug(
                f"Calculated quality score for plan {plan.id}",
                extra={"plan_id": str(plan.id), "quality_score": quality_score}
            )
        except Exception as e:
            logger.warning(f"Failed to calculate plan quality score: {e}", exc_info=True)
        
        return plan
    
    async def _analyze_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze task and create strategy"""
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

Return a JSON object with these fields."""
        
        context_str = ""
        if context:
            context_str = f"\n\nContext:\n{json.dumps(context, indent=2, ensure_ascii=False)}"
        
        user_prompt = f"""Task: {task_description}{context_str}

Analyze this task and create a strategic plan. Return only valid JSON."""
        
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
            
            # Create OllamaClient
            ollama_client = OllamaClient()
            
            # IMPORTANT: Add timeout to prevent infinite loops
            import asyncio
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
            except asyncio.TimeoutError:
                raise ValueError("Strategy analysis timed out after 5 minutes. Task may be too complex or model is stuck.")
            
            # Parse JSON from response
            strategy = self._parse_json_from_response(response.response)
            
            # Ensure required fields
            if not isinstance(strategy, dict):
                strategy = {}
            
            strategy.setdefault("approach", "Standard approach")
            strategy.setdefault("assumptions", [])
            strategy.setdefault("constraints", [])
            strategy.setdefault("success_criteria", [])
            
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
        context: Optional[Dict[str, Any]]
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
        
        context_str = ""
        if context:
            context_str = f"\n\nContext:\n{json.dumps(context, indent=2, ensure_ascii=False)}"
        
        strategy_str = json.dumps(strategy, indent=2, ensure_ascii=False)
        
        user_prompt = f"""Task: {task_description}

Strategy:
{strategy_str}{context_str}

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
            
            # Create OllamaClient
            ollama_client = OllamaClient()
            
            # IMPORTANT: Add timeout to prevent infinite loops
            import asyncio
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
            except asyncio.TimeoutError:
                raise ValueError("Task decomposition timed out after 5 minutes. Task may be too complex or model is stuck.")
            
            # Parse JSON from response
            steps = self._parse_json_from_response(response.response)
            
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
    
    def _parse_json_from_response(self, response_text: str) -> Any:
        """Parse JSON from LLM response"""
        # Try to find JSON in response
        # Look for JSON object or array
        json_match = re.search(r'\{.*\}|\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try to parse entire response
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Return empty structure
            return {}
    
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
        if plan.agent_metadata and isinstance(plan.agent_metadata, dict):
            agent_id_str = plan.agent_metadata.get("agent_id")
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
        
        return new_plan

