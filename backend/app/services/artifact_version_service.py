"""
Artifact Version Service for managing artifact versions
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.core.logging_config import LoggingConfig
from app.models.artifact import Artifact, ArtifactType, ArtifactStatus
from app.models.artifact_version import ArtifactVersion

logger = LoggingConfig.get_logger(__name__)


class ArtifactVersionService:
    """
    Service for managing artifact versions with:
    - Automatic versioning on changes
    - Changelog tracking
    - Metrics comparison
    - Automatic rollback on metric degradation
    """
    
    def __init__(self, db: Session):
        """
        Initialize Artifact Version Service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_version(
        self,
        artifact: Artifact,
        changelog: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> ArtifactVersion:
        """
        Create a new version of an artifact
        
        Args:
            artifact: Artifact to version
            changelog: Description of changes in this version
            metrics: Performance metrics for this version
            created_by: User/system that created this version
            
        Returns:
            Created ArtifactVersion
        """
        # Get current max version
        max_version = self.db.query(ArtifactVersion.version).filter(
            ArtifactVersion.artifact_id == artifact.id
        ).order_by(desc(ArtifactVersion.version)).first()
        
        new_version = (max_version[0] + 1) if max_version else 1
        
        # Deactivate previous active version
        self.db.query(ArtifactVersion).filter(
            and_(
                ArtifactVersion.artifact_id == artifact.id,
                ArtifactVersion.is_active == "true"
            )
        ).update({"is_active": "false"})
        
        # Create new version snapshot
        version = ArtifactVersion(
            artifact_id=artifact.id,
            version=new_version,
            name=artifact.name,
            description=artifact.description,
            code=artifact.code,
            prompt=artifact.prompt,
            type=artifact.type,
            changelog=changelog or f"Version {new_version} of {artifact.name}",
            created_by=created_by or "system",
            metrics=metrics or {},
            test_results=artifact.test_results,
            security_rating=artifact.security_rating,
            is_active="true",
            promoted_at=datetime.now(timezone.utc)
        )
        
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        
        # Update artifact version
        artifact.version = new_version
        self.db.commit()
        
        logger.info(
            f"Created version {new_version} for artifact {artifact.id}",
            extra={
                "artifact_id": str(artifact.id),
                "artifact_name": artifact.name,
                "version": new_version
            }
        )
        
        return version
    
    def get_version(self, artifact_id: UUID, version: int) -> Optional[ArtifactVersion]:
        """
        Get specific version of an artifact
        
        Args:
            artifact_id: Artifact ID
            version: Version number
            
        Returns:
            ArtifactVersion or None
        """
        return self.db.query(ArtifactVersion).filter(
            and_(
                ArtifactVersion.artifact_id == artifact_id,
                ArtifactVersion.version == version
            )
        ).first()
    
    def get_active_version(self, artifact_id: UUID) -> Optional[ArtifactVersion]:
        """
        Get active version of an artifact
        
        Args:
            artifact_id: Artifact ID
            
        Returns:
            Active ArtifactVersion or None
        """
        return self.db.query(ArtifactVersion).filter(
            and_(
                ArtifactVersion.artifact_id == artifact_id,
                ArtifactVersion.is_active == "true"
            )
        ).first()
    
    def get_all_versions(self, artifact_id: UUID) -> List[ArtifactVersion]:
        """
        Get all versions of an artifact, ordered by version descending
        
        Args:
            artifact_id: Artifact ID
            
        Returns:
            List of ArtifactVersion
        """
        return self.db.query(ArtifactVersion).filter(
            ArtifactVersion.artifact_id == artifact_id
        ).order_by(desc(ArtifactVersion.version)).all()
    
    def compare_versions(
        self,
        artifact_id: UUID,
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """
        Compare two versions of an artifact
        
        Args:
            artifact_id: Artifact ID
            version1: First version number
            version2: Second version number
            
        Returns:
            Comparison result with metrics differences
        """
        v1 = self.get_version(artifact_id, version1)
        v2 = self.get_version(artifact_id, version2)
        
        if not v1 or not v2:
            raise ValueError(f"One or both versions not found: v{version1}, v{version2}")
        
        comparison = {
            "version1": version1,
            "version2": version2,
            "metrics_diff": {},
            "improved": [],
            "degraded": [],
            "unchanged": []
        }
        
        # Compare metrics
        metrics1 = v1.metrics or {}
        metrics2 = v2.metrics or {}
        
        all_metrics = set(list(metrics1.keys()) + list(metrics2.keys()))
        
        for metric in all_metrics:
            val1 = metrics1.get(metric, 0)
            val2 = metrics2.get(metric, 0)
            
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                diff = val2 - val1
                comparison["metrics_diff"][metric] = {
                    "v1": val1,
                    "v2": val2,
                    "diff": diff,
                    "diff_percent": ((val2 - val1) / val1 * 100) if val1 != 0 else 0
                }
                
                # Determine if improved or degraded
                # For success_rate, avg_execution_time (lower is better), etc.
                if metric in ["success_rate", "accuracy"]:
                    if diff > 0:
                        comparison["improved"].append(metric)
                    elif diff < 0:
                        comparison["degraded"].append(metric)
                    else:
                        comparison["unchanged"].append(metric)
                elif metric in ["avg_execution_time", "error_rate"]:
                    if diff < 0:
                        comparison["improved"].append(metric)
                    elif diff > 0:
                        comparison["degraded"].append(metric)
                    else:
                        comparison["unchanged"].append(metric)
        
        # Compare security ratings
        if v1.security_rating and v2.security_rating:
            security_diff = v2.security_rating - v1.security_rating
            comparison["metrics_diff"]["security_rating"] = {
                "v1": v1.security_rating,
                "v2": v2.security_rating,
                "diff": security_diff
            }
            if security_diff < 0:
                comparison["degraded"].append("security_rating")
            elif security_diff > 0:
                comparison["improved"].append("security_rating")
        
        return comparison
    
    def should_rollback(
        self,
        artifact_id: UUID,
        current_version: int,
        threshold_percent: float = 15.0
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if artifact should be rolled back based on metrics degradation
        
        Args:
            artifact_id: Artifact ID
            current_version: Current version to check
            threshold_percent: Percentage degradation threshold (default 15%)
            
        Returns:
            Tuple of (should_rollback: bool, reason: Optional[str])
        """
        current = self.get_version(artifact_id, current_version)
        if not current:
            return False, None
        
        # Get previous active version
        previous = self.db.query(ArtifactVersion).filter(
            and_(
                ArtifactVersion.artifact_id == artifact_id,
                ArtifactVersion.version < current_version,
                ArtifactVersion.is_active == "false"  # Previous active version
            )
        ).order_by(desc(ArtifactVersion.version)).first()
        
        if not previous:
            return False, None  # No previous version to compare
        
        # Compare metrics
        comparison = self.compare_versions(artifact_id, previous.version, current_version)
        
        # Check for significant degradation
        degraded_metrics = []
        for metric in comparison["degraded"]:
            if metric in comparison["metrics_diff"]:
                diff_percent = abs(comparison["metrics_diff"][metric].get("diff_percent", 0))
                if diff_percent >= threshold_percent:
                    degraded_metrics.append(f"{metric} ({diff_percent:.1f}% worse)")
        
        if degraded_metrics:
            reason = f"Metrics degraded: {', '.join(degraded_metrics)}"
            return True, reason
        
        return False, None
    
    def rollback_to_version(
        self,
        artifact_id: UUID,
        target_version: int,
        reason: Optional[str] = None
    ) -> Artifact:
        """
        Rollback artifact to a previous version
        
        Args:
            artifact_id: Artifact ID
            target_version: Version to rollback to
            reason: Reason for rollback
            
        Returns:
            Updated Artifact
        """
        artifact = self.db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")
        
        target_version_obj = self.get_version(artifact_id, target_version)
        if not target_version_obj:
            raise ValueError(f"Version {target_version} not found for artifact {artifact_id}")
        
        # Deactivate current version
        self.db.query(ArtifactVersion).filter(
            and_(
                ArtifactVersion.artifact_id == artifact_id,
                ArtifactVersion.is_active == "true"
            )
        ).update({"is_active": "false"})
        
        # Restore artifact from target version
        artifact.name = target_version_obj.name
        artifact.description = target_version_obj.description
        artifact.code = target_version_obj.code
        artifact.prompt = target_version_obj.prompt
        artifact.test_results = target_version_obj.test_results
        artifact.security_rating = target_version_obj.security_rating
        
        # Create new version from rollback
        new_version = self.create_version(
            artifact=artifact,
            changelog=f"Rollback to version {target_version}" + (f": {reason}" if reason else ""),
            metrics=target_version_obj.metrics,
            created_by="system"
        )
        
        # Mark as rolled back
        new_version.rolled_back_from_version = artifact.version - 1
        new_version.rollback_reason = reason or "Automatic rollback due to metric degradation"
        
        self.db.commit()
        self.db.refresh(artifact)
        
        logger.warning(
            f"Rolled back artifact {artifact_id} to version {target_version}",
            extra={
                "artifact_id": str(artifact_id),
                "target_version": target_version,
                "new_version": new_version.version,
                "reason": reason
            }
        )
        
        return artifact
    
    def auto_rollback_if_degraded(
        self,
        artifact_id: UUID,
        threshold_percent: float = 15.0
    ) -> Optional[Artifact]:
        """
        Automatically rollback if metrics degraded beyond threshold
        
        Args:
            artifact_id: Artifact ID
            threshold_percent: Degradation threshold percentage
            
        Returns:
            Updated Artifact if rolled back, None otherwise
        """
        artifact = self.db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            return None
        
        should_rollback, reason = self.should_rollback(
            artifact_id,
            artifact.version,
            threshold_percent
        )
        
        if should_rollback:
            # Get previous version
            previous = self.db.query(ArtifactVersion).filter(
                and_(
                    ArtifactVersion.artifact_id == artifact_id,
                    ArtifactVersion.version < artifact.version
                )
            ).order_by(desc(ArtifactVersion.version)).first()
            
            if previous:
                return self.rollback_to_version(
                    artifact_id,
                    previous.version,
                    reason
                )
        
        return None

