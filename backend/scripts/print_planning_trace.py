#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from uuid import UUID

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONPATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.task import Task


def main():
    session = SessionLocal()
    tid = UUID("8680fbf1-13ee-4591-92d5-62e26b6fb9c1")
    task = session.query(Task).filter(Task.id == tid).first()
    if not task:
        print("TASK_NOT_FOUND")
        return 2
    ctx = task.get_context()
    traces = ctx.get("planning_trace") or []
    print("planning_trace length:", len(traces))
    print(json.dumps(traces, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

