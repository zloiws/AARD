#!/usr/bin/env python3
"""Export service docs in backend/docs/services/ to a JSON inventory."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES_DIR = ROOT / "docs" / "services"


def parse_service_md(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    name = path.stem
    # Very small heuristic parsing
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    role = lines[0] if lines else ""
    uses_llm = None
    for l in lines:
        if l.lower().startswith("uses_llm:"):
            uses_llm = l.split(":", 1)[1].strip()
    return {"name": name, "role": role, "uses_llm": uses_llm, "path": str(path.relative_to(ROOT))}


def main():
    items = []
    for p in sorted(SERVICES_DIR.glob("*.md")):
        items.append(parse_service_md(p))
    out = {"services": items}
    out_path = ROOT / "docs" / "services_inventory_export.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Wrote", out_path)


if __name__ == "__main__":
    main()


