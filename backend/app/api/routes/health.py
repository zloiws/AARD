"""
Health check endpoints
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
import asyncio

from app.core.database import get_db
from app.core.config import get_settings
from app.core.logging_config import LoggingConfig
from app.services.ollama_service import OllamaService
from app.models.task_queue import TaskQueue, QueueTask
from app.models.checkpoint import Checkpoint
from app.models.trace import ExecutionTrace
from datetime import datetime, timedelta

logger = LoggingConfig.get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Basic health check endpoint
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AARD"
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with component status
    
    Returns:
        dict: Detailed health status of all components
    """
    settings = get_settings()
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env,
        "components": {}
    }
    
    overall_healthy = True
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        db.commit()
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        overall_healthy = False
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
            "error": type(e).__name__
        }
    
    # Check Ollama servers
    try:
        servers = OllamaService.get_all_active_servers(db)
        server_statuses = []
        all_servers_healthy = True
        
        for server in servers:
            server_status = {
                "id": str(server.id),
                "name": server.name,
                "url": server.url,
                "is_available": server.is_available,
                "is_default": server.is_default
            }
            
            # Try to check server health
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    base_url = server.url
                    if base_url.endswith("/v1"):
                        base_url = base_url[:-3]
                    elif base_url.endswith("/v1/"):
                        base_url = base_url[:-4]
                    
                    response = await client.get(f"{base_url}/api/tags", timeout=5.0)
                    server_status["reachable"] = response.status_code == 200
                    if not server_status["reachable"]:
                        all_servers_healthy = False
            except Exception as e:
                server_status["reachable"] = False
                server_status["error"] = str(e)
                all_servers_healthy = False
            
            server_statuses.append(server_status)
        
        if not servers:
            health_status["components"]["ollama_servers"] = {
                "status": "warning",
                "message": "No Ollama servers configured",
                "servers": []
            }
        elif all_servers_healthy:
            health_status["components"]["ollama_servers"] = {
                "status": "healthy",
                "message": f"All {len(servers)} servers are available",
                "servers": server_statuses
            }
        else:
            overall_healthy = False
            health_status["components"]["ollama_servers"] = {
                "status": "degraded",
                "message": "Some servers are unavailable",
                "servers": server_statuses
            }
    except Exception as e:
        overall_healthy = False
        health_status["components"]["ollama_servers"] = {
            "status": "error",
            "message": f"Failed to check Ollama servers: {str(e)}",
            "error": type(e).__name__
        }
    
    # Check task queues
    try:
        queues = db.query(TaskQueue).filter(TaskQueue.is_active == True).all()
        queue_statuses = []
        
        for queue in queues:
            pending_count = db.query(QueueTask).filter(
                QueueTask.queue_id == queue.id,
                QueueTask.status == "pending"
            ).count()
            
            processing_count = db.query(QueueTask).filter(
                QueueTask.queue_id == queue.id,
                QueueTask.status == "processing"
            ).count()
            
            failed_count = db.query(QueueTask).filter(
                QueueTask.queue_id == queue.id,
                QueueTask.status == "failed"
            ).count()
            
            queue_statuses.append({
                "id": str(queue.id),
                "name": queue.name,
                "pending": pending_count,
                "processing": processing_count,
                "failed": failed_count,
                "total": pending_count + processing_count + failed_count
            })
        
        if queue_statuses:
            total_pending = sum(q["pending"] for q in queue_statuses)
            total_failed = sum(q["failed"] for q in queue_statuses)
            
            if total_failed > 100:  # Threshold for unhealthy
                overall_healthy = False
                status = "unhealthy"
                message = f"High number of failed tasks: {total_failed}"
            elif total_pending > 1000:  # Threshold for degraded
                status = "degraded"
                message = f"High queue backlog: {total_pending} pending tasks"
            else:
                status = "healthy"
                message = f"Queues operating normally"
            
            health_status["components"]["task_queues"] = {
                "status": status,
                "message": message,
                "queues": queue_statuses,
                "summary": {
                    "total_pending": total_pending,
                    "total_processing": sum(q["processing"] for q in queue_statuses),
                    "total_failed": total_failed
                }
            }
        else:
            health_status["components"]["task_queues"] = {
                "status": "healthy",
                "message": "No active queues",
                "queues": []
            }
    except Exception as e:
        health_status["components"]["task_queues"] = {
            "status": "error",
            "message": f"Failed to check queues: {str(e)}",
            "error": type(e).__name__
        }
    
    # Check recent activity (traces in last 5 minutes)
    try:
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        recent_traces = db.query(ExecutionTrace).filter(
            ExecutionTrace.start_time >= five_minutes_ago
        ).count()
        
        recent_errors = db.query(ExecutionTrace).filter(
            ExecutionTrace.start_time >= five_minutes_ago,
            ExecutionTrace.status == "error"
        ).count()
        
        error_rate = recent_errors / recent_traces if recent_traces > 0 else 0
        
        if error_rate > 0.5:  # More than 50% errors
            overall_healthy = False
            status = "unhealthy"
        elif error_rate > 0.2:  # More than 20% errors
            status = "degraded"
        else:
            status = "healthy"
        
        health_status["components"]["recent_activity"] = {
            "status": status,
            "message": f"{recent_traces} traces in last 5 minutes, {recent_errors} errors",
            "traces_last_5min": recent_traces,
            "errors_last_5min": recent_errors,
            "error_rate": round(error_rate, 3)
        }
    except Exception as e:
        health_status["components"]["recent_activity"] = {
            "status": "error",
            "message": f"Failed to check activity: {str(e)}",
            "error": type(e).__name__
        }
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    elif any(comp.get("status") == "degraded" for comp in health_status["components"].values()):
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/health/readiness")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - is the service ready to accept traffic?
    
    Returns:
        dict: Readiness status
    """
    try:
        # Check database
        db.execute(text("SELECT 1"))
        db.commit()
        
        # Check if at least one Ollama server is available
        servers = OllamaService.get_all_active_servers(db)
        if not servers:
            return {
                "status": "not_ready",
                "message": "No Ollama servers configured",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Check if at least one server is available
        available_servers = [s for s in servers if s.is_available]
        if not available_servers:
            return {
                "status": "not_ready",
                "message": "No available Ollama servers",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "ready",
            "message": "Service is ready to accept traffic",
            "timestamp": datetime.utcnow().isoformat(),
            "available_servers": len(available_servers)
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        return {
            "status": "not_ready",
            "message": f"Service is not ready: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "error": type(e).__name__
        }


@router.get("/health/liveness")
async def liveness_check():
    """
    Liveness check - is the service alive?
    
    Returns:
        dict: Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }

