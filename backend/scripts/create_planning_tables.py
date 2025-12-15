#!/usr/bin/env python3
"""
Create planning hypothesis tables manually
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import engine
from sqlalchemy import text

def create_planning_tables():
    """Create planning hypothesis tables"""

    create_tables_sql = """
    -- plan_hypotheses
    CREATE TABLE IF NOT EXISTS plan_hypotheses (
      id UUID PRIMARY KEY NOT NULL,
      timeline_id UUID NOT NULL REFERENCES decision_timelines(id) ON DELETE CASCADE,
      name VARCHAR(255) NOT NULL,
      description TEXT,
      lifecycle VARCHAR(32) NOT NULL DEFAULT 'draft',
      assumptions JSONB,
      risks JSONB,
      confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
      steps JSONB,
      dependencies JSONB,
      resources JSONB,
      plan_metadata JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ
    );

    -- plan_hypothesis_nodes
    CREATE TABLE IF NOT EXISTS plan_hypothesis_nodes (
      id UUID PRIMARY KEY NOT NULL,
      hypothesis_id UUID NOT NULL REFERENCES plan_hypotheses(id) ON DELETE CASCADE,
      node_id UUID NOT NULL REFERENCES decision_nodes(id) ON DELETE CASCADE,
      node_type VARCHAR(50) NOT NULL,
      node_metadata JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- indexes
    CREATE INDEX IF NOT EXISTS ix_plan_hypotheses_timeline_lifecycle ON plan_hypotheses(timeline_id, lifecycle);
    CREATE INDEX IF NOT EXISTS ix_plan_hypothesis_nodes_hypothesis_node ON plan_hypothesis_nodes(hypothesis_id, node_id);
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(create_tables_sql))
            conn.commit()
            print("Planning hypothesis tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

    return True

if __name__ == "__main__":
    success = create_planning_tables()
    sys.exit(0 if success else 1)
