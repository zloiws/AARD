"""
Registry service: single source of truth for artifacts and capabilities.

Scope (Phase 2 deliverable):
- Provide a stable, non-LLM API for listing / looking up artifacts (agents/tools).
- Expose "capabilities" as names that can be routed/selected against.

Note: The codebase currently has both:
- `artifacts` table (agents/tools as Artifact records)
- `tools` table (Tool records)
- `agents` table (Agent records)

This registry starts with Artifact as the canonical store (per plan),
but can surface Tool/Agent information as supplementary data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.agent import Agent
from app.models.artifact import Artifact
from app.models.tool import Tool
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CapabilityRecord:
    name: str
    source: str  # "artifact_tool" | "tool" | "agent"
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RegistryService:
    def __init__(self, db: Session):
        self.db = db

    # --- Artifacts (canonical for this phase) ---
    def list_artifacts(
        self,
        artifact_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Artifact]:
        q = self.db.query(Artifact)
        if artifact_type:
            q = q.filter(Artifact.type == artifact_type)
        if status:
            q = q.filter(Artifact.status == status)
        return q.order_by(Artifact.created_at.desc()).offset(offset).limit(limit).all()

    def get_artifact(self, artifact_id: UUID) -> Optional[Artifact]:
        return self.db.query(Artifact).filter(Artifact.id == artifact_id).first()

    def register_artifact(
        self,
        *,
        artifact_type: str,
        name: str,
        description: Optional[str] = None,
        code: Optional[str] = None,
        prompt: Optional[str] = None,
        status: str = "draft",
        created_by: str = "system",
        version: int = 1,
        security_rating: Optional[float] = None,
        test_results: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        artifact = Artifact(
            type=str(artifact_type),
            name=name,
            description=description,
            code=code,
            prompt=prompt,
            status=str(status),
            created_by=created_by,
            version=int(version),
            security_rating=security_rating,
            test_results=test_results,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def update_lifecycle(self, artifact_id: UUID, status: str) -> Optional[Artifact]:
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return None
        artifact.status = str(status)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    # --- Capabilities (registry view) ---
    def list_capabilities(self, include_inactive: bool = False) -> List[CapabilityRecord]:
        caps: List[CapabilityRecord] = []

        # From Artifact tools (canonical for this phase)
        aq = self.db.query(Artifact).filter(Artifact.type == "tool")
        if not include_inactive:
            aq = aq.filter(Artifact.status == "active")
        for a in aq.all():
            caps.append(CapabilityRecord(name=a.name, source="artifact_tool", status=a.status))

        # From tools table (supplementary)
        tq = self.db.query(Tool)
        if not include_inactive:
            tq = tq.filter(Tool.status == "active")
        for t in tq.all():
            caps.append(CapabilityRecord(name=t.name, source="tool", status=t.status))

        # From agents table capabilities (supplementary)
        agq = self.db.query(Agent)
        if not include_inactive:
            agq = agq.filter(Agent.status == "active")
        for ag in agq.all():
            for cap in (ag.capabilities or []):
                caps.append(
                    CapabilityRecord(
                        name=str(cap),
                        source="agent",
                        status=ag.status,
                        metadata={"agent_id": str(ag.id), "agent_name": ag.name},
                    )
                )

        # Deduplicate by (name, source)
        seen = set()
        out: List[CapabilityRecord] = []
        for c in caps:
            key = (c.name, c.source)
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        out.sort(key=lambda x: (x.name, x.source))
        return out

    def lookup_by_capability(self, capability_name: str, include_inactive: bool = False) -> Dict[str, Any]:
        """Return matching agents/tools/artifacts that claim this capability/name."""
        result: Dict[str, Any] = {"capability": capability_name, "matches": {"artifact_tools": [], "tools": [], "agents": []}}

        aq = self.db.query(Artifact).filter(Artifact.type == "tool", Artifact.name == capability_name)
        if not include_inactive:
            aq = aq.filter(Artifact.status == "active")
        for a in aq.all():
            result["matches"]["artifact_tools"].append({"id": str(a.id), "name": a.name, "status": a.status, "version": a.version})

        tq = self.db.query(Tool).filter(Tool.name == capability_name)
        if not include_inactive:
            tq = tq.filter(Tool.status == "active")
        for t in tq.all():
            result["matches"]["tools"].append({"id": str(t.id), "name": t.name, "status": t.status, "version": t.version})

        agq = self.db.query(Agent)
        if not include_inactive:
            agq = agq.filter(Agent.status == "active")
        for ag in agq.all():
            if capability_name in (ag.capabilities or []):
                result["matches"]["agents"].append(
                    {"id": str(ag.id), "name": ag.name, "status": ag.status, "version": ag.version, "capabilities": ag.capabilities or []}
                )

        return result


