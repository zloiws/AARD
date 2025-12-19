"""
API routes for project metrics
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.project_metric import MetricPeriod, MetricType
from app.services.project_metrics_service import ProjectMetricsService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/metrics/project", tags=["project_metrics"])
logger = LoggingConfig.get_logger(__name__)


class MetricResponse(BaseModel):
    """Response model for a single metric"""
    id: str
    metric_type: str
    metric_name: str
    period: str
    period_start: str
    period_end: str
    value: Optional[float]
    count: int
    min_value: Optional[float]
    max_value: Optional[float]
    sum_value: Optional[float]
    metadata: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


class OverviewResponse(BaseModel):
    """Response model for project metrics overview"""
    period: Dict[str, Any]
    performance: Dict[str, Any]
    distribution: Dict[str, Any]
    plans: Dict[str, Any]
    recent_metrics: List[Dict[str, Any]]


class TrendResponse(BaseModel):
    """Response model for metric trends"""
    metric_name: str
    metric_type: Optional[str]
    period: str
    days: int
    data_points: List[Dict[str, Any]]


class ComparisonResponse(BaseModel):
    """Response model for period comparison"""
    period1: Dict[str, Any]
    period2: Dict[str, Any]
    changes: Dict[str, Any]


@router.get("/overview", response_model=OverviewResponse)
async def get_project_overview(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get overview of project metrics
    
    Returns:
        Overview with performance metrics, task distribution, plans statistics, and recent metrics
    """
    try:
        service = ProjectMetricsService(db)
        overview = service.get_overview(days=days)
        
        if not overview:
            raise HTTPException(status_code=500, detail="Failed to get overview")
        
        return OverviewResponse(**overview)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends", response_model=TrendResponse)
async def get_metric_trends(
    metric_name: str = Query(..., description="Name of the metric to get trends for"),
    metric_type: Optional[str] = Query(None, description="Optional metric type filter"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    period: str = Query(default="day", description="Aggregation period (hour, day, week, month)"),
    db: Session = Depends(get_db)
):
    """
    Get trends for a specific metric
    
    Args:
        metric_name: Name of the metric (e.g., "task_success_rate", "avg_execution_time")
        metric_type: Optional metric type filter
        days: Number of days to analyze
        period: Aggregation period (hour, day, week, month)
    
    Returns:
        Trend data with metric values over time
    """
    try:
        # Validate period
        try:
            period_enum = MetricPeriod(period.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period: {period}. Must be one of: hour, day, week, month"
            )
        
        # Validate metric_type if provided
        metric_type_enum = None
        if metric_type:
            try:
                metric_type_enum = MetricType(metric_type.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid metric_type: {metric_type}. Must be one of: performance, task_success, execution_time, task_distribution, trend, aggregate"
                )
        
        service = ProjectMetricsService(db)
        trends = service.get_trends(
            metric_name=metric_name,
            metric_type=metric_type_enum,
            days=days,
            period=period_enum
        )
        
        return TrendResponse(
            metric_name=metric_name,
            metric_type=metric_type,
            period=period,
            days=days,
            data_points=trends
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metric trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison", response_model=ComparisonResponse)
async def compare_periods(
    period1_start: str = Query(..., description="Start of first period (ISO format)"),
    period1_end: str = Query(..., description="End of first period (ISO format)"),
    period2_start: str = Query(..., description="Start of second period (ISO format)"),
    period2_end: str = Query(..., description="End of second period (ISO format)"),
    db: Session = Depends(get_db)
):
    """
    Compare metrics between two periods
    
    Args:
        period1_start: Start of first period (ISO format datetime)
        period1_end: End of first period (ISO format datetime)
        period2_start: Start of second period (ISO format datetime)
        period2_end: End of second period (ISO format datetime)
    
    Returns:
        Comparison data with metrics for both periods and calculated changes
    """
    try:
        # Parse datetime strings
        try:
            p1_start = datetime.fromisoformat(period1_start.replace('Z', '+00:00'))
            p1_end = datetime.fromisoformat(period1_end.replace('Z', '+00:00'))
            p2_start = datetime.fromisoformat(period2_start.replace('Z', '+00:00'))
            p2_end = datetime.fromisoformat(period2_end.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid datetime format: {e}. Use ISO format (e.g., 2025-12-01T00:00:00Z)"
            )
        
        # Validate periods
        if p1_start >= p1_end:
            raise HTTPException(
                status_code=400,
                detail="period1_start must be before period1_end"
            )
        
        if p2_start >= p2_end:
            raise HTTPException(
                status_code=400,
                detail="period2_start must be before period2_end"
            )
        
        service = ProjectMetricsService(db)
        comparison = service.compare_periods(
            period1_start=p1_start,
            period1_end=p1_end,
            period2_start=p2_start,
            period2_end=p2_end
        )
        
        if not comparison:
            raise HTTPException(status_code=500, detail="Failed to compare periods")
        
        return ComparisonResponse(**comparison)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing periods: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=List[MetricResponse])
async def list_metrics(
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    period: Optional[str] = Query(None, description="Filter by period"),
    limit: int = Query(default=100, ge=1, le=1000, description="Limit number of results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    List project metrics with optional filtering
    
    Args:
        metric_type: Optional metric type filter
        metric_name: Optional metric name filter
        period: Optional period filter
        limit: Maximum number of results
        offset: Offset for pagination
    
    Returns:
        List of metrics matching the filters
    """
    try:
        from app.models.project_metric import ProjectMetric
        from sqlalchemy import and_
        
        query = db.query(ProjectMetric)
        
        # Apply filters
        if metric_type:
            try:
                metric_type_enum = MetricType(metric_type.upper())
                query = query.filter(ProjectMetric.metric_type == metric_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid metric_type: {metric_type}"
                )
        
        if metric_name:
            query = query.filter(ProjectMetric.metric_name == metric_name)
        
        if period:
            try:
                period_enum = MetricPeriod(period.upper())
                query = query.filter(ProjectMetric.period == period_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid period: {period}"
                )
        
        # Order by period_start descending (most recent first)
        query = query.order_by(ProjectMetric.period_start.desc())
        
        # Apply pagination
        metrics = query.offset(offset).limit(limit).all()
        
        return [MetricResponse(**m.to_dict()) for m in metrics]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

