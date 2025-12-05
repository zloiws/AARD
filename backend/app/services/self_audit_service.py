"""
Self Audit Service for project self-analysis
Provides automated auditing of performance, quality, prompts, and errors
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.audit_report import AuditReport, AuditType, AuditStatus
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.prompt import Prompt
from app.services.project_metrics_service import ProjectMetricsService
from app.services.reflection_service import ReflectionService

logger = LoggingConfig.get_logger(__name__)


class SelfAuditService:
    """
    Service for automated self-auditing of the project:
    - Performance analysis
    - Quality analysis of plans
    - Prompt effectiveness analysis
    - Error pattern analysis
    - Trend analysis and recommendations
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize Self Audit Service
        
        Args:
            db: Database session (optional)
        """
        self.db = db or SessionLocal()
        self.metrics_service = ProjectMetricsService(self.db)
        self.reflection_service = ReflectionService(self.db)
    
    async def audit_performance(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Audit system performance
        
        Args:
            period_start: Start of audit period
            period_end: End of audit period
            
        Returns:
            Performance audit results
        """
        try:
            logger.info(f"Starting performance audit for period {period_start} to {period_end}")
            
            # Get performance metrics
            overview = self.metrics_service.get_overview(
                days=int((period_end - period_start).total_seconds() / 86400)
            )
            
            # Analyze execution times
            execution_metrics = self.db.query(
                func.avg(Plan.actual_duration).label('avg_duration'),
                func.min(Plan.actual_duration).label('min_duration'),
                func.max(Plan.actual_duration).label('max_duration'),
                func.count(Plan.id).label('total_plans')
            ).filter(
                and_(
                    Plan.created_at >= period_start,
                    Plan.created_at < period_end,
                    Plan.actual_duration.isnot(None)
                )
            ).first()
            
            # Analyze task success rates
            task_stats = self.db.query(
                Task.status,
                func.count(Task.id).label('count')
            ).filter(
                and_(
                    Task.created_at >= period_start,
                    Task.created_at < period_end
                )
            ).group_by(Task.status).all()
            
            total_tasks = sum(count for _, count in task_stats)
            completed_tasks = sum(count for status, count in task_stats if status == TaskStatus.COMPLETED)
            failed_tasks = sum(count for status, count in task_stats if status == TaskStatus.FAILED)
            
            success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
            
            # Calculate findings
            findings = []
            recommendations = []
            
            if success_rate < 0.7:
                findings.append({
                    "severity": "high",
                    "type": "low_success_rate",
                    "message": f"Task success rate is {success_rate:.2%}, below threshold of 70%",
                    "value": success_rate
                })
                recommendations.append({
                    "priority": "high",
                    "action": "Investigate failed tasks and improve error handling",
                    "details": f"Failed tasks: {failed_tasks} out of {total_tasks}"
                })
            
            if execution_metrics and execution_metrics.avg_duration:
                avg_duration = execution_metrics.avg_duration
                if avg_duration > 300:  # More than 5 minutes
                    findings.append({
                        "severity": "medium",
                        "type": "high_execution_time",
                        "message": f"Average execution time is {avg_duration:.1f} seconds",
                        "value": avg_duration
                    })
                    recommendations.append({
                        "priority": "medium",
                        "action": "Optimize plan execution to reduce average duration",
                        "details": f"Current average: {avg_duration:.1f}s"
                    })
            
            return {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metrics": {
                    "success_rate": success_rate,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "failed_tasks": failed_tasks,
                    "avg_execution_time": execution_metrics.avg_duration if execution_metrics else None,
                    "min_execution_time": execution_metrics.min_duration if execution_metrics else None,
                    "max_execution_time": execution_metrics.max_duration if execution_metrics else None,
                    "total_plans": execution_metrics.total_plans if execution_metrics else 0
                },
                "findings": findings,
                "recommendations": recommendations,
                "overview": overview
            }
        except Exception as e:
            logger.error(f"Error in performance audit: {e}", exc_info=True)
            return {
                "error": str(e),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat()
            }
    
    async def audit_quality(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Audit plan quality
        
        Args:
            period_start: Start of audit period
            period_end: End of audit period
            
        Returns:
            Quality audit results
        """
        try:
            logger.info(f"Starting quality audit for period {period_start} to {period_end}")
            
            # Get plans in period
            plans = self.db.query(Plan).filter(
                and_(
                    Plan.created_at >= period_start,
                    Plan.created_at < period_end
                )
            ).all()
            
            # Analyze plan characteristics
            total_plans = len(plans)
            completed_plans = sum(1 for p in plans if p.status == PlanStatus.COMPLETED)
            failed_plans = sum(1 for p in plans if p.status == PlanStatus.FAILED)
            
            # Analyze plan complexity (number of steps)
            plan_complexities = []
            for plan in plans:
                if plan.steps:
                    if isinstance(plan.steps, str):
                        import json
                        try:
                            steps = json.loads(plan.steps)
                        except:
                            steps = []
                    else:
                        steps = plan.steps
                    plan_complexities.append(len(steps) if isinstance(steps, list) else 0)
            
            avg_complexity = sum(plan_complexities) / len(plan_complexities) if plan_complexities else 0
            
            # Analyze plan accuracy (estimated vs actual duration)
            duration_accuracy = []
            for plan in plans:
                if plan.estimated_duration and plan.actual_duration:
                    accuracy = plan.estimated_duration / plan.actual_duration if plan.actual_duration > 0 else 0
                    duration_accuracy.append(accuracy)
            
            avg_accuracy = sum(duration_accuracy) / len(duration_accuracy) if duration_accuracy else None
            
            # Calculate findings
            findings = []
            recommendations = []
            
            if completed_plans / total_plans < 0.8 if total_plans > 0 else False:
                findings.append({
                    "severity": "medium",
                    "type": "low_completion_rate",
                    "message": f"Only {completed_plans}/{total_plans} plans completed successfully",
                    "value": completed_plans / total_plans if total_plans > 0 else 0
                })
                recommendations.append({
                    "priority": "medium",
                    "action": "Improve plan quality and error handling",
                    "details": f"Failed plans: {failed_plans}"
                })
            
            if avg_complexity > 10:
                findings.append({
                    "severity": "low",
                    "type": "high_complexity",
                    "message": f"Average plan complexity is {avg_complexity:.1f} steps",
                    "value": avg_complexity
                })
                recommendations.append({
                    "priority": "low",
                    "action": "Consider breaking down complex plans into smaller sub-plans",
                    "details": f"Average steps: {avg_complexity:.1f}"
                })
            
            if avg_accuracy and (avg_accuracy < 0.5 or avg_accuracy > 2.0):
                findings.append({
                    "severity": "medium",
                    "type": "poor_duration_estimation",
                    "message": f"Duration estimation accuracy is {avg_accuracy:.2f} (should be close to 1.0)",
                    "value": avg_accuracy
                })
                recommendations.append({
                    "priority": "medium",
                    "action": "Improve duration estimation in planning",
                    "details": f"Current accuracy: {avg_accuracy:.2f}"
                })
            
            return {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metrics": {
                    "total_plans": total_plans,
                    "completed_plans": completed_plans,
                    "failed_plans": failed_plans,
                    "avg_complexity": avg_complexity,
                    "avg_duration_accuracy": avg_accuracy
                },
                "findings": findings,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Error in quality audit: {e}", exc_info=True)
            return {
                "error": str(e),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat()
            }
    
    async def audit_prompts(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Audit prompt effectiveness
        
        Args:
            period_start: Start of audit period
            period_end: End of audit period
            
        Returns:
            Prompt audit results
        """
        try:
            logger.info(f"Starting prompt audit for period {period_start} to {period_end}")
            
            # Get all prompts
            prompts = self.db.query(Prompt).all()
            
            # Analyze prompt metrics
            prompt_analysis = []
            for prompt in prompts:
                if prompt.usage_count > 0:
                    prompt_analysis.append({
                        "id": str(prompt.id),
                        "name": prompt.name,
                        "type": prompt.prompt_type,
                        "usage_count": prompt.usage_count,
                        "success_rate": prompt.success_rate,
                        "avg_execution_time": prompt.avg_execution_time,
                        "version": prompt.version
                    })
            
            # Sort by usage count
            prompt_analysis.sort(key=lambda x: x["usage_count"], reverse=True)
            
            # Find underperforming prompts
            findings = []
            recommendations = []
            
            for prompt_data in prompt_analysis:
                if prompt_data["success_rate"] is not None and prompt_data["success_rate"] < 0.7:
                    findings.append({
                        "severity": "medium",
                        "type": "low_success_rate",
                        "message": f"Prompt '{prompt_data['name']}' has success rate of {prompt_data['success_rate']:.2%}",
                        "prompt_id": prompt_data["id"],
                        "prompt_name": prompt_data["name"],
                        "value": prompt_data["success_rate"]
                    })
                    recommendations.append({
                        "priority": "medium",
                        "action": f"Review and improve prompt '{prompt_data['name']}'",
                        "details": f"Success rate: {prompt_data['success_rate']:.2%}, Usage: {prompt_data['usage_count']}"
                    })
                
                if prompt_data["avg_execution_time"] and prompt_data["avg_execution_time"] > 5000:  # > 5 seconds
                    findings.append({
                        "severity": "low",
                        "type": "high_execution_time",
                        "message": f"Prompt '{prompt_data['name']}' has high execution time: {prompt_data['avg_execution_time']:.0f}ms",
                        "prompt_id": prompt_data["id"],
                        "prompt_name": prompt_data["name"],
                        "value": prompt_data["avg_execution_time"]
                    })
            
            return {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metrics": {
                    "total_prompts": len(prompts),
                    "active_prompts": len(prompt_analysis),
                    "total_usage": sum(p["usage_count"] for p in prompt_analysis)
                },
                "prompt_analysis": prompt_analysis[:10],  # Top 10 most used
                "findings": findings,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Error in prompt audit: {e}", exc_info=True)
            return {
                "error": str(e),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat()
            }
    
    async def audit_errors(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Audit errors and failure patterns
        
        Args:
            period_start: Start of audit period
            period_end: End of audit period
            
        Returns:
            Error audit results
        """
        try:
            logger.info(f"Starting error audit for period {period_start} to {period_end}")
            
            # Get failed tasks
            failed_tasks = self.db.query(Task).filter(
                and_(
                    Task.status == TaskStatus.FAILED,
                    Task.created_at >= period_start,
                    Task.created_at < period_end
                )
            ).all()
            
            # Get failed plans
            failed_plans = self.db.query(Plan).filter(
                and_(
                    Plan.status == PlanStatus.FAILED,
                    Plan.created_at >= period_start,
                    Plan.created_at < period_end
                )
            ).all()
            
            # Analyze error patterns from task context
            error_patterns = {}
            for task in failed_tasks:
                context = task.get_context()
                execution_logs = context.get("execution_logs", [])
                
                for log in execution_logs:
                    if isinstance(log, dict) and log.get("type") == "error":
                        error_msg = log.get("message", "Unknown error")
                        error_type = self._classify_error(error_msg)
                        error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
            
            # Analyze plan failure reasons
            plan_failure_reasons = {}
            for plan in failed_plans:
                # Try to extract failure reason from plan or task context
                if plan.task:
                    context = plan.task.get_context()
                    execution_logs = context.get("execution_logs", [])
                    for log in execution_logs:
                        if isinstance(log, dict) and log.get("type") == "error":
                            error_msg = log.get("message", "Unknown error")
                            reason = self._classify_error(error_msg)
                            plan_failure_reasons[reason] = plan_failure_reasons.get(reason, 0) + 1
            
            # Calculate findings
            findings = []
            recommendations = []
            
            if len(failed_tasks) > 0:
                findings.append({
                    "severity": "high",
                    "type": "task_failures",
                    "message": f"{len(failed_tasks)} tasks failed in this period",
                    "value": len(failed_tasks),
                    "error_patterns": error_patterns
                })
                recommendations.append({
                    "priority": "high",
                    "action": "Investigate and fix common error patterns",
                    "details": f"Most common errors: {sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:3]}"
                })
            
            if len(failed_plans) > 0:
                findings.append({
                    "severity": "high",
                    "type": "plan_failures",
                    "message": f"{len(failed_plans)} plans failed in this period",
                    "value": len(failed_plans),
                    "failure_reasons": plan_failure_reasons
                })
            
            return {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metrics": {
                    "failed_tasks": len(failed_tasks),
                    "failed_plans": len(failed_plans),
                    "error_patterns": error_patterns,
                    "plan_failure_reasons": plan_failure_reasons
                },
                "findings": findings,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Error in error audit: {e}", exc_info=True)
            return {
                "error": str(e),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat()
            }
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error type from error message"""
        error_lower = error_message.lower()
        
        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "permission" in error_lower or "access" in error_lower:
            return "permission"
        elif "not found" in error_lower or "missing" in error_lower:
            return "not_found"
        elif "invalid" in error_lower or "bad" in error_lower:
            return "invalid_input"
        elif "connection" in error_lower or "network" in error_lower:
            return "connection"
        elif "syntax" in error_lower or "parse" in error_lower:
            return "syntax_error"
        else:
            return "other"
    
    async def generate_report(
        self,
        audit_type: AuditType,
        period_start: datetime,
        period_end: datetime,
        use_llm: bool = False
    ) -> AuditReport:
        """
        Generate a complete audit report
        
        Args:
            audit_type: Type of audit to perform
            period_start: Start of audit period
            period_end: End of audit period
            use_llm: Whether to use LLM for deep analysis
            
        Returns:
            AuditReport instance
        """
        try:
            # Create audit report record
            report = AuditReport(
                audit_type=audit_type,
                status=AuditStatus.IN_PROGRESS,
                period_start=period_start,
                period_end=period_end
            )
            self.db.add(report)
            self.db.commit()
            self.db.refresh(report)
            
            logger.info(f"Generating {audit_type.value} audit report (ID: {report.id})")
            
            # Perform audit based on type
            audit_results = {}
            
            if audit_type in [AuditType.PERFORMANCE, AuditType.FULL]:
                audit_results["performance"] = await self.audit_performance(period_start, period_end)
            
            if audit_type in [AuditType.QUALITY, AuditType.FULL]:
                audit_results["quality"] = await self.audit_quality(period_start, period_end)
            
            if audit_type in [AuditType.PROMPTS, AuditType.FULL]:
                audit_results["prompts"] = await self.audit_prompts(period_start, period_end)
            
            if audit_type in [AuditType.ERRORS, AuditType.FULL]:
                audit_results["errors"] = await self.audit_errors(period_start, period_end)
            
            # Get trends
            from app.models.project_metric import MetricPeriod
            trends = self.metrics_service.get_trends(
                metric_name="task_success_rate",
                days=int((period_end - period_start).total_seconds() / 86400),
                period=MetricPeriod.DAY
            )
            
            # Generate summary
            all_findings = []
            all_recommendations = []
            
            for section, results in audit_results.items():
                if "findings" in results:
                    all_findings.extend(results["findings"])
                if "recommendations" in results:
                    all_recommendations.extend(results["recommendations"])
            
            # Use LLM for summary if requested
            summary = None
            if use_llm and all_findings:
                try:
                    summary = await self._generate_llm_summary(audit_results, all_findings, all_recommendations)
                except Exception as e:
                    logger.warning(f"Failed to generate LLM summary: {e}", exc_info=True)
                    summary = self._generate_text_summary(all_findings, all_recommendations)
            else:
                summary = self._generate_text_summary(all_findings, all_recommendations)
            
            # Update report
            report.status = AuditStatus.COMPLETED
            report.summary = summary
            report.findings = {"sections": audit_results, "all_findings": all_findings}
            report.recommendations = {"all_recommendations": all_recommendations}
            report.metrics = {section: results.get("metrics", {}) for section, results in audit_results.items()}
            report.trends = trends
            report.completed_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(report)
            
            logger.info(f"Audit report {report.id} completed successfully")
            
            return report
        except Exception as e:
            logger.error(f"Error generating audit report: {e}", exc_info=True)
            if report:
                report.status = AuditStatus.FAILED
                report.summary = f"Audit failed: {str(e)}"
                self.db.commit()
            raise
    
    def _generate_text_summary(
        self,
        findings: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Generate text summary without LLM"""
        summary_parts = []
        
        if findings:
            summary_parts.append(f"Found {len(findings)} issues:")
            for finding in findings[:5]:  # Top 5
                summary_parts.append(f"- {finding.get('message', 'Unknown issue')}")
        
        if recommendations:
            summary_parts.append(f"\nGenerated {len(recommendations)} recommendations:")
            for rec in recommendations[:5]:  # Top 5
                summary_parts.append(f"- {rec.get('action', 'Unknown action')}")
        
        return "\n".join(summary_parts) if summary_parts else "No significant issues found."
    
    async def _generate_llm_summary(
        self,
        audit_results: Dict[str, Any],
        findings: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Generate summary using LLM"""
        from app.core.ollama_client import OllamaClient
        
        prompt = f"""Analyze the following audit results and generate a concise summary.

Findings: {len(findings)} issues found
Recommendations: {len(recommendations)} recommendations generated

Key metrics:
{self._format_metrics_for_llm(audit_results)}

Generate a brief executive summary (2-3 paragraphs) highlighting:
1. Overall system health
2. Key issues identified
3. Priority recommendations

Return only the summary text, no additional formatting."""
        
        try:
            client = OllamaClient()
            response = await client.generate(
                prompt=prompt,
                task_type="reasoning"
            )
            return response.response
        except Exception as e:
            logger.warning(f"LLM summary generation failed: {e}")
            return self._generate_text_summary(findings, recommendations)
    
    def _format_metrics_for_llm(self, audit_results: Dict[str, Any]) -> str:
        """Format metrics for LLM prompt"""
        lines = []
        for section, results in audit_results.items():
            if "metrics" in results:
                lines.append(f"{section}:")
                for key, value in results["metrics"].items():
                    if value is not None:
                        lines.append(f"  {key}: {value}")
        return "\n".join(lines)

