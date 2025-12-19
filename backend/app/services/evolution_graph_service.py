"""
EvolutionGraphService: build evolution graph from EvolutionHistory entries.
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.evolution import EntityType, EvolutionHistory
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class EvolutionGraphService:
    """
    Build a graph representation of component evolution.
    Nodes represent component versions, edges represent 'from_version' -> 'to_version'.
    """

    def __init__(self, db: Optional[Session] = None):
        self._db_provided = db is not None
        self._db = db

    def _get_session(self) -> Session:
        return self._db if self._db_provided else SessionLocal()

    def build_component_evolution(self, component_id: str) -> Dict[str, Any]:
        """
        Build evolution graph for a single component (artifact/agent).
        Returns dict with nodes and edges suitable for frontend consumption.
        """
        db = self._get_session()
        try:
            entries = db.query(EvolutionHistory).filter(EvolutionHistory.entity_id == component_id).order_by(EvolutionHistory.created_at.asc()).all()
            if not entries:
                return {"nodes": [], "edges": []}

            nodes = []
            edges = []
            version_map = {}  # map version identifier to node id

            for entry in entries:
                after = entry.after_state or {}
                before = entry.before_state or {}
                node_id = f"{entry.id}"
                version_label = after.get("version") or before.get("version") or f"v{len(nodes)+1}"
                nodes.append({
                    "id": node_id,
                    "version": str(version_label),
                    "change_type": entry.change_type.value if entry.change_type else None,
                    "description": entry.change_description,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                    "data": {
                        "before": before,
                        "after": after,
                        "trigger_type": entry.trigger_type.value if entry.trigger_type else None
                    }
                })
                # create edge from previous entry to this
                if nodes and len(nodes) > 1:
                    prev_id = nodes[-2]["id"]
                    edges.append({
                        "id": f"{prev_id}_to_{node_id}",
                        "source": prev_id,
                        "target": node_id,
                        "label": entry.change_type.value if entry.change_type else None
                    })

            return {"nodes": nodes, "edges": edges}
        finally:
            if not self._db_provided:
                db.close()

    def build_system_evolution(self, limit: int = 100) -> Dict[str, Any]:
        """
        Build a simplified system-wide timeline graph from EvolutionHistory.
        Returns recent entries as nodes and chronological 'next' edges.
        """
        db = self._get_session()
        try:
            entries = db.query(EvolutionHistory).order_by(EvolutionHistory.created_at.asc()).limit(limit).all()
            nodes = []
            edges = []
            for i, entry in enumerate(entries):
                nodes.append({
                    "id": str(entry.id),
                    "entity_type": entry.entity_type.value if entry.entity_type else None,
                    "entity_id": str(entry.entity_id) if entry.entity_id else None,
                    "change_type": entry.change_type.value if entry.change_type else None,
                    "description": entry.change_description,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                })
                if i > 0:
                    edges.append({
                        "id": f"{entries[i-1].id}_to_{entry.id}",
                        "source": str(entries[i-1].id),
                        "target": str(entry.id),
                        "label": "next"
                    })
            return {"nodes": nodes, "edges": edges}
        finally:
            if not self._db_provided:
                db.close()


