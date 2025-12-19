#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("PYTHONPATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import SessionLocal


def main():
    session = SessionLocal()
    try:
        rows = session.execute(
            "SELECT id, context->'planning_trace' AS planning_trace, context FROM tasks WHERE context IS NOT NULL AND jsonb_array_length(COALESCE(context->'planning_trace','[]'))>0 ORDER BY updated_at DESC LIMIT 5"
        ).fetchall()
        out = []
        for r in rows:
            task_id = str(r[0])
            trace = r[1]
            ctx = r[2]
            out.append({"task_id": task_id, "planning_trace_count": len(trace) if isinstance(trace, list) else 0, "planning_trace": trace, "context_excerpt": {k: ctx.get(k) for k in ['plan','active_todos'] if isinstance(ctx, dict)}})
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.stdout.flush()
    except Exception as e:
        print("ERROR", e, file=sys.stderr)
        sys.stderr.flush()
        return 2
    finally:
        session.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


