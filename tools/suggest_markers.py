#!/usr/bin/env python3
"""
Suggest pytest markers for test files based on TEST_MATRIX inventory.
Reads `backend/tests/TEST_MATRIX.md` and writes an updated version with
an additional column `SuggestedMarkers`.

Logic:
 - If DB == yes or category == integration -> suggest `integration`
 - If LLM == yes -> suggest `real_llm`
 - Preserve existing markers; only add suggestions (no file edits)
"""
from __future__ import annotations
from pathlib import Path
import re

IN_PATH = Path("backend/tests/TEST_MATRIX.md")
OUT_PATH = IN_PATH


def parse_table(lines):
    # find header line index (the table header starts with "| File |")
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("| File |"):
            start = i
            break
    if start is None:
        raise RuntimeError("Table header not found in TEST_MATRIX.md")
    header = lines[start].rstrip("\n")
    sep = lines[start+1].rstrip("\n")
    rows = lines[start+2:]
    parsed = []
    for r in rows:
        if not r.strip().startswith("|"):
            continue
        # split into columns; keep empty columns
        parts = [p.strip() for p in r.split("|")[1:-1]]
        # ensure length at least 6 (File, Category, Markers, DB, LLM, Notes)
        while len(parts) < 6:
            parts.append("")
        parsed.append(parts)
    return header, sep, parsed


def suggest_markers_for_row(parts):
    # parts: [File, Category, Markers, DB, LLM, Notes]
    file, category, markers, db, llm, notes = parts
    existing = set([m.strip() for m in markers.split(",") if m.strip()])
    suggestions = set()
    if db.strip().lower() == "yes" or category.strip().lower() == "integration":
        if "integration" not in existing:
            suggestions.add("integration")
    if llm.strip().lower() == "yes":
        if "real_llm" not in existing and "real-llm" not in existing:
            suggestions.add("real_llm")
    # preserve slow if existing contains slow or file path contains "slow" or "timeout"
    if "slow" in markers or "slow" in category or "timeout" in markers:
        if "slow" not in existing:
            suggestions.add("slow")
    return ",".join(sorted(suggestions))


def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(str(IN_PATH))
    raw = IN_PATH.read_text(encoding="utf-8")
    lines = raw.splitlines()
    header, sep, rows = parse_table(lines)
    new_lines = []
    # copy everything up to header start
    for ln in lines:
        if ln.strip().startswith("| File |"):
            break
        new_lines.append(ln)
    # write new header with SuggestedMarkers column
    new_lines.append(header + " | SuggestedMarkers |")
    new_lines.append(sep + " | --- |")
    # process rows
    for parts in rows:
        suggested = suggest_markers_for_row(parts)
        file_cell = parts[0].replace("|", "\\|")
        category = parts[1]
        markers = parts[2]
        db = parts[3]
        llm = parts[4]
        notes = parts[5]
        new_lines.append(f"| {file_cell} | {category} | {markers} | {db} | {llm} | {notes} | {suggested} |")
    OUT_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Updated {OUT_PATH} with SuggestedMarkers column ({len(rows)} rows)")


if __name__ == "__main__":
    main()


