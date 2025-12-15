"""
Planning Hypothesis Service for generating and validating plan hypotheses
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.planning import PlanHypothesis, PlanLifecycle, PlanHypothesisNode
from app.models.interpretation import DecisionTimeline, DecisionNode, DecisionEdge
from backend.app.core.ollama_client import OllamaClient
from backend.app.services.ollama_service import OllamaService
from backend.app.core.config import get_settings
from backend.app.core.tracing import get_tracer


class PlanningHypothesisService:
    """Service for generating and managing plan hypotheses"""

    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
        self.settings = get_settings()
        self.ollama_service = OllamaService(db)

    async def generate_plan_hypotheses(
        self,
        timeline_id: UUID,
        interpretation_result: Dict[str, Any]
    ) -> List[PlanHypothesis]:
        """
        Generate plan hypotheses based on interpretation result

        Args:
            timeline_id: ID of the decision timeline
            interpretation_result: Result from InterpretationService

        Returns:
            List of generated plan hypotheses
        """
        with self.tracer.start_as_span("generate_plan_hypotheses") as span:
            span.set_attribute("timeline_id", str(timeline_id))

            # Get timeline and existing interpretation
            timeline = self.db.query(DecisionTimeline).filter(
                DecisionTimeline.id == timeline_id
            ).first()

            if not timeline:
                raise ValueError(f"DecisionTimeline {timeline_id} not found")

            # Generate hypotheses using LLM
            hypotheses_data = await self._generate_hypotheses_from_interpretation(
                interpretation_result
            )

            # Create hypothesis objects
            hypotheses = []
            for hypothesis_data in hypotheses_data:
                hypothesis = PlanHypothesis(
                    timeline_id=timeline_id,
                    name=hypothesis_data["name"],
                    description=hypothesis_data["description"],
                    assumptions=hypothesis_data["assumptions"],
                    risks=hypothesis_data["risks"],
                    confidence=hypothesis_data["confidence"],
                    steps=hypothesis_data["steps"],
                    dependencies=hypothesis_data["dependencies"],
                    resources=hypothesis_data["resources"],
                    lifecycle=PlanLifecycle.DRAFT
                )

                self.db.add(hypothesis)
                self.db.flush()  # Get ID for nodes

                # Create hypothesis nodes in timeline
                await self._create_hypothesis_nodes(hypothesis, interpretation_result)

                hypotheses.append(hypothesis)

            self.db.commit()
            return hypotheses

    async def _generate_hypotheses_from_interpretation(
        self,
        interpretation_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate hypothesis data using LLM based on interpretation"""

        prompt = f"""
Based on the following interpretation of a user request, generate 2-3 plan hypotheses.
Each hypothesis should include assumptions, risks, confidence level, and a structured plan.

Interpretation:
{json.dumps(interpretation_result, indent=2)}

Generate hypotheses in the following JSON format:
[
  {{
    "name": "Hypothesis name",
    "description": "Brief description",
    "assumptions": ["assumption 1", "assumption 2"],
    "risks": [
      {{"description": "risk description", "probability": 0.3, "impact": "high"}},
      {{"description": "another risk", "probability": 0.1, "impact": "medium"}}
    ],
    "confidence": 0.8,
    "steps": [
      {{"name": "step 1", "description": "step description", "duration": 30}},
      {{"name": "step 2", "description": "step description", "duration": 60}}
    ],
    "dependencies": {{"step1": [], "step2": ["step1"]}},
    "resources": ["resource1", "resource2"]
  }}
]
"""

        try:
            response = await self.ollama_service.generate_completion(
                prompt=prompt,
                model="llama3.2",
                temperature=0.7,
                max_tokens=2000
            )

            # Parse JSON response
            hypotheses_text = response.get("response", "[]")
            hypotheses = json.loads(hypotheses_text)

            if not isinstance(hypotheses, list):
                hypotheses = [hypotheses]

            return hypotheses

        except Exception as e:
            # Fallback to deterministic hypotheses
            return self._generate_fallback_hypotheses(interpretation_result)

    def _generate_fallback_hypotheses(
        self,
        interpretation_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate fallback hypotheses when LLM fails"""

        intent = interpretation_result.get("intent", "unknown")
        confidence = interpretation_result.get("confidence", 0.5)

        return [
            {
                "name": f"Direct {intent} approach",
                "description": f"Execute {intent} directly",
                "assumptions": [f"System can handle {intent} requests"],
                "risks": [
                    {"description": "Unexpected complexity", "probability": 0.2, "impact": "medium"}
                ],
                "confidence": confidence,
                "steps": [
                    {"name": "analyze", "description": "Analyze requirements", "duration": 15},
                    {"name": "execute", "description": "Execute the task", "duration": 45},
                    {"name": "verify", "description": "Verify results", "duration": 10}
                ],
                "dependencies": {"analyze": [], "execute": ["analyze"], "verify": ["execute"]},
                "resources": ["core_system"]
            }
        ]

    async def _create_hypothesis_nodes(
        self,
        hypothesis: PlanHypothesis,
        interpretation_result: Dict[str, Any]
    ) -> None:
        """Create decision nodes for hypothesis elements"""

        # Create assumption nodes
        for assumption in hypothesis.assumptions or []:
            node = DecisionNode(
                timeline_id=hypothesis.timeline_id,
                node_type="assumption",
                content={"text": assumption, "hypothesis_id": str(hypothesis.id)},
                metadata={"hypothesis_stage": "planning"}
            )
            self.db.add(node)
            self.db.flush()

            # Link to hypothesis
            hypothesis_node = PlanHypothesisNode(
                hypothesis_id=hypothesis.id,
                node_id=node.id,
                node_type="assumption",
                node_metadata={"text": assumption}
            )
            self.db.add(hypothesis_node)

        # Create risk nodes
        for risk in hypothesis.risks or []:
            node = DecisionNode(
                timeline_id=hypothesis.timeline_id,
                node_type="risk",
                content={"description": risk.get("description"), "hypothesis_id": str(hypothesis.id)},
                metadata={"probability": risk.get("probability"), "impact": risk.get("impact")}
            )
            self.db.add(node)
            self.db.flush()

            hypothesis_node = PlanHypothesisNode(
                hypothesis_id=hypothesis.id,
                node_id=node.id,
                node_type="risk",
                node_metadata=risk
            )
            self.db.add(hypothesis_node)

        # Create step nodes
        for step in hypothesis.steps or []:
            node = DecisionNode(
                timeline_id=hypothesis.timeline_id,
                node_type="plan_step",
                content={"name": step.get("name"), "description": step.get("description"), "hypothesis_id": str(hypothesis.id)},
                metadata={"duration": step.get("duration")}
            )
            self.db.add(node)
            self.db.flush()

            hypothesis_node = PlanHypothesisNode(
                hypothesis_id=hypothesis.id,
                node_id=node.id,
                node_type="step",
                node_metadata=step
            )
            self.db.add(hypothesis_node)

    async def validate_hypothesis(
        self,
        hypothesis_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate a plan hypothesis against current context

        Args:
            hypothesis_id: ID of the hypothesis to validate

        Returns:
            Validation result with updated confidence and issues
        """
        with self.tracer.start_as_span("validate_hypothesis") as span:
            span.set_attribute("hypothesis_id", str(hypothesis_id))

            hypothesis = self.db.query(PlanHypothesis).filter(
                PlanHypothesis.id == hypothesis_id
            ).first()

            if not hypothesis:
                raise ValueError(f"PlanHypothesis {hypothesis_id} not found")

            # Basic validation logic
            validation_result = {
                "hypothesis_id": str(hypothesis_id),
                "is_valid": True,
                "confidence": hypothesis.confidence,
                "issues": [],
                "recommendations": []
            }

            # Check assumptions
            for assumption in hypothesis.assumptions or []:
                if "unknown" in assumption.lower():
                    validation_result["issues"].append(f"Uncertain assumption: {assumption}")
                    validation_result["confidence"] = min(validation_result["confidence"], 0.7)

            # Check risks
            high_risk_count = 0
            for risk in hypothesis.risks or []:
                if risk.get("impact") == "high" and risk.get("probability", 0) > 0.3:
                    high_risk_count += 1

            if high_risk_count > 2:
                validation_result["issues"].append("Too many high-impact risks")
                validation_result["confidence"] = min(validation_result["confidence"], 0.6)

            # Update hypothesis confidence
            hypothesis.confidence = validation_result["confidence"]
            self.db.commit()

            return validation_result

    def get_hypotheses_for_timeline(
        self,
        timeline_id: UUID
    ) -> List[PlanHypothesis]:
        """Get all hypotheses for a timeline"""
        return self.db.query(PlanHypothesis).filter(
            PlanHypothesis.timeline_id == timeline_id
        ).order_by(PlanHypothesis.created_at).all()

    def approve_hypothesis(
        self,
        hypothesis_id: UUID
    ) -> PlanHypothesis:
        """Mark hypothesis as approved and ready for execution"""
        hypothesis = self.db.query(PlanHypothesis).filter(
            PlanHypothesis.id == hypothesis_id
        ).first()

        if not hypothesis:
            raise ValueError(f"PlanHypothesis {hypothesis_id} not found")

        hypothesis.lifecycle = PlanLifecycle.APPROVED
        self.db.commit()

        return hypothesis
