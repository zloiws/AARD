#!/usr/bin/env python3
\"\"\"Parse test log for missing columns/tables and generate/apply idempotent SQL patches.

Usage:
  Set env var DATABASE_URL and run:
    python backend/scripts/generate_apply_patches_from_log.py --log backend/logs/latest_test_run.txt
\"\"\"
from __future__ import annotations
import re
import os
import sys
from pathlib import Path
from datetime import datetime

LOG_REGEX_COL = re.compile(r'column \"(?P<col>[^\"]+)\" of relation \"(?P<table>[^\"]+)\" does not exist', re.IGNORECASE)
LOG_REGEX_TAB = re.compile(r'relation \"(?P<table>[^\"]+)\" does not exist', re.IGNORECASE)

SQL_OUT_DIR = Path(__file__).resolve().parents[1] / "sql"
SQL_OUT_DIR.mkdir(parents=True, exist_ok=True)

def guess_type(column_name: str) -> str:
    cn = column_name.lower()
    if cn.endswith("_id") or cn.endswith("_by") or cn.endswith("_uuid") or cn.endswith("_agent_id") or cn.endswith("_server_id") or cn.endswith("_model_id"):
        return "UUID"
    if cn.endswith("_at") or cn.endswith("_time") or cn in ("timestamp","created_at","updated_at","last_seen_at","modified_at","activated_at","last_used_at","last_heartbeat"):
        return "TIMESTAMPTZ"
    if cn.startswith("is_") or cn.startswith("has_") or cn in ("is_active","is_available"):
        return "BOOLEAN"
    if cn.endswith("_count") or cn.endswith("_num") or cn.endswith("_size") or cn.endswith("_bytes") or cn.endswith("_ms") or cn.endswith("_time"):
        return "INTEGER"
    if cn.endswith("_json") or cn.endswith("_data") or cn in ("metadata","event_data","details","capabilities","agent_metadata"):
        return "JSONB"
    if cn.endswith("_rate") or cn.endswith("_score") or cn.endswith("_ratio") or cn in ("success_rate","average_execution_time","response_time_ms"):
        return "DOUBLE PRECISION"
    # fallback
    return "TEXT"

def parse_log(path: Path):
    cols = []
    tables = set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    for m in LOG_REGEX_COL.finditer(text):
        col = m.group('col')
        tbl = m.group('table')
        cols.append((tbl, col))
    for m in LOG_REGEX_TAB.finditer(text):
        tables.add(m.group('table'))
    # remove tables that were found as relation in column matches
    for tbl, _ in cols:
        tables.discard(tbl)
    return cols, tables

def build_sql(cols, tables):
    stmts = []
    # create missing tables minimally
    for tbl in sorted(tables):
        stmts.append(f"CREATE TABLE IF NOT EXISTS {tbl} (id UUID PRIMARY KEY DEFAULT gen_random_uuid());")
    # add missing columns
    grouped = {}
    for tbl, col in cols:
        grouped.setdefault(tbl, []).append(col)
    for tbl, col_list in grouped.items():
        add_parts = []
        for c in col_list:
            ctype = guess_type(c)
            add_parts.append(f"ADD COLUMN IF NOT EXISTS {c} {ctype}")
        if add_parts:
            stmts.append("ALTER TABLE " + tbl + "\n  " + ",\n  ".join(add_parts) + ";")
    if not stmts:
        return "-- Nothing to patch\n"
    header = f"-- Auto-generated patch {datetime.utcnow().isoformat()}\nBEGIN;\n\n"
    footer = "\nCOMMIT;\n"
    return header + "\n".join(stmts) + footer

def write_and_apply(sql_text: str):
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out = SQL_OUT_DIR / f"auto_patch_{ts}.sql"
    out.write_text(sql_text, encoding="utf-8")
    print(f"Wrote patch: {out}")
    # try apply via sqlalchemy
    try:
        from sqlalchemy import create_engine
    except Exception as exc:
        print("SQLAlchemy not available, patch saved but not applied:", exc, file=sys.stderr)
        return False
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set, patch saved but not applied", file=sys.stderr)
        return False
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.exec_driver_sql(sql_text)
    print("Patch applied to DB.")
    return True

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True, help="Path to test run log file")
    args = p.parse_args()
    path = Path(args.log)
    if not path.exists():
        print("Log file not found:", path, file=sys.stderr)
        return 2
    cols, tables = parse_log(path)
    print(f"Found {len(cols)} missing columns and {len(tables)} missing tables.")
    sql_text = build_sql(cols, tables)
    print(sql_text[:400])
    ok = write_and_apply(sql_text)
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())


