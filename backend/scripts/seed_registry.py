"""
Seed the (Artifact-backed) Registry from existing DB tables.

This script is intentionally conservative:
- It can copy active tools from `tools` table into `artifacts` table (type='tool')
- It does NOT delete anything.
- It supports dry-run.

Usage (from repo root or backend/):
  python backend/scripts/seed_registry.py --from-tools --dry-run
  python backend/scripts/seed_registry.py --from-tools
"""

from __future__ import annotations

import argparse
from typing import Optional

from app.core.database import get_session_local
from app.models.artifact import Artifact
from app.models.tool import Tool


def seed_from_tools(dry_run: bool) -> int:
    SessionLocal = get_session_local()
    db = SessionLocal()
    created = 0
    try:
        tools = db.query(Tool).all()
        for t in tools:
            # Only seed active tools by default; keep behavior deterministic.
            if (t.status or "").lower() != "active":
                continue

            exists = (
                db.query(Artifact)
                .filter(Artifact.type == "tool")
                .filter(Artifact.name == t.name)
                .first()
            )
            if exists:
                continue

            a = Artifact(
                type="tool",
                name=t.name,
                description=t.description,
                code=t.code,
                prompt=None,
                version=int(getattr(t, "version", 1) or 1),
                status="draft",  # require explicit approval before activation
                created_by=getattr(t, "created_by", None) or "seed_registry",
            )
            created += 1
            if not dry_run:
                db.add(a)

        if not dry_run:
            db.commit()
        return created
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-tools", action="store_true", help="Seed artifacts from active tools in `tools` table")
    ap.add_argument("--dry-run", action="store_true", help="Do not write changes to DB")
    args = ap.parse_args()

    if not args.from_tools:
        print("Nothing to do. Provide --from-tools.")
        return 0

    created = seed_from_tools(dry_run=bool(args.dry_run))
    mode = "DRY_RUN" if args.dry_run else "WRITE"
    print(f"[{mode}] Created {created} artifact records from active tools.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


