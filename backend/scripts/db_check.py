#!/usr/bin/env python3
"""
DB check script: connects to DATABASE_URL and prints counts and sample rows
for interpretation_rules, decision_timelines, decision_nodes, decision_edges.

Usage: python backend/scripts/db_check.py
Set DATABASE_URL env var or edit the DATABASE_URL constant below.
"""
import json
import os
import sys

DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql://postgres:Cdthrf12@10.39.0.101:5432/aard"

TABLES = [
    "interpretation_rules",
    "decision_timelines",
    "decision_nodes",
    "decision_edges",
]

def try_psycopg2(url):
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(dsn=url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        out = {}
        for t in TABLES:
            try:
                cur.execute(f"SELECT count(*) AS cnt FROM {t}")
                cnt = cur.fetchone()["cnt"]
                out[t] = {"count": cnt}
                cur.execute(f"SELECT * FROM {t} LIMIT 5")
                rows = cur.fetchall()
                out[t]["rows"] = rows
            except Exception as e:
                out[t] = {"error": str(e)}
        cur.close()
        conn.close()
        print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        print(f"psycopg2 not available or failed: {e}", file=sys.stderr)
        return False

def try_psycopg(url):
    try:
        import psycopg
        conn = psycopg.connect(url)
        cur = conn.cursor(row_factory=psycopg.rows.dict_row)
        out = {}
        for t in TABLES:
            try:
                cur.execute(f"SELECT count(*) AS cnt FROM {t}")
                cnt = cur.fetchone()["cnt"]
                out[t] = {"count": cnt}
                cur.execute(f"SELECT * FROM {t} LIMIT 5")
                rows = cur.fetchall()
                out[t]["rows"] = rows
            except Exception as e:
                out[t] = {"error": str(e)}
        cur.close()
        conn.close()
        print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        print(f"psycopg (3) not available or failed: {e}", file=sys.stderr)
        return False

def try_sqlalchemy(url):
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        out = {}
        with engine.connect() as conn:
            for t in TABLES:
                try:
                    cnt = conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                    rows = []
                    res = conn.execute(text(f"SELECT * FROM {t} LIMIT 5"))
                    for r in res:
                        rows.append(dict(r._mapping))
                    out[t] = {"count": int(cnt), "rows": rows}
                except Exception as e:
                    out[t] = {"error": str(e)}
        print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        print(f"sqlalchemy not available or failed: {e}", file=sys.stderr)
        return False

def main():
    url = DATABASE_URL
    # Try libraries in order
    if try_psycopg2(url):
        return
    if try_psycopg(url):
        return
    if try_sqlalchemy(url):
        return
    print("No DB client available (psycopg2/psycopg/sqlalchemy). Install one and retry.", file=sys.stderr)
    sys.exit(2)

if __name__ == "__main__":
    main()


