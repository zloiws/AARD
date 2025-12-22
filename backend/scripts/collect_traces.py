#!/usr/bin/env python3
from __future__ import annotations

import json
import os

from sqlalchemy import text

os.environ.setdefault("PYTHONPATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.workflow_event import WorkflowEvent


def main():
    session = SessionLocal()
    q = text(
        "SELECT id, context, updated_at FROM tasks "
        "WHERE context IS NOT NULL AND jsonb_array_length(COALESCE(context->'planning_trace','[]'))>0 "
        "ORDER BY updated_at DESC LIMIT 5"
    )
    rows = session.execute(q).fetchall()
    out = []
    for r in rows:
        task_id = r[0]
        ctx = r[1] or {}
        updated = r[2]
        traces = ctx.get("planning_trace") if isinstance(ctx.get("planning_trace"), list) else []
        trace_summary = []
        step_counts = {}
        for e in traces:
            step = e.get("step")
            trace_summary.append({"ts": e.get("timestamp"), "step": step, "info": e.get("info")})
            if step:
                step_counts[step] = step_counts.get(step, 0) + 1
        loops = [k for k,v in step_counts.items() if v > 4]
        # workflow events
        wf = session.query(WorkflowEvent).filter(WorkflowEvent.task_id==task_id).order_by(WorkflowEvent.timestamp.desc()).limit(10).all()
        wf_s = [{"ts": w.timestamp.isoformat() if w.timestamp else None, "stage": getattr(w, "stage", None), "message": getattr(w, "message", None)} for w in wf]
        # request_logs referencing task_id (best-effort)
        rq = session.execute(text("SELECT id, request_type, model_used, server_url, status, created_at FROM request_logs WHERE request_data::text LIKE :like ORDER BY created_at DESC LIMIT 5"), {"like": "%"+str(task_id)+"%"}).fetchall()
        rq_s = []
        for row in rq:
            try:
                # SQLAlchemy Row supports _mapping
                rq_s.append(dict(row._mapping))
            except Exception:
                # fallback: convert tuple to dict with known columns
                cols = ["id", "request_type", "model_used", "server_url", "status", "created_at"]
                rq_s.append({cols[i]: row[i] for i in range(min(len(row), len(cols)))})
        out.append({
            "task_id": str(task_id),
            "updated_at": str(updated),
            "planning_trace_count": len(traces),
            "trace_summary": trace_summary,
            "loops_detected": loops,
            "workflow_events": wf_s,
            "request_logs": rq_s
        })
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


