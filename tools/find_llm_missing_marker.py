#!/usr/bin/env python3
from pathlib import Path
import re

IN = Path("backend/tests/TEST_MATRIX.md")
OUT = Path("reports/llm_missing_marker.txt")

def main():
    if not IN.exists():
        print("TEST_MATRIX.md not found")
        return
    text = IN.read_text(encoding="utf-8")
    lines = text.splitlines()
    results = []
    for ln in lines:
        if not ln.strip().startswith("| "):
            continue
        parts = [p.strip() for p in ln.split("|")[1:-1]]
        if len(parts) < 7:
            # expected: File, Category, Markers, DB, LLM, Notes, SuggestedMarkers
            continue
        file, category, markers, db, llm, notes, suggested = parts[:7]
        if llm.lower() == "yes":
            has_marker = "real_llm" in markers or "real_llm" in suggested
            if not has_marker:
                results.append(file)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(r + "\n")
    print(f"Wrote {OUT} ({len(results)} files)")

if __name__ == "__main__":
    main()


