"""
API routes for execution traces
"""
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.models.trace import ExecutionTrace
from app.core.logging_config import LoggingConfig
from pydantic import BaseModel

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(prefix="/api/traces", tags=["traces"])


class TraceResponse(BaseModel):
    """Trace response model"""
    id: str
    trace_id: str
    task_id: Optional[str]
    plan_id: Optional[str]
    span_id: Optional[str]
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[int]
    status: Optional[str]
    attributes: Optional[dict]
    agent_id: Optional[str]
    tool_id: Optional[str]
    error_message: Optional[str]
    error_type: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TraceListResponse(BaseModel):
    """Trace list response model"""
    traces: List[TraceResponse]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=TraceListResponse)
async def list_traces(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    plan_id: Optional[str] = Query(None, description="Filter by plan ID"),
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    operation_name: Optional[str] = Query(None, description="Filter by operation name"),
    start_time_from: Optional[datetime] = Query(None, description="Filter traces from this time"),
    start_time_to: Optional[datetime] = Query(None, description="Filter traces to this time"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    """
    List execution traces with filters
    """
    try:
        # Build query
        query = db.query(ExecutionTrace)
        
        # Apply filters
        if task_id:
            try:
                task_uuid = UUID(task_id)
                query = query.filter(ExecutionTrace.task_id == task_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid task_id format")
        
        if plan_id:
            try:
                plan_uuid = UUID(plan_id)
                query = query.filter(ExecutionTrace.plan_id == plan_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid plan_id format")
        
        if trace_id:
            query = query.filter(ExecutionTrace.trace_id == trace_id)
        
        if status:
            query = query.filter(ExecutionTrace.status == status.lower())
        
        if operation_name:
            query = query.filter(ExecutionTrace.operation_name.ilike(f"%{operation_name}%"))
        
        if start_time_from:
            query = query.filter(ExecutionTrace.start_time >= start_time_from)
        
        if start_time_to:
            query = query.filter(ExecutionTrace.start_time <= start_time_to)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        traces = query.order_by(ExecutionTrace.start_time.desc()).offset(offset).limit(page_size).all()
        
        # Convert to response models
        trace_responses = [
            TraceResponse(
                id=str(trace.id),
                trace_id=trace.trace_id,
                task_id=str(trace.task_id) if trace.task_id else None,
                plan_id=str(trace.plan_id) if trace.plan_id else None,
                span_id=trace.span_id,
                parent_span_id=trace.parent_span_id,
                operation_name=trace.operation_name,
                start_time=trace.start_time,
                end_time=trace.end_time,
                duration_ms=trace.duration_ms,
                status=trace.status,
                attributes=trace.attributes,
                agent_id=str(trace.agent_id) if trace.agent_id else None,
                tool_id=str(trace.tool_id) if trace.tool_id else None,
                error_message=trace.error_message,
                error_type=trace.error_type,
                created_at=trace.created_at,
            )
            for trace in traces
        ]
        
        return TraceListResponse(
            traces=trace_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing traces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a single trace by trace_id
    """
    try:
        trace = db.query(ExecutionTrace).filter(ExecutionTrace.trace_id == trace_id).first()
        
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        return TraceResponse(
            id=str(trace.id),
            trace_id=trace.trace_id,
            task_id=str(trace.task_id) if trace.task_id else None,
            plan_id=str(trace.plan_id) if trace.plan_id else None,
            span_id=trace.span_id,
            parent_span_id=trace.parent_span_id,
            operation_name=trace.operation_name,
            start_time=trace.start_time,
            end_time=trace.end_time,
            duration_ms=trace.duration_ms,
            status=trace.status,
            attributes=trace.attributes,
            agent_id=str(trace.agent_id) if trace.agent_id else None,
            tool_id=str(trace.tool_id) if trace.tool_id else None,
            error_message=trace.error_message,
            error_type=trace.error_type,
            created_at=trace.created_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trace_id}/spans", response_model=List[TraceResponse])
async def get_trace_spans(
    trace_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all spans for a trace
    """
    try:
        traces = db.query(ExecutionTrace).filter(
            ExecutionTrace.trace_id == trace_id
        ).order_by(ExecutionTrace.start_time.asc()).all()
        
        if not traces:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        return [
            TraceResponse(
                id=str(trace.id),
                trace_id=trace.trace_id,
                task_id=str(trace.task_id) if trace.task_id else None,
                plan_id=str(trace.plan_id) if trace.plan_id else None,
                span_id=trace.span_id,
                parent_span_id=trace.parent_span_id,
                operation_name=trace.operation_name,
                start_time=trace.start_time,
                end_time=trace.end_time,
                duration_ms=trace.duration_ms,
                status=trace.status,
                attributes=trace.attributes,
                agent_id=str(trace.agent_id) if trace.agent_id else None,
                tool_id=str(trace.tool_id) if trace.tool_id else None,
                error_message=trace.error_message,
                error_type=trace.error_type,
                created_at=trace.created_at,
            )
            for trace in traces
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace spans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_trace_stats(
    start_time_from: Optional[datetime] = Query(None, description="Filter from this time"),
    start_time_to: Optional[datetime] = Query(None, description="Filter to this time"),
    db: Session = Depends(get_db)
):
    """
    Get trace statistics
    """
    try:
        query = db.query(ExecutionTrace)
        
        if start_time_from:
            query = query.filter(ExecutionTrace.start_time >= start_time_from)
        
        if start_time_to:
            query = query.filter(ExecutionTrace.start_time <= start_time_to)
        
        total = query.count()
        success = query.filter(ExecutionTrace.status == "success").count()
        error = query.filter(ExecutionTrace.status == "error").count()
        timeout = query.filter(ExecutionTrace.status == "timeout").count()
        
        # Average duration - calculate manually
        traces_with_duration = query.filter(
            ExecutionTrace.duration_ms.isnot(None)
        ).all()
        
        if traces_with_duration:
            avg_duration = sum(t.duration_ms for t in traces_with_duration) / len(traces_with_duration)
        else:
            avg_duration = 0
        
        return {
            "total": total,
            "success": success,
            "error": error,
            "timeout": timeout,
            "avg_duration_ms": int(avg_duration) if avg_duration else 0,
        }
        
    except Exception as e:
        logger.error(f"Error getting trace stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

