#!/usr/bin/env python3
from __future__ import annotations
import os, json, sys
from sqlalchemy import create_engine, text

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL env var", file=sys.stderr)
        return 2
    engine = create_engine(db_url)
    with engine.connect() as conn:
        q = text("SELECT id, context FROM tasks WHERE context IS NOT NULL AND jsonb_array_length(COALESCE(context->'planning_trace','[]'))>0 ORDER BY updated_at DESC LIMIT 10")
        rows = conn.execute(q).fetchall()
        out = []
        for r in rows:
            tid = str(r[0])
            ctx = r[1] or {}
            traces = ctx.get("planning_trace") if isinstance(ctx.get("planning_trace"), list) else []
            plan = ctx.get("plan") if isinstance(ctx.get("plan"), dict) else {}
            out.append({
                "task_id": tid,
                "planning_trace_count": len(traces),
                "plan_steps_count": plan.get("steps_count") if isinstance(plan.get("steps_count"), int) else None,
                "trace_last": traces[-6:] if traces else []
            })
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


