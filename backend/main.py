"""
Main FastAPI application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback
import sys
import logging

from app.core.config import get_settings
from app.core.logging_config import LoggingConfig
from app.api.routes import chat, pages, models, servers, approvals_pages

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
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}...")


# Create FastAPI app
# Settings loaded here to get app name
_settings = get_settings()
app = FastAPI(
    title=_settings.app_name,
    description="Autonomous Agentic Recursive Development Platform",
    version="0.1.0",
    lifespan=lifespan,
)

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
    
    logger.error(f"Unhandled exception: {error_msg}")
    logger.error(f"Traceback:\n{error_traceback}")
    
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

# Evolution system routers
from app.api.routes import approvals, artifacts, prompts
app.include_router(approvals.router)
app.include_router(artifacts.router)
app.include_router(prompts.router)

# Evolution system web pages
app.include_router(approvals_pages.router)
from app.api.routes import artifacts_pages
app.include_router(artifacts_pages.router)
from app.api.routes import settings_pages
app.include_router(settings_pages.router)
from app.api.routes import models_management
app.include_router(models_management.router)


@app.get("/")
async def root():
    """Root endpoint"""
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "environment": settings.app_env,
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
    )

