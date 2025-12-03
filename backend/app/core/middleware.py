"""
FastAPI middleware for request context and logging
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_current_trace_id, get_current_span_id, add_span_attributes

logger = LoggingConfig.get_logger(__name__)


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context to logs"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request context and log request/response"""
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Set context for logging
        LoggingConfig.set_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        # Get trace_id from OpenTelemetry context (non-blocking)
        try:
            otel_trace_id = get_current_trace_id()
            if otel_trace_id:
                LoggingConfig.set_context(trace_id=otel_trace_id)
                try:
                    add_span_attributes(
                        request_id=request_id,
                        method=request.method,
                        path=request.url.path,
                    )
                except Exception:
                    # Ignore tracing errors - don't block requests
                    pass
        except Exception:
            # Ignore tracing errors - don't block requests
            pass
        
        # Also try to extract from headers (for external traces)
        header_trace_id = request.headers.get("x-trace-id") or request.headers.get("traceparent")
        if header_trace_id and not otel_trace_id:
            LoggingConfig.set_context(trace_id=header_trace_id)
        
        # Log request
        start_time = time.time()
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Update context with response info
            LoggingConfig.set_context(
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            
            # Log response
            logger.info(
                "Request completed",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration even on error
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            logger.error(
                "Request failed",
                exc_info=True,
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": duration_ms,
                }
            )
            
            # Re-raise exception
            raise
        
        finally:
            # Clear context after request
            LoggingConfig.clear_context()

