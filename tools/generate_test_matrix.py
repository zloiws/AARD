#!/usr/bin/env python3
"""
Generate `backend/tests/TEST_MATRIX.md` by scanning test files and extracting:
 - File | Category | Markers | DB | LLM | Notes

This is a static inventory (do not run tests).
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import List, Set

ROOT = Path(".")
TESTS_DIR = ROOT / "backend" / "tests"
OUT_PATH = TESTS_DIR / "TEST_MATRIX.md"


def find_test_files() -> List[Path]:
    files: List[Path] = []
    for p in TESTS_DIR.rglob("*.py"):
        # skip __pycache__ and helper files if any
        if p.name.startswith("__"):
            continue
        files.append(p)
    files.sort()
    return files


def extract_markers_and_features(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    # markers like @pytest.mark.integration or @pytest.mark.real_llm
    markers = set(re.findall(r"@pytest\.mark\.([A-Za-z0-9_]+)", text))
    # also look for pytest.mark.<name> in code (non-decorator)
    markers.update(re.findall(r"pytest\.mark\.([A-Za-z0-9_]+)", text))
    # detect DB usage by common fixtures or sqlalchemy/psycopg mentions
    db_indicators = ["db_session", "db,", "db)", "db:", "psycopg", "sqlalchemy", "engine", "session"]
    db = any(ind in text for ind in db_indicators)
    # detect LLM usage
    llm_indicators = ["ollama", "Ollama", "real_llm", "OLLAMA", "OllamaClient", "model_name"]
    llm = any(ind in text for ind in llm_indicators)
    return markers, db, llm


def infer_category(path: Path, markers: Set[str]) -> str:
    lower = str(path).lower()
    if "integration" in lower or "integration" in markers:
        return "integration"
    if "cli" in lower or "cli" in markers:
        return "cli"
    if "scripts" in lower or "scripts" in markers:
        return "scripts"
    if "docs" in lower or "docs" in markers:
        return "docs"
    if "api" in lower or "api" in markers:
        return "api"
    # default: unit
    return "unit"


def escape_pipe(s: str) -> str:
    return s.replace("|", "\\|")


def build_matrix():
    files = find_test_files()
    rows = []
    for f in files:
        rel = f.relative_to(ROOT)
        markers, db, llm = extract_markers_and_features(f)
        category = infer_category(f, markers)
        markers_str = ",".join(sorted(markers)) if markers else ""
        rows.append({
            "file": str(rel).replace("\\", "/"),
            "category": category,
            "markers": markers_str,
            "db": "yes" if db else "no",
            "llm": "yes" if llm else "no",
            "notes": ""
        })
    return rows


def write_md(rows):
    lines = []
    lines.append("# TEST_MATRIX — inventory of backend tests")
    lines.append("")
    lines.append("Columns: File | Category | Markers | DB | LLM | Notes")
    lines.append("")
    lines.append("| File | Category | Markers | DB | LLM | Notes |")
    lines.append("| --- | --- | --- | ---: | ---: | --- |")
    for r in rows:
        lines.append(f"| {escape_pipe(r['file'])} | {r['category']} | {escape_pipe(r['markers'])} | {r['db']} | {r['llm']} | {escape_pipe(r['notes'])} |")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH} with {len(rows)} entries")


def main():
    rows = build_matrix()
    write_md(rows)


if __name__ == "__main__":
    main()


