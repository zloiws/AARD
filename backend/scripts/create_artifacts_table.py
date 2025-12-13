#!/usr/bin/env python3
from sqlalchemy import create_engine, text
import os

SQL = """
CREATE TABLE IF NOT EXISTS artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  code TEXT,
  prompt TEXT,
  version INTEGER DEFAULT 1 NOT NULL,
  status TEXT DEFAULT 'draft' NOT NULL,
  test_results JSONB,
  security_rating DOUBLE PRECISION,
  created_at TIMESTAMPTZ DEFAULT now(),
  created_by TEXT
);

CREATE TABLE IF NOT EXISTS artifact_dependencies (
  artifact_id UUID NOT NULL,
  depends_on_artifact_id UUID NOT NULL,
  PRIMARY KEY (artifact_id, depends_on_artifact_id)
);
"""

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL)
        print("Created artifacts tables if missing")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


