"""
Page routes for audit reports web interface
"""
from typing import Optional

from app.core.database import get_db
from app.core.templates import templates
from app.models.audit_report import AuditReport, AuditStatus, AuditType
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

router = APIRouter(tags=["audit_reports_pages"])


@router.get("/audit-reports", response_class=HTMLResponse)
async def audit_reports_list_page(
    request: Request,
    audit_type: Optional[AuditType] = Query(None),
    status: Optional[AuditStatus] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List page for audit reports"""
    try:
        query = db.query(AuditReport)
        
        if audit_type:
            query = query.filter(AuditReport.audit_type == audit_type)
        
        if status:
            query = query.filter(AuditReport.status == status)
        
        reports = query.order_by(desc(AuditReport.created_at)).limit(limit).all()
        
        # Convert to dicts for template
        reports_data = [report.to_dict() for report in reports]
        
        return templates.TemplateResponse(
            "audit_reports.html",
            {
                "request": request,
                "reports": reports_data,
                "audit_types": [t.value for t in AuditType],
                "statuses": [s.value for s in AuditStatus],
                "selected_audit_type": audit_type.value if audit_type else None,
                "selected_status": status.value if status else None
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading audit reports: {str(e)}")


@router.get("/audit-reports/{report_id}", response_class=HTMLResponse)
async def audit_report_detail_page(
    request: Request,
    report_id: str,
    db: Session = Depends(get_db)
):
    """Detail page for a specific audit report"""
    try:
        from uuid import UUID
        
        report = db.query(AuditReport).filter(AuditReport.id == UUID(report_id)).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Audit report not found")
        
        report_dict = report.to_dict()
        
        return templates.TemplateResponse(
            "audit_report_detail.html",
            {
                "request": request,
                "report": report_dict
            }
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading audit report: {str(e)}")

