"""
Page routes for project metrics web interface
"""
from app.core.database import get_db
from app.core.templates import templates
from app.services.project_metrics_service import ProjectMetricsService
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

router = APIRouter(tags=["project_metrics_pages"])


@router.get("/metrics/project", response_class=HTMLResponse)
async def project_metrics_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Project metrics dashboard page"""
    try:
        metrics_service = ProjectMetricsService(db)
        
        # Get overview for default period (30 days)
        overview = metrics_service.get_overview(days=30)
        
        # Get trends for key metrics
        from app.models.project_metric import MetricPeriod
        
        success_rate_trends = metrics_service.get_trends(
            metric_name="task_success_rate",
            days=30,
            period=MetricPeriod.DAY
        )
        
        execution_time_trends = metrics_service.get_trends(
            metric_name="task_execution_time",
            days=30,
            period=MetricPeriod.DAY
        )
        
        return templates.TemplateResponse(
            "project_metrics.html",
            {
                "request": request,
                "overview": overview,
                "success_rate_trends": success_rate_trends,
                "execution_time_trends": execution_time_trends
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading project metrics: {str(e)}")

