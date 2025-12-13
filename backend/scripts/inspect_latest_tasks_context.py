#!/usr/bin/env python3
from sqlalchemy import create_engine, text
import os, json

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, context FROM tasks ORDER BY created_at DESC LIMIT 10")).fetchall()
        for r in rows:
            try:
                m = dict(r._mapping)
            except Exception:
                m = dict(r)
            ctx = m.get('context')
            if not ctx:
                print(m['id'], "no context")
                continue
            if isinstance(ctx, str):
                try:
                    ctx = json.loads(ctx)
                except Exception:
                    print(m['id'], "context not json parsable")
                    continue
            artifacts = ctx.get('artifacts') if isinstance(ctx, dict) else None
            print(m['id'], "artifacts:", type(artifacts), (len(artifacts) if artifacts else 0))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


