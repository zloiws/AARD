"""
API endpoints for logging management
"""
from typing import Dict, Optional

from app.core.logging_config import LoggingConfig
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/logging", tags=["logging"])


class LogLevelUpdate(BaseModel):
    """Request model for updating log level"""
    level: str = Field(..., description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")


class LogLevelResponse(BaseModel):
    """Response model for log level"""
    module: str
    level: str


class LogMetricsResponse(BaseModel):
    """Response model for log metrics"""
    metrics: Dict[str, int]
    total: int


@router.get("/levels", response_model=Dict[str, str])
async def get_log_levels():
    """Get current log levels for all modules"""
    levels = {}
    # Get levels for known modules
    known_modules = [
        "root",
        "app",
        "app.api",
        "app.services",
        "app.core",
        "sqlalchemy.engine",
        "uvicorn.access",
        "uvicorn.error",
    ]
    
    for module in known_modules:
        try:
            level = LoggingConfig.get_module_level(module)
            levels[module] = level
        except Exception:
            pass
    
    return levels


@router.get("/levels/{module:path}", response_model=LogLevelResponse)
async def get_module_log_level(module: str):
    """Get log level for a specific module"""
    try:
        level = LoggingConfig.get_module_level(module)
        return LogLevelResponse(module=module, level=level)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Module '{module}' not found: {str(e)}")


@router.put("/levels/{module:path}", response_model=LogLevelResponse)
async def set_module_log_level(module: str, level_update: LogLevelUpdate):
    """Set log level for a specific module"""
    level = level_update.level.upper()
    
    # Validate level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"]
    if level not in valid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid log level '{level}'. Valid levels: {', '.join(valid_levels)}"
        )
    
    try:
        LoggingConfig.set_module_level(module, level)
        return LogLevelResponse(module=module, level=level)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to set log level for module '{module}': {str(e)}"
        )


@router.get("/metrics", response_model=LogMetricsResponse)
async def get_log_metrics():
    """Get logging metrics (count of logs by level)"""
    metrics = LoggingConfig.get_metrics()
    total = sum(metrics.values())
    return LogMetricsResponse(metrics=metrics, total=total)


@router.post("/metrics/reset")
async def reset_log_metrics():
    """Reset logging metrics"""
    LoggingConfig.reset_metrics()
    return {"message": "Log metrics reset successfully"}

