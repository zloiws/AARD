#!/usr/bin/env python3
"""Restore missing backend files from a specific commit.

Usage:
  python backend/scripts/restore_from_commit_fixed.py <commit>
"""
from __future__ import annotations
import sys
import subprocess
import os


def run(cmd):
    return subprocess.check_output(cmd)


def main():
    if len(sys.argv) < 2:
        print("Usage: restore_from_commit_fixed.py <commit>")
        return 2
    commit = sys.argv[1]
    out = run(["git", "show", "--name-only", "--pretty=format:", commit]).decode("utf-8", errors="ignore")
    files = [l.strip() for l in out.splitlines() if l.strip()]
    want = []
    for f in files:
        if f.startswith("backend/app/") or f.startswith("backend/scripts/") or f.startswith("backend/alembic/versions/") or f in ("backend/main.py", "backend/init_servers.py"):
            want.append(f)

    restored = []
    skipped = []
    for f in want:
        if os.path.exists(f):
            skipped.append(f)
            continue
        parent = os.path.dirname(f)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        try:
            content = run(["git", "show", f"{commit}:{f}"])
        except subprocess.CalledProcessError:
            print(f"Failed to retrieve {f} from commit {commit}")
            continue
        with open(f, "wb") as fh:
            fh.write(content)
        restored.append(f)
        print("Restored:", f)

    print(f"\\nSummary:\\nRestored {len(restored)} files, skipped {len(skipped)} existing files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


