#!/usr/bin/env python3
import json
import os
from uuid import uuid4

from sqlalchemy import create_engine, text


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.begin() as conn:
        art_id = str(uuid4())
        conn.execute(text(
            "INSERT INTO artifacts (id, type, name, description, created_at, status) VALUES (:id, :type, :name, :desc, now(), :status)"
        ), {"id": art_id, "type": "tool", "name": "test-seed-artifact", "desc": "Seeded artifact for tests", "status": "active"})
        # Attach to the latest task's context artifacts array
        row = conn.execute(text("SELECT id, context FROM tasks ORDER BY created_at DESC LIMIT 1")).fetchone()
        if not row:
            print("No tasks found to attach artifact")
            return 0
        task_id = row[0]
        ctx = row[1] or {}
        # Ensure parsed
        if isinstance(ctx, str):
            try:
                ctx = json.loads(ctx)
            except Exception:
                ctx = {}
        artifacts = ctx.get("artifacts") if isinstance(ctx, dict) else None
        if not isinstance(artifacts, list):
            artifacts = []
        artifacts.append(art_id)
        # Update task context
        conn.execute(text("UPDATE tasks SET context = :ctx WHERE id = :id"), {"ctx": json.dumps(ctx | {"artifacts": artifacts}), "id": task_id})
        print("Inserted artifact", art_id, "and attached to task", task_id)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


