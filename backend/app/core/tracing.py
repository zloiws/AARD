"""
OpenTelemetry tracing configuration
"""
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from app.core.config import get_settings
from app.core.logging_config import LoggingConfig
from app.core.trace_exporter import DatabaseSpanExporter

logger = LoggingConfig.get_logger(__name__)

# Global tracer provider
_tracer_provider: Optional[TracerProvider] = None
_configured = False


def configure_tracing(app=None):
    """
    Configure OpenTelemetry tracing
    
    Args:
        app: FastAPI application instance (optional, for auto-instrumentation)
    """
    global _tracer_provider, _configured
    
    if _configured:
        return
    
    settings = get_settings()
    
    if not settings.enable_tracing:
        logger.info("OpenTelemetry tracing is disabled")
        return
    
    logger.info("Configuring OpenTelemetry tracing...")
    
    # Create resource with service name
    resource = Resource.create({
        "service.name": settings.tracing_service_name,
        "service.version": "0.1.0",
        "service.environment": settings.app_env,
    })
    
    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)
    
    # Configure exporter based on settings
    exporter = None
    
    if settings.tracing_exporter == "otlp":
        if settings.tracing_otlp_endpoint:
            exporter = OTLPSpanExporter(endpoint=settings.tracing_otlp_endpoint)
            logger.info(f"Using OTLP exporter: {settings.tracing_otlp_endpoint}")
        else:
            logger.warning("OTLP exporter selected but no endpoint configured, falling back to console")
            exporter = ConsoleSpanExporter()
    elif settings.tracing_exporter == "database":
        exporter = DatabaseSpanExporter()
        logger.info("Using database exporter for tracing")
    else:
        # Default: console exporter
        exporter = ConsoleSpanExporter()
        logger.info("Using console exporter for tracing")
    
    # Add span processor
    span_processor = BatchSpanProcessor(exporter)
    _tracer_provider.add_span_processor(span_processor)
    
    # Auto-instrument FastAPI if app is provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    
    # Auto-instrument SQLAlchemy
    try:
        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")
    
    # Auto-instrument HTTP clients
    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument HTTPX: {e}")
    
    try:
        AioHttpClientInstrumentor().instrument()
        logger.info("AioHTTP instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument AioHTTP: {e}")
    
    _configured = True
    logger.info("OpenTelemetry tracing configured successfully")


def get_tracer(name: str):
    """
    Get a tracer instance
    
    Args:
        name: Tracer name (usually module name)
    
    Returns:
        Tracer instance
    """
    if not _configured:
        configure_tracing()
    
    return trace.get_tracer(name)


def get_current_trace_id() -> Optional[str]:
    """
    Get current trace ID from context
    
    Returns:
        Trace ID as string or None if not in a trace
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, '032x')
    return None


def get_current_span_id() -> Optional[str]:
    """
    Get current span ID from context
    
    Returns:
        Span ID as string or None if not in a span
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, '016x')
    return None


def add_span_attributes(**kwargs):
    """
    Add attributes to current span
    
    Args:
        **kwargs: Attributes to add
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        for key, value in kwargs.items():
            span.set_attribute(key, value)


def shutdown_tracing():
    """
    Shutdown OpenTelemetry tracing
    
    This should be called during application shutdown to properly
    flush and close all spans and exporters.
    
    Note: Some spans may still be exported after shutdown during reload,
    which is normal and generates a harmless warning.
    """
    global _tracer_provider, _configured
    
    if not _configured or _tracer_provider is None:
        return
    
    try:
        logger.info("Shutting down OpenTelemetry tracing...")
        # Force flush all pending spans before shutdown
        try:
            _tracer_provider.force_flush(timeout_millis=5000)
        except Exception:
            pass  # Ignore flush errors during shutdown
        
        _tracer_provider.shutdown()
        logger.info("OpenTelemetry tracing shutdown complete")
    except Exception as e:
        logger.warning(f"Error during tracing shutdown: {e}")
    finally:
        _tracer_provider = None
        _configured = False

