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
            
            # Get trends data
            from app.models.project_metric import MetricPeriod
            trends_data = self.metrics_service.get_trends(
                metric_name="task_success_rate",
                days=int((period_end - period_start).total_seconds() / 86400),
                period=MetricPeriod.DAY
            )
            
            # Analyze trends
            trends_analysis = self.analyze_trends(
                metric_name="task_success_rate",
                days=int((period_end - period_start).total_seconds() / 86400),
                period_days=7
            )
            
            # Detect improvements/degradations
            improvements_degradations = self.detect_improvements_degradations(
                period_start=period_start,
                period_end=period_end,
                comparison_period_days=7
            )
            
            # Generate summary
            all_findings = []
            all_recommendations = []
            
            for section, results in audit_results.items():
                if "findings" in results:
                    all_findings.extend(results["findings"])
                if "recommendations" in results:
                    all_recommendations.extend(results["recommendations"])
            
            # Generate smart recommendations
            smart_recommendations = self.generate_smart_recommendations(
                audit_results=audit_results,
                trends=trends_analysis,
                improvements_degradations=improvements_degradations
            )
            
            # Merge recommendations
            all_recommendations.extend(smart_recommendations)
            
            # Remove duplicates
            seen_actions = set()
            unique_recommendations = []
            for rec in all_recommendations:
                action = rec.get("action", "")
                if action not in seen_actions:
                    seen_actions.add(action)
                    unique_recommendations.append(rec)
            
            # Use LLM for summary if requested
            summary = None
            if use_llm and all_findings:
                try:
                    summary = await self._generate_llm_summary(audit_results, all_findings, unique_recommendations)
                except Exception as e:
                    logger.warning(f"Failed to generate LLM summary: {e}", exc_info=True)
                    summary = self._generate_text_summary(all_findings, unique_recommendations)
            else:
                summary = self._generate_text_summary(all_findings, unique_recommendations)
            
            # Add trend info to summary
            if trends_analysis.get("status") == "analyzed":
                trend_info = f"\n\nTrend: {trends_analysis.get('trend_direction', 'unknown')} ({trends_analysis.get('change_percent', 0):.1f}% change)"
                summary = (summary or "") + trend_info
            
            # Update report
            report.status = AuditStatus.COMPLETED
            report.summary = summary
            report.findings = {"sections": audit_results, "all_findings": all_findings}
            report.recommendations = {
                "all_recommendations": unique_recommendations,
                "smart_recommendations": smart_recommendations,
                "count": len(unique_recommendations)
            }
            report.metrics = {section: results.get("metrics", {}) for section, results in audit_results.items()}
            report.trends = {
                "trends_data": trends_data,
                "trend_analysis": trends_analysis,
                "improvements_degradations": improvements_degradations
            }
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
    
    def analyze_trends(
        self,
        metric_name: str,
        days: int = 30,
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze trends for a specific metric
        
        Args:
            metric_name: Name of the metric to analyze
            days: Number of days to look back
            period_days: Period for comparison (e.g., compare last 7 days with previous 7 days)
            
        Returns:
            Trend analysis results
        """
        try:
            from app.models.project_metric import MetricPeriod
            
            # Get trends data
            trends = self.metrics_service.get_trends(
                metric_name=metric_name,
                days=days,
                period=MetricPeriod.DAY
            )
            
            if len(trends) < 2:
                return {
                    "metric_name": metric_name,
                    "status": "insufficient_data",
                    "message": "Not enough data points for trend analysis",
                    "data_points": len(trends)
                }
            
            # Extract values
            values = [t.get("value", 0) for t in trends if t.get("value") is not None]
            
            if len(values) < 2:
                return {
                    "metric_name": metric_name,
                    "status": "insufficient_data",
                    "message": "Not enough valid values for trend analysis",
                    "data_points": len(values)
                }
            
            # Calculate trend direction
            recent_values = values[-period_days:] if len(values) >= period_days else values[-len(values)//2:]
            previous_values = values[-period_days*2:-period_days] if len(values) >= period_days*2 else values[:len(values)//2]
            
            recent_avg = sum(recent_values) / len(recent_values) if recent_values else 0
            previous_avg = sum(previous_values) / len(previous_values) if previous_values else 0
            
            # Determine trend
            change = recent_avg - previous_avg
            change_percent = (change / previous_avg * 100) if previous_avg > 0 else 0
            
            # Calculate slope (simple linear regression)
            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = sum(values) / n
            
            numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            slope = numerator / denominator if denominator > 0 else 0
            
            # Classify trend
            if abs(change_percent) < 5:
                trend_direction = "stable"
                trend_severity = "none"
            elif change_percent > 20:
                trend_direction = "improving"
                trend_severity = "significant"
            elif change_percent > 10:
                trend_direction = "improving"
                trend_severity = "moderate"
            elif change_percent > 5:
                trend_direction = "improving"
                trend_severity = "minor"
            elif change_percent < -20:
                trend_direction = "degrading"
                trend_severity = "significant"
            elif change_percent < -10:
                trend_direction = "degrading"
                trend_severity = "moderate"
            else:
                trend_direction = "degrading"
                trend_severity = "minor"
            
            return {
                "metric_name": metric_name,
                "status": "analyzed",
                "trend_direction": trend_direction,
                "trend_severity": trend_severity,
                "change_absolute": change,
                "change_percent": change_percent,
                "recent_average": recent_avg,
                "previous_average": previous_avg,
                "slope": slope,
                "data_points": len(values),
                "period_days": period_days
            }
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}", exc_info=True)
            return {
                "metric_name": metric_name,
                "status": "error",
                "error": str(e)
            }
    
    def detect_improvements_degradations(
        self,
        period_start: datetime,
        period_end: datetime,
        comparison_period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Detect improvements and degradations by comparing periods
        
        Args:
            period_start: Start of current period
            period_end: End of current period
            comparison_period_days: Days to compare against (previous period)
            
        Returns:
            Dictionary with improvements and degradations
        """
        try:
            # Calculate comparison period
            period_duration = (period_end - period_start).total_seconds() / 86400
            comparison_period_end = period_start
            comparison_period_start = comparison_period_end - timedelta(days=comparison_period_days)
            
            # Get metrics for both periods
            current_metrics = self.metrics_service.get_overview(
                days=int(period_duration)
            )
            previous_metrics = self.metrics_service.get_overview(
                days=comparison_period_days
            )
            
            improvements = []
            degradations = []
            
            # Compare key metrics
            if current_metrics and previous_metrics:
                perf_current = current_metrics.get("performance", {})
                perf_previous = previous_metrics.get("performance", {})
                
                # Success rate
                current_sr = perf_current.get("success_rate")
                previous_sr = perf_previous.get("success_rate")
                if current_sr is not None and previous_sr is not None and current_sr > 0 and previous_sr > 0:
                    change = current_sr - previous_sr
                    if change > 0.05:  # 5% improvement
                        improvements.append({
                            "metric": "success_rate",
                            "change": change,
                            "change_percent": (change / previous_sr * 100),
                            "current": current_sr,
                            "previous": previous_sr,
                            "message": f"Success rate improved by {change:.2%}"
                        })
                    elif change < -0.05:  # 5% degradation
                        degradations.append({
                            "metric": "success_rate",
                            "change": change,
                            "change_percent": (change / previous_sr * 100),
                            "current": current_sr,
                            "previous": previous_sr,
                            "message": f"Success rate degraded by {abs(change):.2%}"
                        })
                
                # Execution time
                current_et = perf_current.get("avg_execution_time")
                previous_et = perf_previous.get("avg_execution_time")
                if current_et is not None and previous_et is not None and current_et > 0 and previous_et > 0:
                    change = previous_et - current_et  # Negative is good (faster)
                    change_percent = (change / previous_et * 100)
                    if change > previous_et * 0.1:  # 10% faster
                        improvements.append({
                            "metric": "execution_time",
                            "change": -change,  # Negative change means improvement
                            "change_percent": change_percent,
                            "current": current_et,
                            "previous": previous_et,
                            "message": f"Execution time improved by {change_percent:.1f}% (faster)"
                        })
                    elif change < -previous_et * 0.1:  # 10% slower
                        degradations.append({
                            "metric": "execution_time",
                            "change": -change,
                            "change_percent": abs(change_percent),
                            "current": current_et,
                            "previous": previous_et,
                            "message": f"Execution time degraded by {abs(change_percent):.1f}% (slower)"
                        })
            
            return {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "comparison_period_start": comparison_period_start.isoformat(),
                "comparison_period_end": comparison_period_end.isoformat(),
                "improvements": improvements,
                "degradations": degradations,
                "summary": {
                    "improvements_count": len(improvements),
                    "degradations_count": len(degradations),
                    "net_change": len(improvements) - len(degradations)
                }
            }
        except Exception as e:
            logger.error(f"Error detecting improvements/degradations: {e}", exc_info=True)
            return {
                "error": str(e),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat()
            }
    
    def generate_smart_recommendations(
        self,
        audit_results: Dict[str, Any],
        trends: Dict[str, Any],
        improvements_degradations: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate smart recommendations based on audit results, trends, and improvements/degradations
        
        Args:
            audit_results: Results from audit methods
            trends: Trend analysis results
            improvements_degradations: Improvements and degradations detected
            
        Returns:
            List of smart recommendations
        """
        recommendations = []
        
        try:
            # Analyze trends for recommendations
            if trends.get("status") == "analyzed":
                trend_direction = trends.get("trend_direction")
                trend_severity = trends.get("trend_severity")
                change_percent = trends.get("change_percent", 0)
                
                if trend_direction == "degrading" and trend_severity in ["significant", "moderate"]:
                    recommendations.append({
                        "priority": "high" if trend_severity == "significant" else "medium",
                        "category": "trend",
                        "action": f"Address degrading trend in {trends.get('metric_name')}",
                        "details": f"Metric has degraded by {abs(change_percent):.1f}% over the period",
                        "reasoning": f"Trend analysis shows {trend_severity} degradation",
                        "source": "trend_analysis"
                    })
                elif trend_direction == "improving" and trend_severity == "significant":
                    recommendations.append({
                        "priority": "low",
                        "category": "trend",
                        "action": f"Maintain practices that improved {trends.get('metric_name')}",
                        "details": f"Metric has improved by {change_percent:.1f}% over the period",
                        "reasoning": f"Trend analysis shows significant improvement",
                        "source": "trend_analysis"
                    })
            
            # Analyze improvements/degradations
            degradations = improvements_degradations.get("degradations", [])
            for degradation in degradations:
                metric = degradation.get("metric")
                change_percent = abs(degradation.get("change_percent", 0))
                
                if metric == "success_rate":
                    recommendations.append({
                        "priority": "high",
                        "category": "performance",
                        "action": "Investigate and fix root causes of task failures",
                        "details": f"Success rate decreased by {change_percent:.1f}%",
                        "reasoning": "Task success rate degradation indicates systemic issues",
                        "source": "period_comparison"
                    })
                elif metric == "execution_time":
                    recommendations.append({
                        "priority": "medium",
                        "category": "performance",
                        "action": "Optimize plan execution and reduce bottlenecks",
                        "details": f"Execution time increased by {change_percent:.1f}%",
                        "reasoning": "Slower execution times may indicate resource constraints or inefficient plans",
                        "source": "period_comparison"
                    })
            
            # Analyze audit findings for recommendations
            for section, results in audit_results.items():
                findings = results.get("findings", [])
                for finding in findings:
                    severity = finding.get("severity", "low")
                    finding_type = finding.get("type")
                    
                    if severity == "high":
                        if finding_type == "low_success_rate":
                            recommendations.append({
                                "priority": "high",
                                "category": "quality",
                                "action": "Conduct root cause analysis of task failures",
                                "details": finding.get("message", ""),
                                "reasoning": "High failure rate requires immediate attention",
                                "source": "audit_findings"
                            })
                        elif finding_type == "task_failures":
                            recommendations.append({
                                "priority": "high",
                                "category": "errors",
                                "action": "Review error patterns and implement fixes",
                                "details": finding.get("message", ""),
                                "reasoning": "Multiple task failures indicate systemic issues",
                                "source": "audit_findings"
                            })
            
            # Remove duplicates (same action)
            seen_actions = set()
            unique_recommendations = []
            for rec in recommendations:
                action_key = rec.get("action", "")
                if action_key not in seen_actions:
                    seen_actions.add(action_key)
                    unique_recommendations.append(rec)
            
            # Sort by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            unique_recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))
            
            return unique_recommendations
            
        except Exception as e:
            logger.error(f"Error generating smart recommendations: {e}", exc_info=True)
            return []
    
    async def analyze_trends_with_llm(
        self,
        trends_data: Dict[str, Any],
        audit_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deep analysis of trends using LLM (stub - requires internet)
        
        Args:
            trends_data: Trend analysis results
            audit_results: Audit results for context
            
        Returns:
            Enhanced analysis with LLM insights (or fallback if LLM unavailable)
        """
        try:
            from app.core.ollama_client import OllamaClient
            
            # Check if LLM is available (stub - will fail gracefully if not)
            client = OllamaClient()
            
            prompt = f"""Analyze the following trend data and provide insights:

Trend Analysis:
{self._format_trends_for_llm(trends_data)}

Audit Context:
{self._format_metrics_for_llm(audit_results)}

Provide:
1. Key insights about the trends
2. Potential root causes
3. Actionable recommendations
4. Risk assessment

Return JSON with: insights, root_causes, recommendations, risk_level"""
            
            response = await client.generate(
                prompt=prompt,
                task_type="reasoning"
            )
            
            # Try to parse JSON response
            import json
            try:
                llm_analysis = json.loads(response.response)
                return {
                    "llm_available": True,
                    "analysis": llm_analysis,
                    "raw_response": response.response
                }
            except json.JSONDecodeError:
                return {
                    "llm_available": True,
                    "analysis": {"insights": response.response},
                    "raw_response": response.response
                }
        except Exception as e:
            logger.warning(f"LLM trend analysis unavailable: {e}. Using fallback analysis.")
            return {
                "llm_available": False,
                "fallback_analysis": {
                    "insights": self._generate_fallback_insights(trends_data),
                    "message": "LLM analysis unavailable, using rule-based analysis"
                },
                "error": str(e)
            }
    
    def _format_trends_for_llm(self, trends_data: Dict[str, Any]) -> str:
        """Format trends data for LLM prompt"""
        lines = []
        if trends_data.get("status") == "analyzed":
            lines.append(f"Metric: {trends_data.get('metric_name')}")
            lines.append(f"Trend: {trends_data.get('trend_direction')} ({trends_data.get('trend_severity')})")
            lines.append(f"Change: {trends_data.get('change_percent', 0):.1f}%")
            lines.append(f"Recent Average: {trends_data.get('recent_average', 0):.2f}")
            lines.append(f"Previous Average: {trends_data.get('previous_average', 0):.2f}")
        else:
            lines.append(f"Status: {trends_data.get('status', 'unknown')}")
            lines.append(f"Message: {trends_data.get('message', 'No data')}")
        return "\n".join(lines)
    
    def _generate_fallback_insights(self, trends_data: Dict[str, Any]) -> str:
        """Generate fallback insights without LLM"""
        if trends_data.get("status") != "analyzed":
            return "Insufficient data for trend analysis."
        
        trend_direction = trends_data.get("trend_direction", "unknown")
        change_percent = trends_data.get("change_percent", 0)
        
        if trend_direction == "improving":
            return f"Metric shows improvement trend ({change_percent:.1f}% increase). Continue current practices."
        elif trend_direction == "degrading":
            return f"Metric shows degradation trend ({abs(change_percent):.1f}% decrease). Investigation recommended."
        else:
            return f"Metric is stable ({abs(change_percent):.1f}% change). No significant trend detected."
    
    async def generate_enhanced_report(
        self,
        audit_type: AuditType,
        period_start: datetime,
        period_end: datetime,
        use_llm: bool = False
    ) -> AuditReport:
        """
        Generate enhanced audit report with trend analysis and smart recommendations
        
        Args:
            audit_type: Type of audit
            period_start: Start of audit period
            period_end: End of audit period
            use_llm: Whether to use LLM for deep analysis (stub if unavailable)
            
        Returns:
            Enhanced AuditReport with trend analysis
        """
        # First generate base report
        report = await self.generate_report(
            audit_type=audit_type,
            period_start=period_start,
            period_end=period_end,
            use_llm=False  # Don't use LLM for base report
        )
        
        try:
            # Analyze trends
            trends_analysis = self.analyze_trends(
                metric_name="task_success_rate",
                days=int((period_end - period_start).total_seconds() / 86400),
                period_days=7
            )
            
            # Detect improvements/degradations
            improvements_degradations = self.detect_improvements_degradations(
                period_start=period_start,
                period_end=period_end,
                comparison_period_days=7
            )
            
            # Generate smart recommendations
            audit_results = report.findings.get("sections", {}) if report.findings else {}
            smart_recommendations = self.generate_smart_recommendations(
                audit_results=audit_results,
                trends=trends_analysis,
                improvements_degradations=improvements_degradations
            )
            
            # Enhance with LLM analysis if requested and available
            llm_analysis = None
            if use_llm:
                try:
                    llm_analysis = await self.analyze_trends_with_llm(
                        trends_data=trends_analysis,
                        audit_results=audit_results
                    )
                except Exception as e:
                    logger.warning(f"LLM analysis failed, using fallback: {e}")
                    llm_analysis = {
                        "llm_available": False,
                        "fallback_analysis": self._generate_fallback_insights(trends_analysis),
                        "error": str(e)
                    }
            
            # Update report with enhanced data
            if report.trends is None:
                report.trends = {}
            
            report.trends.update({
                "trend_analysis": trends_analysis,
                "improvements_degradations": improvements_degradations,
                "llm_analysis": llm_analysis
            })
            
            # Merge smart recommendations with existing ones
            existing_recommendations = report.recommendations.get("all_recommendations", []) if report.recommendations else []
            all_recommendations = existing_recommendations + smart_recommendations
            
            # Remove duplicates
            seen = set()
            unique_recommendations = []
            for rec in all_recommendations:
                action = rec.get("action", "")
                if action not in seen:
                    seen.add(action)
                    unique_recommendations.append(rec)
            
            report.recommendations = {
                "all_recommendations": unique_recommendations,
                "smart_recommendations": smart_recommendations,
                "count": len(unique_recommendations)
            }
            
            # Update summary with trend information
            if trends_analysis.get("status") == "analyzed":
                trend_info = f"\n\nTrend Analysis: {trends_analysis.get('trend_direction', 'unknown')} trend detected ({trends_analysis.get('change_percent', 0):.1f}% change)."
                report.summary = (report.summary or "") + trend_info
            
            self.db.commit()
            self.db.refresh(report)
            
            logger.info(f"Enhanced audit report {report.id} generated with trend analysis")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating enhanced report: {e}", exc_info=True)
            # Return base report even if enhancement fails
            return report

