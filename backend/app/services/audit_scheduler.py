"""
Background scheduler for regular audit reports
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from enum import Enum

from app.core.logging_config import LoggingConfig
from app.core.database import get_db
from app.services.self_audit_service import SelfAuditService
from app.models.audit_report import AuditType, AuditStatus

logger = LoggingConfig.get_logger(__name__)


class AuditSchedule(str, Enum):
    """Audit schedule types"""
    DAILY = "daily"  # Run once per day
    WEEKLY = "weekly"  # Run once per week
    MONTHLY = "monthly"  # Run once per month


class AuditScheduler:
    """Background scheduler for regular audit reports"""
    
    def __init__(self):
        self.running = False
        self.schedules: Dict[AuditSchedule, Dict[str, Any]] = {
            AuditSchedule.DAILY: {
                "enabled": True,
                "audit_type": AuditType.FULL,
                "period_days": 1,
                "hour": 2,  # Run at 2 AM
                "use_llm": False
            },
            AuditSchedule.WEEKLY: {
                "enabled": True,
                "audit_type": AuditType.FULL,
                "period_days": 7,
                "day_of_week": 0,  # Monday (0 = Monday, 6 = Sunday)
                "hour": 3,  # Run at 3 AM
                "use_llm": True
            },
            AuditSchedule.MONTHLY: {
                "enabled": True,
                "audit_type": AuditType.FULL,
                "period_days": 30,
                "day_of_month": 1,  # First day of month
                "hour": 4,  # Run at 4 AM
                "use_llm": True
            }
        }
    
    async def start(self):
        """Start the audit scheduler"""
        if self.running:
            logger.warning("Audit scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting audit scheduler...")
        
        # Run scheduling loop
        asyncio.create_task(self._scheduler_loop())
    
    async def stop(self):
        """Stop the audit scheduler"""
        self.running = False
        logger.info("Stopping audit scheduler...")
    
    async def _scheduler_loop(self):
        """Main scheduling loop - checks every hour"""
        while self.running:
            try:
                await self._check_and_run_scheduled_audits()
                # Check every hour
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Error in audit scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(3600)
    
    async def _check_and_run_scheduled_audits(self):
        """Check if any scheduled audits should run"""
        now = datetime.now(timezone.utc)
        
        # Check daily audit
        if self.schedules[AuditSchedule.DAILY]["enabled"]:
            await self._check_daily_audit(now)
        
        # Check weekly audit
        if self.schedules[AuditSchedule.WEEKLY]["enabled"]:
            await self._check_weekly_audit(now)
        
        # Check monthly audit
        if self.schedules[AuditSchedule.MONTHLY]["enabled"]:
            await self._check_monthly_audit(now)
    
    async def _check_daily_audit(self, now: datetime):
        """Check if daily audit should run"""
        schedule = self.schedules[AuditSchedule.DAILY]
        target_hour = schedule["hour"]
        
        # Check if it's the target hour and we haven't run today
        if now.hour == target_hour and now.minute < 30:  # Run within first 30 minutes of the hour
            # Check if we already ran today
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=schedule["period_days"])
            period_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if not await self._audit_already_exists(period_start, period_end, AuditSchedule.DAILY):
                await self._run_audit(AuditSchedule.DAILY, period_start, period_end)
    
    async def _check_weekly_audit(self, now: datetime):
        """Check if weekly audit should run"""
        schedule = self.schedules[AuditSchedule.WEEKLY]
        target_day = schedule["day_of_week"]
        target_hour = schedule["hour"]
        
        # Check if it's the target day and hour
        if now.weekday() == target_day and now.hour == target_hour and now.minute < 30:
            # Calculate period (last 7 days)
            period_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_start = period_end - timedelta(days=schedule["period_days"])
            
            if not await self._audit_already_exists(period_start, period_end, AuditSchedule.WEEKLY):
                await self._run_audit(AuditSchedule.WEEKLY, period_start, period_end)
    
    async def _check_monthly_audit(self, now: datetime):
        """Check if monthly audit should run"""
        schedule = self.schedules[AuditSchedule.MONTHLY]
        target_day = schedule["day_of_month"]
        target_hour = schedule["hour"]
        
        # Check if it's the target day and hour
        if now.day == target_day and now.hour == target_hour and now.minute < 30:
            # Calculate period (last 30 days)
            period_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_start = period_end - timedelta(days=schedule["period_days"])
            
            if not await self._audit_already_exists(period_start, period_end, AuditSchedule.MONTHLY):
                await self._run_audit(AuditSchedule.MONTHLY, period_start, period_end)
    
    async def _audit_already_exists(
        self,
        period_start: datetime,
        period_end: datetime,
        schedule_type: AuditSchedule
    ) -> bool:
        """Check if audit for this period already exists"""
        try:
            from app.models.audit_report import AuditReport
            
            db = next(get_db())
            
            # Check for existing audit with same period and type
            existing = db.query(AuditReport).filter(
                AuditReport.period_start == period_start,
                AuditReport.period_end == period_end,
                AuditReport.audit_metadata.contains({"schedule_type": schedule_type.value})
            ).first()
            
            db.close()
            return existing is not None
        except Exception as e:
            logger.error(f"Error checking for existing audit: {e}", exc_info=True)
            return False
    
    async def _run_audit(
        self,
        schedule_type: AuditSchedule,
        period_start: datetime,
        period_end: datetime
    ):
        """Run a scheduled audit"""
        try:
            schedule = self.schedules[schedule_type]
            audit_type = schedule["audit_type"]
            use_llm = schedule.get("use_llm", False)
            
            logger.info(
                f"Running scheduled {schedule_type.value} audit for period {period_start} to {period_end}"
            )
            
            db = next(get_db())
            audit_service = SelfAuditService(db)
            
            # Generate report
            report = await audit_service.generate_report(
                audit_type=audit_type,
                period_start=period_start,
                period_end=period_end,
                use_llm=use_llm
            )
            
            # Add schedule metadata
            if report.audit_metadata is None:
                report.audit_metadata = {}
            report.audit_metadata["schedule_type"] = schedule_type.value
            report.audit_metadata["scheduled_at"] = datetime.now(timezone.utc).isoformat()
            
            db.commit()
            db.close()
            
            logger.info(
                f"Scheduled {schedule_type.value} audit completed: Report ID {report.id}, "
                f"Findings: {len(report.findings.get('all_findings', [])) if report.findings else 0}, "
                f"Recommendations: {len(report.recommendations.get('all_recommendations', [])) if report.recommendations else 0}"
            )
        except Exception as e:
            logger.error(f"Error running scheduled audit: {e}", exc_info=True)
    
    def update_schedule(
        self,
        schedule_type: AuditSchedule,
        enabled: Optional[bool] = None,
        audit_type: Optional[AuditType] = None,
        period_days: Optional[int] = None,
        hour: Optional[int] = None,
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
        use_llm: Optional[bool] = None
    ):
        """Update schedule configuration"""
        if schedule_type not in self.schedules:
            raise ValueError(f"Unknown schedule type: {schedule_type}")
        
        schedule = self.schedules[schedule_type]
        
        if enabled is not None:
            schedule["enabled"] = enabled
        if audit_type is not None:
            schedule["audit_type"] = audit_type
        if period_days is not None:
            schedule["period_days"] = period_days
        if hour is not None:
            schedule["hour"] = hour
        if day_of_week is not None:
            schedule["day_of_week"] = day_of_week
        if day_of_month is not None:
            schedule["day_of_month"] = day_of_month
        if use_llm is not None:
            schedule["use_llm"] = use_llm
        
        logger.info(f"Updated {schedule_type.value} schedule: {schedule}")
    
    def get_schedule(self, schedule_type: AuditSchedule) -> Dict[str, Any]:
        """Get schedule configuration"""
        if schedule_type not in self.schedules:
            raise ValueError(f"Unknown schedule type: {schedule_type}")
        return self.schedules[schedule_type].copy()
    
    async def run_audit_now(
        self,
        schedule_type: AuditSchedule,
        use_llm: bool = False
    ):
        """Manually trigger a scheduled audit now"""
        schedule = self.schedules[schedule_type]
        period_days = schedule["period_days"]
        audit_type = schedule["audit_type"]
        
        period_end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        period_start = period_end - timedelta(days=period_days)
        
        await self._run_audit(schedule_type, period_start, period_end)


# Global scheduler instance
_audit_scheduler: Optional[AuditScheduler] = None


def get_audit_scheduler() -> AuditScheduler:
    """Get or create audit scheduler instance"""
    global _audit_scheduler
    if _audit_scheduler is None:
        _audit_scheduler = AuditScheduler()
    return _audit_scheduler

