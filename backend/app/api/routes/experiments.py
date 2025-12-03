"""
API routes for agent A/B testing experiments
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.services.agent_experiment_service import AgentExperimentService
from app.models.agent_experiment import AgentExperiment, ExperimentResult, ExperimentStatus

logger = LoggingConfig.get_logger(__name__)
router = APIRouter(prefix="/api/experiments", tags=["experiments"])


class ExperimentCreate(BaseModel):
    name: str
    agent_a_id: UUID
    agent_b_id: UUID
    description: Optional[str] = None
    traffic_split: float = Field(0.5, ge=0.0, le=1.0)
    primary_metric: Optional[str] = None
    success_threshold: Optional[float] = None
    min_samples_per_variant: int = Field(100, ge=1)
    max_samples_per_variant: Optional[int] = None
    max_duration_hours: Optional[int] = None
    metrics_to_track: Optional[List[str]] = None
    confidence_level: float = Field(0.95, ge=0.0, le=1.0)
    created_by: Optional[str] = None


class ExperimentResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    agent_a_id: UUID
    agent_b_id: UUID
    status: str
    traffic_split: float
    primary_metric: Optional[str]
    success_threshold: Optional[float]
    min_samples_per_variant: int
    max_samples_per_variant: Optional[int]
    max_duration_hours: Optional[int]
    metrics_to_track: Optional[List[str]]
    confidence_level: float
    agent_a_samples: int
    agent_b_samples: int
    agent_a_metrics: Optional[Dict[str, Any]]
    agent_b_metrics: Optional[Dict[str, Any]]
    p_value: Optional[float]
    is_significant: Optional[bool]
    winner: Optional[UUID]
    start_date: Optional[str]
    end_date: Optional[str]
    created_by: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ResultCreate(BaseModel):
    agent_id: UUID
    variant: str = Field(..., pattern="^[AB]$")
    success: Optional[bool] = None
    execution_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    error_message: Optional[str] = None
    task_id: Optional[UUID] = None
    task_description: Optional[str] = None
    custom_metrics: Optional[Dict[str, Any]] = None
    user_feedback: Optional[str] = None


class ResultResponse(BaseModel):
    id: UUID
    experiment_id: UUID
    agent_id: UUID
    variant: str
    task_id: Optional[UUID]
    task_description: Optional[str]
    success: Optional[bool]
    execution_time_ms: Optional[int]
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    quality_score: Optional[float]
    error_message: Optional[str]
    custom_metrics: Optional[Dict[str, Any]]
    user_feedback: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    experiment: ExperimentCreate,
    db: Session = Depends(get_db)
):
    """Create a new A/B testing experiment"""
    try:
        service = AgentExperimentService(db)
        created = service.create_experiment(
            name=experiment.name,
            agent_a_id=experiment.agent_a_id,
            agent_b_id=experiment.agent_b_id,
            description=experiment.description,
            traffic_split=experiment.traffic_split,
            primary_metric=experiment.primary_metric,
            success_threshold=experiment.success_threshold,
            min_samples_per_variant=experiment.min_samples_per_variant,
            max_samples_per_variant=experiment.max_samples_per_variant,
            max_duration_hours=experiment.max_duration_hours,
            metrics_to_track=experiment.metrics_to_track,
            confidence_level=experiment.confidence_level,
            created_by=experiment.created_by
        )
        return ExperimentResponse(**created.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating experiment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[ExperimentResponse])
async def list_experiments(
    status: Optional[ExperimentStatus] = None,
    agent_id: Optional[UUID] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List experiments with optional filters"""
    try:
        service = AgentExperimentService(db)
        experiments = service.list_experiments(
            status=status,
            agent_id=agent_id,
            limit=limit
        )
        return [ExperimentResponse(**exp.__dict__) for exp in experiments]
    except Exception as e:
        logger.error(f"Error listing experiments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: UUID,
    db: Session = Depends(get_db)
):
    """Get experiment by ID"""
    try:
        service = AgentExperimentService(db)
        experiment = service.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return ExperimentResponse(**experiment.__dict__)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting experiment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(
    experiment_id: UUID,
    db: Session = Depends(get_db)
):
    """Start an experiment"""
    try:
        service = AgentExperimentService(db)
        experiment = service.start_experiment(experiment_id)
        return ExperimentResponse(**experiment.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting experiment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{experiment_id}/complete", response_model=ExperimentResponse)
async def complete_experiment(
    experiment_id: UUID,
    db: Session = Depends(get_db)
):
    """Complete an experiment"""
    try:
        service = AgentExperimentService(db)
        experiment = service.complete_experiment(experiment_id)
        return ExperimentResponse(**experiment.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error completing experiment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{experiment_id}/select-variant", response_model=Dict[str, Any])
async def select_variant(
    experiment_id: UUID,
    db: Session = Depends(get_db)
):
    """Select which agent variant to use for a task"""
    try:
        service = AgentExperimentService(db)
        agent_id, variant = service.select_variant(experiment_id)
        return {
            "agent_id": str(agent_id),
            "variant": variant,
            "experiment_id": str(experiment_id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error selecting variant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{experiment_id}/results", response_model=ResultResponse, status_code=status.HTTP_201_CREATED)
async def record_result(
    experiment_id: UUID,
    result: ResultCreate,
    db: Session = Depends(get_db)
):
    """Record a result for an experiment"""
    try:
        service = AgentExperimentService(db)
        created = service.record_result(
            experiment_id=experiment_id,
            agent_id=result.agent_id,
            variant=result.variant,
            success=result.success,
            execution_time_ms=result.execution_time_ms,
            tokens_used=result.tokens_used,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
            error_message=result.error_message,
            task_id=result.task_id,
            task_description=result.task_description,
            custom_metrics=result.custom_metrics,
            user_feedback=result.user_feedback
        )
        return ResultResponse(**created.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error recording result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{experiment_id}/results", response_model=List[ResultResponse])
async def get_experiment_results(
    experiment_id: UUID,
    variant: Optional[str] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get results for an experiment"""
    try:
        service = AgentExperimentService(db)
        results = service.get_experiment_results(
            experiment_id=experiment_id,
            variant=variant,
            limit=limit
        )
        return [ResultResponse(**r.__dict__) for r in results]
    except Exception as e:
        logger.error(f"Error getting results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

