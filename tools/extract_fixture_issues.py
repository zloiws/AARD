#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path
import json

IN_CSV = Path("reports/failed_rerun_summary.csv")
OUT_TXT = Path("reports/fixtures_issues.txt")
OUT_JSON = Path("reports/fixtures_issues.json")


def main():
    if not IN_CSV.exists():
        print("Input CSV not found:", IN_CSV)
        return
    issues = []
    with IN_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            msg = (row.get("message") or "").lower()
            if "fixture '" in msg or "fixture " in msg and "not found" in msg:
                issues.append({
                    "file": row.get("file"),
                    "failures": int(row.get("failures") or 0),
                    "errors": int(row.get("errors") or 0),
                    "message": row.get("message")
                })
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_TXT.open("w", encoding="utf-8") as fh:
        for it in issues:
            fh.write(f"{it['file']}: failures={it['failures']}, errors={it['errors']}\n  message: {it['message']}\n\n")
    with OUT_JSON.open("w", encoding="utf-8") as fh:
        json.dump(issues, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_TXT} ({len(issues)} issues) and {OUT_JSON}")


if __name__ == "__main__":
    main()


