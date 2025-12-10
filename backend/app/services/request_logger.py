"""
Service for logging requests and calculating rankings
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.request_log import RequestLog, RequestConsequence
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class RequestLogger:
    """Service for logging requests and calculating rankings"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_request(
        self,
        request_type: str,
        request_data: Dict[str, Any],
        status: str,
        model_used: Optional[str] = None,
        server_url: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> RequestLog:
        """
        Log a request and calculate its ranking
        
        Args:
            request_type: Type of request (chat, plan_generation, etc.)
            request_data: Full request data
            status: Request status (success, failed, timeout, cancelled)
            model_used: Model that was used
            server_url: Server URL that was used
            response_data: Response data
            error_message: Error message if failed
            duration_ms: Duration in milliseconds
            user_id: User ID
            session_id: Session ID
            trace_id: OpenTelemetry trace ID
            
        Returns:
            Created RequestLog
        """
        # Calculate initial scores
        success_score = self._calculate_success_score(status, response_data)
        importance_score = self._calculate_importance_score(request_type)
        impact_score = 0.5  # Will be updated after consequences are added
        
        # Create request log
        request_log = RequestLog(
            request_type=request_type,
            request_data=request_data,
            model_used=model_used,
            server_url=server_url,
            status=status,
            response_data=response_data,
            error_message=error_message,
            duration_ms=duration_ms,
            success_score=success_score,
            importance_score=importance_score,
            impact_score=impact_score,
            user_id=user_id,
            session_id=session_id,
            trace_id=trace_id,
        )
        
        self.db.add(request_log)
        self.db.flush()  # Flush to get ID
        
        # Calculate initial overall rank
        request_log.overall_rank = self._calculate_overall_rank(request_log)
        
        self.db.commit()
        self.db.refresh(request_log)
        
        logger.debug(
            "Request logged",
            extra={
                "request_id": str(request_log.id),
                "request_type": request_type,
                "status": status,
                "overall_rank": request_log.overall_rank,
            }
        )
        
        return request_log
    
    def add_consequence(
        self,
        request_id: UUID,
        consequence_type: str,
        entity_type: str,
        entity_id: UUID,
        impact_type: Optional[str] = None,
        impact_description: Optional[str] = None,
        impact_score: float = 0.0,
    ) -> RequestConsequence:
        """
        Add a consequence to a request log
        
        Args:
            request_id: Request log ID
            consequence_type: Type of consequence (artifact_created, plan_created, etc.)
            entity_type: Type of entity (artifact, plan, approval, etc.)
            entity_id: Entity ID
            impact_type: Impact type (positive, negative, neutral)
            impact_description: Description of impact
            impact_score: Impact score (-1.0 to 1.0)
            
        Returns:
            Created RequestConsequence
        """
        consequence = RequestConsequence(
            request_id=request_id,
            consequence_type=consequence_type,
            entity_type=entity_type,
            entity_id=entity_id,
            impact_type=impact_type,
            impact_description=impact_description,
            impact_score=impact_score,
        )
        
        self.db.add(consequence)
        self.db.flush()
        
        # Update request log with consequence
        request_log = self.db.query(RequestLog).filter(RequestLog.id == request_id).first()
        if request_log:
            # Update arrays
            if entity_type == "artifact":
                if request_log.created_artifacts is None:
                    request_log.created_artifacts = []
                if entity_id not in request_log.created_artifacts:
                    request_log.created_artifacts.append(entity_id)
            elif entity_type == "plan":
                if request_log.created_plans is None:
                    request_log.created_plans = []
                if entity_id not in request_log.created_plans:
                    request_log.created_plans.append(entity_id)
            elif entity_type == "approval":
                if request_log.created_approvals is None:
                    request_log.created_approvals = []
                if entity_id not in request_log.created_approvals:
                    request_log.created_approvals.append(entity_id)
            
            # Recalculate impact score
            request_log.impact_score = self._calculate_impact_score(request_log)
            
            # Recalculate overall rank
            request_log.overall_rank = self._calculate_overall_rank(request_log)
        
        self.db.commit()
        self.db.refresh(consequence)
        
        return consequence
    
    def _calculate_success_score(self, status: str, response_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate success score (0.0-1.0)
        
        Args:
            status: Request status
            response_data: Response data
            
        Returns:
            Success score
        """
        if status == "success":
            # Check response quality if available
            if response_data:
                # Could add more sophisticated quality checks here
                return 1.0
            return 1.0
        elif status == "failed":
            return 0.0
        elif status == "timeout":
            return 0.2
        elif status == "cancelled":
            return 0.3
        else:
            return 0.5
    
    def _calculate_importance_score(self, request_type: str) -> float:
        """
        Calculate importance score based on request type (0.0-1.0)
        
        Args:
            request_type: Type of request
            
        Returns:
            Importance score
        """
        importance_map = {
            "artifact_generation": 0.8,
            "plan_generation": 0.7,
            "plan_execution": 0.7,
            "approval_request": 0.6,
            "chat": 0.3,
            "code_generation": 0.8,
            "code_analysis": 0.6,
        }
        
        return importance_map.get(request_type, 0.5)
    
    def _calculate_impact_score(self, request_log: RequestLog) -> float:
        """
        Calculate impact score based on consequences (0.0-1.0)
        
        Args:
            request_log: Request log with consequences
            
        Returns:
            Impact score
        """
        base_score = 0.5
        
        # Count consequences
        consequences = self.db.query(RequestConsequence).filter(
            RequestConsequence.request_id == request_log.id
        ).all()
        
        if not consequences:
            return base_score
        
        # Calculate impact from consequences
        total_impact = 0.0
        for consequence in consequences:
            # Positive impact increases score, negative decreases
            if consequence.impact_type == "positive":
                total_impact += abs(consequence.impact_score)
            elif consequence.impact_type == "negative":
                total_impact -= abs(consequence.impact_score)
            else:
                total_impact += consequence.impact_score * 0.5  # Neutral has less impact
        
        # Normalize to 0.0-1.0 range
        impact_score = base_score + (total_impact / max(len(consequences), 1))
        impact_score = max(0.0, min(1.0, impact_score))  # Clamp to [0.0, 1.0]
        
        # Add bonus for number of entities created
        entity_count = 0
        if request_log.created_artifacts:
            entity_count += len(request_log.created_artifacts)
        if request_log.created_plans:
            entity_count += len(request_log.created_plans)
        if request_log.created_approvals:
            entity_count += len(request_log.created_approvals)
        if request_log.modified_artifacts:
            entity_count += len(request_log.modified_artifacts) * 1.5  # Modifications are more impactful
        
        # Add 0.1 per entity, capped at 0.3
        entity_bonus = min(0.3, entity_count * 0.1)
        impact_score = min(1.0, impact_score + entity_bonus)
        
        return impact_score
    
    def _calculate_overall_rank(self, request_log: RequestLog) -> float:
        """
        Calculate overall rank based on all scores (0.0-1.0)
        
        Args:
            request_log: Request log
            
        Returns:
            Overall rank
        """
        # Weights
        success_weight = 0.3
        importance_weight = 0.3
        impact_weight = 0.3
        recency_weight = 0.1
        
        # Calculate recency score (0.0-1.0)
        created_at = request_log.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - created_at).days
        recency_score = max(0.0, 1.0 - (days_old / 365.0))  # Loses relevance over a year
        
        # Calculate overall rank
        overall_rank = (
            request_log.success_score * success_weight +
            request_log.importance_score * importance_weight +
            request_log.impact_score * impact_weight +
            recency_score * recency_weight
        )
        
        return overall_rank
    
    def update_rank(self, request_id: UUID):
        """
        Update the overall rank for a request log
        
        Args:
            request_id: Request log ID
        """
        request_log = self.db.query(RequestLog).filter(RequestLog.id == request_id).first()
        if request_log:
            # Recalculate impact score
            request_log.impact_score = self._calculate_impact_score(request_log)
            
            # Recalculate overall rank
            request_log.overall_rank = self._calculate_overall_rank(request_log)
            
            request_log.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(request_log)

