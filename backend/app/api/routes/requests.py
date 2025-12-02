"""
API routes for request logs and ranking
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.core.database import get_db
from app.models.request_log import RequestLog, RequestConsequence
from app.core.logging_config import LoggingConfig
from pydantic import BaseModel

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(prefix="/api/requests", tags=["requests"])


class RequestLogResponse(BaseModel):
    """Request log response model"""
    id: str
    request_type: str
    status: str
    model_used: Optional[str]
    server_url: Optional[str]
    duration_ms: Optional[int]
    success_score: float
    importance_score: float
    impact_score: float
    overall_rank: float
    created_artifacts: Optional[List[str]]
    created_plans: Optional[List[str]]
    created_approvals: Optional[List[str]]
    modified_artifacts: Optional[List[str]]
    session_id: Optional[str]
    trace_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RequestLogDetailResponse(BaseModel):
    """Detailed request log response model"""
    id: str
    request_type: str
    request_data: dict
    status: str
    model_used: Optional[str]
    server_url: Optional[str]
    response_data: Optional[dict]
    error_message: Optional[str]
    duration_ms: Optional[int]
    success_score: float
    importance_score: float
    impact_score: float
    overall_rank: float
    created_artifacts: Optional[List[str]]
    created_plans: Optional[List[str]]
    created_approvals: Optional[List[str]]
    modified_artifacts: Optional[List[str]]
    session_id: Optional[str]
    trace_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    consequences: List[dict]
    
    class Config:
        from_attributes = True


class RequestListResponse(BaseModel):
    """Request list response model"""
    requests: List[RequestLogResponse]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=RequestListResponse)
async def list_requests(
    request_type: Optional[str] = Query(None, description="Filter by request type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    model_used: Optional[str] = Query(None, description="Filter by model"),
    min_rank: Optional[float] = Query(None, description="Minimum overall rank"),
    start_time_from: Optional[datetime] = Query(None, description="Filter from this time"),
    start_time_to: Optional[datetime] = Query(None, description="Filter to this time"),
    order_by: str = Query("rank", description="Order by: rank, created_at, duration"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    """
    List request logs with filters
    """
    try:
        # Build query
        query = db.query(RequestLog)
        
        # Apply filters
        if request_type:
            query = query.filter(RequestLog.request_type == request_type)
        
        if status:
            query = query.filter(RequestLog.status == status.lower())
        
        if model_used:
            query = query.filter(RequestLog.model_used == model_used)
        
        if min_rank is not None:
            query = query.filter(RequestLog.overall_rank >= min_rank)
        
        if start_time_from:
            query = query.filter(RequestLog.created_at >= start_time_from)
        
        if start_time_to:
            query = query.filter(RequestLog.created_at <= start_time_to)
        
        # Get total count
        total = query.count()
        
        # Apply ordering
        if order_by == "rank":
            query = query.order_by(desc(RequestLog.overall_rank))
        elif order_by == "created_at":
            query = query.order_by(desc(RequestLog.created_at))
        elif order_by == "duration":
            query = query.order_by(desc(RequestLog.duration_ms))
        else:
            query = query.order_by(desc(RequestLog.overall_rank))
        
        # Apply pagination
        offset = (page - 1) * page_size
        requests = query.offset(offset).limit(page_size).all()
        
        # Convert to response models
        request_responses = [
            RequestLogResponse(
                id=str(req.id),
                request_type=req.request_type,
                status=req.status,
                model_used=req.model_used,
                server_url=req.server_url,
                duration_ms=req.duration_ms,
                success_score=req.success_score,
                importance_score=req.importance_score,
                impact_score=req.impact_score,
                overall_rank=req.overall_rank,
                created_artifacts=[str(aid) for aid in req.created_artifacts] if req.created_artifacts else None,
                created_plans=[str(pid) for pid in req.created_plans] if req.created_plans else None,
                created_approvals=[str(aid) for aid in req.created_approvals] if req.created_approvals else None,
                modified_artifacts=[str(aid) for aid in req.modified_artifacts] if req.modified_artifacts else None,
                session_id=req.session_id,
                trace_id=req.trace_id,
                created_at=req.created_at,
            )
            for req in requests
        ]
        
        return RequestListResponse(
            requests=request_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing requests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranked", response_model=RequestListResponse)
async def get_ranked_requests(
    limit: int = Query(10, ge=1, le=100, description="Number of top requests"),
    db: Session = Depends(get_db)
):
    """
    Get top ranked requests
    """
    try:
        requests = db.query(RequestLog).order_by(
            desc(RequestLog.overall_rank)
        ).limit(limit).all()
        
        request_responses = [
            RequestLogResponse(
                id=str(req.id),
                request_type=req.request_type,
                status=req.status,
                model_used=req.model_used,
                server_url=req.server_url,
                duration_ms=req.duration_ms,
                success_score=req.success_score,
                importance_score=req.importance_score,
                impact_score=req.impact_score,
                overall_rank=req.overall_rank,
                created_artifacts=[str(aid) for aid in req.created_artifacts] if req.created_artifacts else None,
                created_plans=[str(pid) for pid in req.created_plans] if req.created_plans else None,
                created_approvals=[str(aid) for aid in req.created_approvals] if req.created_approvals else None,
                modified_artifacts=[str(aid) for aid in req.modified_artifacts] if req.modified_artifacts else None,
                session_id=req.session_id,
                trace_id=req.trace_id,
                created_at=req.created_at,
            )
            for req in requests
        ]
        
        return RequestListResponse(
            requests=request_responses,
            total=len(request_responses),
            page=1,
            page_size=limit
        )
        
    except Exception as e:
        logger.error(f"Error getting ranked requests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{request_id}", response_model=RequestLogDetailResponse)
async def get_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a single request log by ID
    """
    try:
        request_uuid = UUID(request_id)
        request_log = db.query(RequestLog).filter(RequestLog.id == request_uuid).first()
        
        if not request_log:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Get consequences
        consequences = db.query(RequestConsequence).filter(
            RequestConsequence.request_id == request_uuid
        ).all()
        
        return RequestLogDetailResponse(
            id=str(request_log.id),
            request_type=request_log.request_type,
            request_data=request_log.request_data,
            status=request_log.status,
            model_used=request_log.model_used,
            server_url=request_log.server_url,
            response_data=request_log.response_data,
            error_message=request_log.error_message,
            duration_ms=request_log.duration_ms,
            success_score=request_log.success_score,
            importance_score=request_log.importance_score,
            impact_score=request_log.impact_score,
            overall_rank=request_log.overall_rank,
            created_artifacts=[str(aid) for aid in request_log.created_artifacts] if request_log.created_artifacts else None,
            created_plans=[str(pid) for pid in request_log.created_plans] if request_log.created_plans else None,
            created_approvals=[str(aid) for aid in request_log.created_approvals] if request_log.created_approvals else None,
            modified_artifacts=[str(aid) for aid in request_log.modified_artifacts] if request_log.modified_artifacts else None,
            session_id=request_log.session_id,
            trace_id=request_log.trace_id,
            created_at=request_log.created_at,
            updated_at=request_log.updated_at,
            consequences=[
                {
                    "id": str(c.id),
                    "consequence_type": c.consequence_type,
                    "entity_type": c.entity_type,
                    "entity_id": str(c.entity_id),
                    "impact_type": c.impact_type,
                    "impact_description": c.impact_description,
                    "impact_score": c.impact_score,
                    "created_at": c.created_at,
                }
                for c in consequences
            ],
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{request_id}/consequences", response_model=List[dict])
async def get_request_consequences(
    request_id: str,
    db: Session = Depends(get_db)
):
    """
    Get consequences for a request
    """
    try:
        request_uuid = UUID(request_id)
        consequences = db.query(RequestConsequence).filter(
            RequestConsequence.request_id == request_uuid
        ).all()
        
        return [
            {
                "id": str(c.id),
                "consequence_type": c.consequence_type,
                "entity_type": c.entity_type,
                "entity_id": str(c.entity_id),
                "impact_type": c.impact_type,
                "impact_description": c.impact_description,
                "impact_score": c.impact_score,
                "created_at": c.created_at,
            }
            for c in consequences
        ]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID format")
    except Exception as e:
        logger.error(f"Error getting consequences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_request_stats(
    start_time_from: Optional[datetime] = Query(None, description="Filter from this time"),
    start_time_to: Optional[datetime] = Query(None, description="Filter to this time"),
    db: Session = Depends(get_db)
):
    """
    Get request statistics
    """
    try:
        query = db.query(RequestLog)
        
        if start_time_from:
            query = query.filter(RequestLog.created_at >= start_time_from)
        
        if start_time_to:
            query = query.filter(RequestLog.created_at <= start_time_to)
        
        total = query.count()
        success = query.filter(RequestLog.status == "success").count()
        failed = query.filter(RequestLog.status == "failed").count()
        timeout = query.filter(RequestLog.status == "timeout").count()
        cancelled = query.filter(RequestLog.status == "cancelled").count()
        
        # Average duration
        requests_with_duration = query.filter(
            RequestLog.duration_ms.isnot(None)
        ).all()
        
        if requests_with_duration:
            avg_duration = sum(r.duration_ms for r in requests_with_duration) / len(requests_with_duration)
        else:
            avg_duration = 0
        
        # Average rank
        avg_rank = db.query(
            db.query(RequestLog.overall_rank).subquery()
        ).scalar()
        
        if avg_rank is None:
            requests_for_rank = query.all()
            if requests_for_rank:
                avg_rank = sum(r.overall_rank for r in requests_for_rank) / len(requests_for_rank)
            else:
                avg_rank = 0
        
        # Count by request type
        type_counts = {}
        for req_type in db.query(RequestLog.request_type).distinct():
            type_counts[req_type[0]] = query.filter(RequestLog.request_type == req_type[0]).count()
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "timeout": timeout,
            "cancelled": cancelled,
            "avg_duration_ms": int(avg_duration) if avg_duration else 0,
            "avg_rank": float(avg_rank) if avg_rank else 0.0,
            "by_type": type_counts,
        }
        
    except Exception as e:
        logger.error(f"Error getting request stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

