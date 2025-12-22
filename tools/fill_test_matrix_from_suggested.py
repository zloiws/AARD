#!/usr/bin/env python3
from pathlib import Path

IN = Path("backend/tests/TEST_MATRIX.md")

def process():
    text = IN.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    in_table = False
    for line in lines:
        if line.strip().startswith("| File |"):
            in_table = True
            out.append(line)
            continue
        if not in_table:
            out.append(line)
            continue
        if not line.strip().startswith("|"):
            out.append(line)
            continue
        # split into columns between pipes, keep inner content
        cols = [c for c in line.split("|")[1:-1]]
        # ensure we have at least 7 columns (File, Category, Markers, DB, LLM, Notes, SuggestedMarkers)
        # trim but preserve empties
        cols = [c if c is not None else "" for c in cols]
        if len(cols) < 7:
            # pad
            cols += [""] * (7 - len(cols))
        # strip each
        stripped = [c.strip() for c in cols]
        file = stripped[0]
        markers = stripped[2]
        suggested = stripped[6] if len(stripped) > 6 else ""
        if markers == "" and suggested != "":
            # set the markers column to suggested
            stripped[2] = suggested
        # reconstruct columns preserving a single space around content
        new_line = "| " + " | ".join(stripped) + " |"
        out.append(new_line)
    IN.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Updated {IN}")

if __name__ == "__main__":
    if not IN.exists():
        print("File not found:", IN)
    else:
        process()


