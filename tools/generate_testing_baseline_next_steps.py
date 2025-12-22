#!/usr/bin/env python3
from pathlib import Path
import re

IN = Path("backend/tests/TEST_MATRIX.md")
OUT = Path(".cursor/plans/TESTING_BASELINE_next_steps.md")

def parse_test_matrix(path: Path):
    text = path.read_text(encoding="utf-8")
    rows = []
    in_table = False
    for line in text.splitlines():
        if line.strip().startswith("| File |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.strip().startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        # Expect at least File, Category, Markers, DB, LLM, Notes (and possibly SuggestedMarkers)
        if len(parts) < 6:
            continue
        file = parts[0]
        category = parts[1]
        markers = parts[2]
        db = parts[3]
        llm = parts[4]
        notes = parts[5]
        suggested = parts[6] if len(parts) > 6 else ""
        rows.append({"file": file, "category": category, "markers": markers, "db": db, "llm": llm, "notes": notes, "suggested": suggested})
    return rows

def filter_missing(rows):
    missing_markers = []
    missing_dbllm = []
    for r in rows:
        if r["markers"] == "":
            missing_markers.append(r["file"])
        if r["db"] == "" or r["llm"] == "":
            missing_dbllm.append(r["file"])
    # unique and preserve order
    def uniq(seq):
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out
    return uniq(missing_markers), uniq(missing_dbllm)

def write_plan(missing_markers, missing_dbllm):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# TESTING_BASELINE_next_steps — checklist")
    lines.append("")
    lines.append("Generated from `backend/tests/TEST_MATRIX.md` — items that need attention before proceeding with stabilization plan.")
    lines.append("")
    lines.append("## 1) Files with missing pytest markers (Markers column empty)")
    lines.append("")
    if not missing_markers:
        lines.append("All files have markers populated.")
    else:
        for f in missing_markers:
            lines.append(f"- `{f}`")
    lines.append("")
    lines.append("## 2) Files with missing DB/LLM indicators (DB or LLM column empty)")
    lines.append("")
    if not missing_dbllm:
        lines.append("All files have DB and LLM indicators populated.")
    else:
        for f in missing_dbllm:
            lines.append(f"- `{f}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Fill markers column with `integration`/`real_llm`/`slow` as appropriate, one file at a time.")
    lines.append("- Fill DB/LLM columns with `yes`/`no` to clarify environment needs.")
    lines.append("- After changes, re-run chunked non-real suite and update `reports/`.")
    OUT.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    print(f"Wrote {OUT} (markers_missing={len(missing_markers)}, dbllm_missing={len(missing_dbllm)})")

def main():
    if not IN.exists():
        print("TEST_MATRIX.md not found", IN)
        return
    rows = parse_test_matrix(IN)
    missing_markers, missing_dbllm = filter_missing(rows)
    write_plan(missing_markers, missing_dbllm)

if __name__ == "__main__":
    main()


