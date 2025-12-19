"""
API routes for audit reports
"""
from datetime import datetime
from typing import List, Optional

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.audit_report import AuditReport, AuditStatus, AuditType
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/audit-reports", tags=["audit_reports"])
logger = LoggingConfig.get_logger(__name__)


class AuditReportResponse(BaseModel):
    """Response model for audit report"""
    id: str
    audit_type: str
    status: str
    period_start: str
    period_end: str
    summary: Optional[str]
    findings: Optional[dict]
    recommendations: Optional[dict]
    metrics: Optional[dict]
    trends: Optional[dict]
    audit_metadata: Optional[dict]
    created_at: str
    completed_at: Optional[str]


@router.get("/", response_model=List[AuditReportResponse])
async def list_audit_reports(
    audit_type: Optional[AuditType] = Query(None, description="Filter by audit type"),
    status: Optional[AuditStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of reports to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """List audit reports"""
    try:
        query = db.query(AuditReport)
        
        if audit_type:
            query = query.filter(AuditReport.audit_type == audit_type)
        
        if status:
            query = query.filter(AuditReport.status == status)
        
        reports = query.order_by(desc(AuditReport.created_at)).offset(offset).limit(limit).all()
        
        return [AuditReportResponse(**report.to_dict()) for report in reports]
    except Exception as e:
        logger.error(f"Error listing audit reports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}", response_model=AuditReportResponse)
async def get_audit_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific audit report"""
    try:
        from uuid import UUID
        
        report = db.query(AuditReport).filter(AuditReport.id == UUID(report_id)).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Audit report not found")
        
        return AuditReportResponse(**report.to_dict())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")
    except Exception as e:
        logger.error(f"Error getting audit report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest/{audit_type}", response_model=AuditReportResponse)
async def get_latest_audit_report(
    audit_type: AuditType,
    db: Session = Depends(get_db)
):
    """Get the latest audit report of a specific type"""
    try:
        report = db.query(AuditReport).filter(
            AuditReport.audit_type == audit_type,
            AuditReport.status == AuditStatus.COMPLETED
        ).order_by(desc(AuditReport.completed_at)).first()
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"No completed {audit_type.value} audit report found"
            )
        
        return AuditReportResponse(**report.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest audit report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

