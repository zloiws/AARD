#!/usr/bin/env python3
from pathlib import Path
import xml.etree.ElementTree as ET
import csv

REPORTS = Path("reports")
INPUTS = ["integration.xml", "targeted_after_stubs.xml", "failed_rerun_summary.csv"]
OUT_CSV = REPORTS / "integration_failures_extracted.csv"

def parse_xml(path):
    rows = []
    if not path.exists():
        return rows
    tree = ET.parse(path)
    root = tree.getroot()
    for tc in root.findall(".//testcase"):
        name = tc.attrib.get("name","")
        classname = tc.attrib.get("classname","")
        time = tc.attrib.get("time","")
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")
        if failure is not None:
            msg = failure.attrib.get("message") or (failure.text or "").strip()
            rows.append({"file":classname, "test": name, "outcome":"failure", "message": msg, "time": time})
        if error is not None:
            msg = error.attrib.get("message") or (error.text or "").strip()
            rows.append({"file":classname, "test": name, "outcome":"error", "message": msg, "time": time})
    return rows

def parse_failed_rerun_csv(path):
    rows = []
    if not path.exists():
        return rows
    import csv
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append({"file": r.get("file",""), "test": "", "outcome": "summary", "message": r.get("message",""), "time": r.get("index","")})
    return rows

def main():
    all_rows = []
    for name in ["integration.xml", "targeted_after_stubs.xml"]:
        p = REPORTS / name
        all_rows.extend(parse_xml(p))
    all_rows.extend(parse_failed_rerun_csv(REPORTS / "failed_rerun_summary.csv"))
    # write CSV
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["file","test","outcome","message","time"])
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r)
    print(f"Wrote {OUT_CSV} with {len(all_rows)} rows")

if __name__ == "__main__":
    main()


