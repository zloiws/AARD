"""
Page routes for traces web interface
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.core.templates import templates
from app.models.trace import ExecutionTrace
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(tags=["traces_pages"])


@router.get("/traces", response_class=HTMLResponse)
async def traces_list(
    request: Request,
    task_id: Optional[str] = Query(None),
    plan_id: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    operation_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Traces list page
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
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        traces = query.order_by(ExecutionTrace.start_time.desc()).offset(offset).limit(page_size).all()
        
        # Get statistics
        stats_query = db.query(ExecutionTrace)
        if task_id:
            try:
                task_uuid = UUID(task_id)
                stats_query = stats_query.filter(ExecutionTrace.task_id == task_uuid)
            except ValueError:
                pass  # Skip invalid UUIDs in stats
        if plan_id:
            try:
                plan_uuid = UUID(plan_id)
                stats_query = stats_query.filter(ExecutionTrace.plan_id == plan_uuid)
            except ValueError:
                pass  # Skip invalid UUIDs in stats
        if trace_id:
            stats_query = stats_query.filter(ExecutionTrace.trace_id == trace_id)
        
        total_traces = stats_query.count()
        success_count = stats_query.filter(ExecutionTrace.status == "success").count()
        error_count = stats_query.filter(ExecutionTrace.status == "error").count()
        timeout_count = stats_query.filter(ExecutionTrace.status == "timeout").count()
        
        # Get unique trace IDs for grouping
        unique_trace_ids = db.query(
            ExecutionTrace.trace_id,
            func.count(ExecutionTrace.id).label("span_count"),
            func.min(ExecutionTrace.start_time).label("start_time"),
            func.max(ExecutionTrace.end_time).label("end_time"),
            func.max(ExecutionTrace.status).label("status")
        ).group_by(ExecutionTrace.trace_id).order_by(func.min(ExecutionTrace.start_time).desc()).limit(100).all()
        
        return templates.TemplateResponse(
            "traces/list.html",
            {
                "request": request,
                "traces": traces,
                "unique_traces": unique_trace_ids,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "stats": {
                    "total": total_traces,
                    "success": success_count,
                    "error": error_count,
                    "timeout": timeout_count,
                },
                "filters": {
                    "task_id": task_id,
                    "plan_id": plan_id,
                    "trace_id": trace_id,
                    "status": status,
                    "operation_name": operation_name,
                }
            }
        )
    except Exception as e:
        logger.error(f"Error rendering traces list: {e}", exc_info=True)
        return templates.TemplateResponse(
            "traces/list.html",
            {
                "request": request,
                "traces": [],
                "unique_traces": [],
                "total": 0,
                "page": 1,
                "page_size": 50,
                "total_pages": 0,
                "stats": {"total": 0, "success": 0, "error": 0, "timeout": 0},
                "filters": {},
                "error": str(e)
            }
        )


@router.get("/traces/{trace_id}", response_class=HTMLResponse)
async def trace_detail(
    request: Request,
    trace_id: str,
    db: Session = Depends(get_db)
):
    """
    Trace detail page with span tree visualization
    """
    try:
        # Get all spans for this trace
        spans = db.query(ExecutionTrace).filter(
            ExecutionTrace.trace_id == trace_id
        ).order_by(ExecutionTrace.start_time.asc()).all()
        
        if not spans:
            return templates.TemplateResponse(
                "traces/detail.html",
                {
                    "request": request,
                    "trace_id": trace_id,
                    "spans": [],
                    "error": "Trace not found"
                }
            )
        
        # Build span tree
        span_map = {span.span_id: span for span in spans if span.span_id}
        root_spans = []
        
        for span in spans:
            if not span.parent_span_id or span.parent_span_id not in span_map:
                root_spans.append(span)
        
        # Calculate trace duration
        start_time = min(s.start_time for s in spans)
        end_time = max(s.end_time for s in spans if s.end_time) if any(s.end_time for s in spans) else None
        total_duration = None
        if end_time:
            total_duration = int((end_time - start_time).total_seconds() * 1000)
        
        # Get statistics
        success_count = sum(1 for s in spans if s.status == "success")
        error_count = sum(1 for s in spans if s.status == "error")
        timeout_count = sum(1 for s in spans if s.status == "timeout")
        
        return templates.TemplateResponse(
            "traces/detail.html",
            {
                "request": request,
                "trace_id": trace_id,
                "spans": spans,
                "root_spans": root_spans,
                "span_map": span_map,
                "start_time": start_time,
                "end_time": end_time,
                "total_duration": total_duration,
                "stats": {
                    "total": len(spans),
                    "success": success_count,
                    "error": error_count,
                    "timeout": timeout_count,
                }
            }
        )
    except Exception as e:
        logger.error(f"Error rendering trace detail: {e}", exc_info=True)
        return templates.TemplateResponse(
            "traces/detail.html",
            {
                "request": request,
                "trace_id": trace_id,
                "spans": [],
                "root_spans": [],
                "span_map": {},
                "error": str(e)
            }
        )

