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
        # Find the most recent task with planning_trace entries
        q = text("SELECT id, context FROM tasks WHERE context IS NOT NULL AND jsonb_typeof(context->'planning_trace')='array' AND jsonb_array_length(COALESCE(context->'planning_trace','[]'))>0 ORDER BY updated_at DESC LIMIT 1")
        row = conn.execute(q).fetchone()
        if not row:
            print("No tasks with planning_trace found.")
            return 0
        task_id = str(row[0])
        ctx = row[1] or {}
        traces = ctx.get("planning_trace") if isinstance(ctx.get("planning_trace"), list) else []
        out = {"task_id": task_id, "planning_trace_count": len(traces), "planning_trace": traces}
        # workflow events
        we_q = text("SELECT id, stage, message, timestamp, event_data FROM workflow_events WHERE task_id = :tid ORDER BY timestamp DESC LIMIT 20")
        we_rows = conn.execute(we_q, {"tid": task_id}).fetchall()
        out["workflow_events"] = [ {"id": str(r[0]), "stage": r[1], "message": r[2], "timestamp": str(r[3]), "event_data": r[4]} for r in we_rows ]
        # request_logs referencing task_id (best-effort by request_data text)
        rq_q = text("SELECT id, request_type, model_used, server_url, status, created_at, request_data FROM request_logs WHERE request_data::text LIKE :like ORDER BY created_at DESC LIMIT 10")
        rq_rows = conn.execute(rq_q, {"like": "%"+task_id+"%"}).fetchall()
        out["request_logs"] = [ {"id": str(r[0]), "request_type": r[1], "model_used": r[2], "server_url": r[3], "status": r[4], "created_at": str(r[5]), "request_data": r[6]} for r in rq_rows ]
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


