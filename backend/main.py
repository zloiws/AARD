"""
Main FastAPI application entry point
"""
import warnings

# Suppress pkg_resources deprecation warning from opentelemetry
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*', category=UserWarning)
# Suppress Pydantic protected namespace warnings
warnings.filterwarnings('ignore', message='.*has conflict with protected namespace.*', category=UserWarning)
# Suppress OpenTelemetry shutdown warnings (spans dropped after shutdown is normal)
warnings.filterwarnings('ignore', message='.*Already shutdown.*', category=UserWarning)

import logging
import sys
import traceback
from contextlib import asynccontextmanager

from app.api.routes import (agent_dialogs, agent_gym, agent_gym_pages,
                            agent_memory, agents, agents_pages,
                            approvals_pages, artifacts_pages, audit_reports,
                            audit_reports_pages, auth, auth_pages, benchmarks,
                            chat, checkpoints, current_work, events, execution,
                            execution_graph, experiments, health)
from app.api.routes import logging as logging_routes
from app.api.routes import (meta, metrics, model_logs, models,
                            models_management, pages, plan_templates,
                            plans_pages, project_metrics,
                            project_metrics_pages, queues, registry, requests,
                            servers, settings_pages, tools, tools_pages,
                            traces, traces_pages, websocket_events, workflow)
from app.core.config import get_settings
from app.core.logging_config import LoggingConfig
from app.core.middleware import LoggingContextMiddleware
from app.core.tracing import configure_tracing, shutdown_tracing
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging first
LoggingConfig.configure()

# Get logger for this module
logger = LoggingConfig.get_logger(__name__)

# Settings will be loaded lazily when needed


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI app"""
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode...")
    configure_tracing(app)
    
    # Start agent heartbeat monitor
    from app.services.agent_heartbeat_background import get_heartbeat_monitor
    heartbeat_monitor = get_heartbeat_monitor()
    await heartbeat_monitor.start()
    
    # Start audit scheduler
    from app.services.audit_scheduler import get_audit_scheduler
    audit_scheduler = get_audit_scheduler()
    await audit_scheduler.start()
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}...")
    
    # Stop audit scheduler
    await audit_scheduler.stop()
    
    # Stop heartbeat monitor
    await heartbeat_monitor.stop()
    
    # Shutdown tracing
    shutdown_tracing()


# Create FastAPI app
# Settings loaded here to get app name
_settings = get_settings()
app = FastAPI(
    title=_settings.app_name,
    description="Personal human-AI interaction environment (AARD)",
    version="0.1.0",
    lifespan=lifespan,
)

# OpenTelemetry tracing is configured in lifespan startup

# Add logging context middleware (before CORS to capture all requests)
app.add_middleware(LoggingContextMiddleware)
# Add metrics middleware
from app.core.middleware_metrics import MetricsMiddleware

app.add_middleware(MetricsMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handler for better error logging (only for unhandled exceptions)
from fastapi.exceptions import HTTPException as FastAPIHTTPException


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to log all unhandled errors"""
    # Don't handle HTTPException - let FastAPI handle it
    if isinstance(exc, FastAPIHTTPException):
        raise exc
    
    import traceback
    error_traceback = traceback.format_exc()
    error_msg = str(exc)
    
    logger.error(
        "Unhandled exception",
        exc_info=True,
        extra={
            "error": error_msg,
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": error_msg,
            "type": type(exc).__name__
        }
    )

# Include routers
app.include_router(pages.router)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(servers.router)
app.include_router(logging_routes.router)
app.include_router(traces.router)
app.include_router(requests.router)
app.include_router(queues.router)
app.include_router(checkpoints.router)
app.include_router(metrics.router)
app.include_router(health.router)
app.include_router(agents.router)
app.include_router(tools.router)
app.include_router(agent_dialogs.router)

# A2A communication
from app.api.routes import a2a

app.include_router(a2a.router)

# Evolution system routers
from app.api.routes import (approvals, artifacts, model_logs, plans,
                            project_metrics, prompts)

app.include_router(approvals.router)
app.include_router(artifacts.router)
app.include_router(prompts.router)
app.include_router(plans.router)
app.include_router(plan_templates.router)
app.include_router(model_logs.router)
app.include_router(project_metrics.router)
app.include_router(registry.router)
app.include_router(project_metrics_pages.router)
app.include_router(audit_reports.router)
app.include_router(audit_reports_pages.router)
from app.api.routes import benchmarks

app.include_router(benchmarks.router)
from app.api.routes import benchmarks_pages

app.include_router(benchmarks_pages.router)
app.include_router(current_work.router)
app.include_router(workflow.router)
app.include_router(websocket_events.router)
app.include_router(events.router)

# Evolution system web pages
app.include_router(approvals_pages.router)
app.include_router(artifacts_pages.router)
app.include_router(settings_pages.router)
app.include_router(models_management.router)
app.include_router(plans_pages.router)
app.include_router(agents_pages.router)
app.include_router(tools_pages.router)
app.include_router(traces_pages.router)

# Dashboard
from app.api.routes import dashboard, dashboard_pages

app.include_router(dashboard.router)
app.include_router(dashboard_pages.router)
app.include_router(experiments.router)
app.include_router(agent_gym.router)
app.include_router(agent_gym_pages.router)
app.include_router(agent_memory.router)
app.include_router(auth.router)
app.include_router(auth_pages.router)


@app.get("/api")
async def root():
    """Root API endpoint"""
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "environment": settings.app_env,
    }


# Health check endpoints are in app.api.routes.health


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
    )

