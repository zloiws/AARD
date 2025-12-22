#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path
import json

IN_CSV = Path("reports/failed_rerun_summary.csv")
LOG = Path("reports/failed_rerun.log")
OUT_TXT = Path("reports/environment_issues.txt")
OUT_JSON = Path("reports/environment_issues.json")

KEYWORDS = [
    "connection refused",
    "connection error",
    "failed to establish a new connection",
    "connection reset",
    "max retries exceeded",
    "ollama",
    "no active",
    "statement timeout",
    "OperationalError",
    "UnicodeDecodeError",
    "psycopg2",
    "timeout",
]


def scan_csv():
    matches = []
    if not IN_CSV.exists():
        return matches
    with IN_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            msg = (row.get("message") or "")
            lower = msg.lower()
            for k in KEYWORDS:
                if k in lower:
                    matches.append({"file": row.get("file"), "failures": int(row.get("failures") or 0), "errors": int(row.get("errors") or 0), "message": msg})
                    break
    return matches


def scan_log():
    matches = []
    if not LOG.exists():
        return matches
    text = LOG.read_text(encoding="utf-8", errors="ignore").lower()
    for k in KEYWORDS:
        if k in text:
            # capture surrounding lines
            idx = text.find(k)
            start = max(0, idx - 200)
            end = min(len(text), idx + 200)
            snippet = text[start:end]
            matches.append({"keyword": k, "snippet": snippet})
    return matches


def main():
    csv_matches = scan_csv()
    log_matches = scan_log()
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_TXT.open("w", encoding="utf-8") as fh:
        fh.write("Environment issues found in CSV summary:\n\n")
        for it in csv_matches:
            fh.write(f"{it['file']}: failures={it['failures']}, errors={it['errors']}\n  message: {it['message']}\n\n")
        fh.write("\nLog snippets for keywords:\n\n")
        for it in log_matches:
            fh.write(f"--- {it['keyword']} ---\n")
            fh.write(it['snippet'])
            fh.write("\n\n")
    OUT_JSON.write_text(json.dumps({"csv": csv_matches, "log": log_matches}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_TXT} ({len(csv_matches)} csv matches, {len(log_matches)} log matches) and JSON")


if __name__ == "__main__":
    main()


