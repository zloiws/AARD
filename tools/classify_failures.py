#!/usr/bin/env python3
from pathlib import Path
import csv, json, re

IN = Path("reports/integration_failures_extracted.csv")
OUT_CSV = Path("reports/integration_failures_classified.csv")
OUT_JSON = Path("reports/integration_failures_classified.json")

ENV_PATTERNS = [
    re.compile(r"ConnectionError", re.I),
    re.compile(r"Failed to establish a new connection", re.I),
    re.compile(r"Connection refused", re.I),
    re.compile(r"OperationalError", re.I),
    re.compile(r"psycopg2", re.I),
]
FIXTURE_PATTERNS = [
    re.compile(r"fixture '", re.I),
    re.compile(r"fixture .* not found", re.I),
    re.compile(r"AsyncMock", re.I),
    re.compile(r"real_model_and_server", re.I),
    re.compile(r"plan_id", re.I),
]
LOGIC_PATTERNS = [
    re.compile(r"AttributeError", re.I),
    re.compile(r"AssertionError", re.I),
    re.compile(r"TypeError", re.I),
    re.compile(r"NameError", re.I),
]
DOC_PATTERNS = [
    re.compile(r"Missing service docs", re.I),
]

def classify_row(msg):
    text = (msg or "").lower()
    for p in ENV_PATTERNS:
        if p.search(text):
            return "environment"
    for p in DOC_PATTERNS:
        if p.search(text):
            return "documentation"
    for p in FIXTURE_PATTERNS:
        if p.search(text):
            return "fixture"
    for p in LOGIC_PATTERNS:
        if p.search(text):
            return "logic"
    return "other"

def main():
    rows = []
    if not IN.exists():
        print("Input not found:", IN)
        return
    with IN.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            cat = classify_row(r.get("message",""))
            r["category"] = cat
            rows.append(r)
    # write outputs
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["file","test","outcome","message","time","category"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    # summary
    summary = {}
    for r in rows:
        summary[r["category"]] = summary.get(r["category"],0)+1
    print("Classified rows:", len(rows), "summary:", summary)

if __name__ == "__main__":
    main()


