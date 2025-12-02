"""
OpenTelemetry database exporter for execution traces
"""
from typing import Optional, List
from datetime import datetime
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode

from app.core.database import SessionLocal
from app.models.trace import ExecutionTrace
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class DatabaseSpanExporter(SpanExporter):
    """
    Exports OpenTelemetry spans to PostgreSQL database
    """
    
    def __init__(self):
        """Initialize database exporter"""
        super().__init__()
        logger.info("DatabaseSpanExporter initialized")
    
    def export(self, spans: List[ReadableSpan]) -> SpanExportResult:
        """
        Export spans to database
        
        Args:
            spans: List of spans to export
        
        Returns:
            SpanExportResult indicating success or failure
        """
        if not spans:
            return SpanExportResult.SUCCESS
        
        db = SessionLocal()
        try:
            for span in spans:
                try:
                    self._export_span(span, db)
                except Exception as e:
                    logger.error(
                        f"Failed to export span {span.context.span_id}: {e}",
                        exc_info=True
                    )
                    # Continue with other spans even if one fails
            
            db.commit()
            logger.debug(f"Exported {len(spans)} spans to database")
            return SpanExportResult.SUCCESS
            
        except Exception as e:
            logger.error(f"Failed to export spans to database: {e}", exc_info=True)
            db.rollback()
            return SpanExportResult.FAILURE
        finally:
            db.close()
    
    def _export_span(self, span: ReadableSpan, db):
        """
        Export a single span to database
        
        Args:
            span: Span to export
            db: Database session
        """
        # Convert trace_id and span_id to hex strings
        trace_id = format(span.context.trace_id, '032x')
        span_id = format(span.context.span_id, '016x')
        parent_span_id = None
        if span.parent and span.parent.span_id:
            parent_span_id = format(span.parent.span_id, '016x')
        
        # Determine status
        status = None
        error_message = None
        error_type = None
        
        if span.status.status_code == StatusCode.ERROR:
            status = "error"
            if span.status.description:
                error_message = span.status.description
            # Try to extract error type from attributes
            if span.attributes:
                error_type = span.attributes.get("error.type") or span.attributes.get("exception.type")
        elif span.status.status_code == StatusCode.OK:
            status = "success"
        else:
            status = "timeout"  # or unknown
        
        # Calculate duration
        duration_ms = None
        if span.end_time and span.start_time:
            duration_ns = span.end_time - span.start_time
            duration_ms = int(duration_ns / 1_000_000)  # Convert nanoseconds to milliseconds
        
        # Extract attributes
        attributes = {}
        if span.attributes:
            # Convert attributes to JSON-serializable format
            for key, value in span.attributes.items():
                # Skip non-serializable values
                try:
                    if isinstance(value, (str, int, float, bool, type(None))):
                        attributes[key] = value
                    elif isinstance(value, (list, dict)):
                        attributes[key] = value
                    else:
                        attributes[key] = str(value)
                except Exception:
                    pass
        
        # Extract task_id, plan_id, agent_id, tool_id from attributes
        task_id = attributes.get("task_id")
        plan_id = attributes.get("plan_id")
        agent_id = attributes.get("agent_id")
        tool_id = attributes.get("tool_id")
        
        # Convert string UUIDs to UUID objects if needed
        from uuid import UUID as UUIDType
        if task_id and isinstance(task_id, str):
            try:
                task_id = UUIDType(task_id)
            except ValueError:
                task_id = None
        if plan_id and isinstance(plan_id, str):
            try:
                plan_id = UUIDType(plan_id)
            except ValueError:
                plan_id = None
        if agent_id and isinstance(agent_id, str):
            try:
                agent_id = UUIDType(agent_id)
            except ValueError:
                agent_id = None
        if tool_id and isinstance(tool_id, str):
            try:
                tool_id = UUIDType(tool_id)
            except ValueError:
                tool_id = None
        
        # Convert timestamps
        start_time = datetime.fromtimestamp(span.start_time / 1_000_000_000)  # Nanoseconds to seconds
        end_time = None
        if span.end_time:
            end_time = datetime.fromtimestamp(span.end_time / 1_000_000_000)
        
        # Check if trace already exists (avoid duplicates)
        existing = db.query(ExecutionTrace).filter(
            ExecutionTrace.trace_id == trace_id,
            ExecutionTrace.span_id == span_id
        ).first()
        
        if existing:
            # Update existing trace
            existing.operation_name = span.name
            existing.start_time = start_time
            existing.end_time = end_time
            existing.duration_ms = duration_ms
            existing.status = status
            existing.attributes = attributes
            existing.task_id = task_id
            existing.plan_id = plan_id
            existing.agent_id = agent_id
            existing.tool_id = tool_id
            existing.error_message = error_message
            existing.error_type = error_type
        else:
            # Create new trace
            trace = ExecutionTrace(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                operation_name=span.name,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                status=status,
                attributes=attributes,
                task_id=task_id,
                plan_id=plan_id,
                agent_id=agent_id,
                tool_id=tool_id,
                error_message=error_message,
                error_type=error_type,
            )
            db.add(trace)
    
    def shutdown(self):
        """Shutdown the exporter"""
        logger.info("DatabaseSpanExporter shutdown")

