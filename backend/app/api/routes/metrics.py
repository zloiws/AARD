"""
Prometheus metrics endpoint
"""
from app.core.logging_config import LoggingConfig
from app.core.metrics import get_metrics, get_metrics_content_type
from fastapi import APIRouter
from fastapi.responses import Response

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    
    Returns metrics in Prometheus text format
    """
    try:
        metrics_data = get_metrics()
        return Response(
            content=metrics_data,
            media_type=get_metrics_content_type()
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        return Response(
            content="# Error generating metrics\n",
            media_type="text/plain",
            status_code=500
        )

