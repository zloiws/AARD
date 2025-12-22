#!/usr/bin/env python3
"""
Traverse backend/ and fix backslash-escaped double quotes in .py files.
Be careful: this performs a simple textual replacement of '"' -> '"'.
Run and review changes before committing.
"""
import sys
from pathlib import Path

root = Path("backend")
if not root.exists():
    print("backend/ not found")
    sys.exit(1)

fixed = []
for p in root.rglob("*.py"):
    try:
        s = p.read_text(encoding="utf-8")
    except Exception as e:
        print("skip read", p, e)
        continue
    if '"' in s:
        ns = s.replace('"', '"')
        # Fix cases where triple-quote became quoted: '"""' -> '"""'
        ns = ns.replace('"""', '"""')
        if ns != s:
            p.write_text(ns, encoding="utf-8")
            fixed.append(str(p))
            print("fixed", p)

print("Done. Fixed count:", len(fixed))
if fixed:
    print("\n".join(fixed))
sys.exit(0)


