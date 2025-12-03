"""
Middleware for collecting HTTP request metrics
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_errors_total
)
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics for Prometheus
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and collect metrics
        """
        start_time = time.time()
        
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error_type = None
        except Exception as e:
            status_code = 500
            error_type = type(e).__name__
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Extract endpoint (simplify path for metrics)
            endpoint = request.url.path
            # Remove UUIDs and IDs from path for better aggregation
            if endpoint.startswith("/api/"):
                # Keep API structure but simplify IDs
                parts = endpoint.split("/")
                if len(parts) > 3:
                    # Replace UUIDs with {id}
                    for i, part in enumerate(parts):
                        if len(part) == 36 and part.count("-") == 4:  # UUID format
                            parts[i] = "{id}"
                    endpoint = "/".join(parts)
            
            # Record metrics
            method = request.method
            status_code_str = str(status_code)
            
            # Increment request counter
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code_str
            ).inc()
            
            # Record duration
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code_str
            ).observe(duration)
            
            # Record errors
            if status_code >= 400:
                http_errors_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code_str,
                    error_type=error_type or f"http_{status_code}"
                ).inc()
        
        return response

