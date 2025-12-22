#!/usr/bin/env python3
"""
Parse pytest JUnit XML (`reports/non_real.xml`) and produce:
 - reports/test_failures_summary.csv
 - reports/test_failures_summary.json

Each record contains:
 - test: full test identifier (classname::name)
 - outcome: one of failure|error|skipped|passed
 - message: short message or empty
 - time: test time (if present)
 - file: optional file/line info (if present)
"""
from __future__ import annotations
import json
import csv
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import List, Dict

ROOT = Path("reports")
INPUT_XML = ROOT / "non_real.xml"
OUT_CSV = ROOT / "test_failures_summary.csv"
OUT_JSON = ROOT / "test_failures_summary.json"


def parse_junit_xml(path: Path) -> List[Dict]:
    if not path.exists():
        raise FileNotFoundError(f"JUnit XML not found: {path}")
    tree = ET.parse(path)
    root = tree.getroot()
    records: List[Dict] = []
    # find all testcase elements
    for tc in root.findall(".//testcase"):
        classname = tc.attrib.get("classname", "").strip()
        name = tc.attrib.get("name", "").strip()
        time = tc.attrib.get("time", "")
        file_info = tc.attrib.get("file", "") or ""
        full_name = f"{classname}::{name}" if classname else name
        outcome = "passed"
        message = ""
        # Check for failure / error / skipped children
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")
        if failure is not None:
            outcome = "failure"
            # message attribute or element text
            message = failure.attrib.get("message", "") or (failure.text or "").strip()
        elif error is not None:
            outcome = "error"
            message = error.attrib.get("message", "") or (error.text or "").strip()
        elif skipped is not None:
            outcome = "skipped"
            message = skipped.attrib.get("message", "") or (skipped.text or "").strip()
        records.append(
            {
                "test": full_name,
                "outcome": outcome,
                "message": message.replace("\n", " ").strip(),
                "time": time,
                "file": file_info,
            }
        )
    return records


def write_csv(records: List[Dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["test", "outcome", "message", "time", "file"])
        writer.writeheader()
        for r in records:
            writer.writerow(r)


def write_json(records: List[Dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)


def summarize(records: List[Dict]) -> Dict[str, int]:
    counts = {"passed": 0, "failure": 0, "error": 0, "skipped": 0}
    for r in records:
        cnt = counts.get(r["outcome"])
        if cnt is None:
            counts[r["outcome"]] = 1
        else:
            counts[r["outcome"]] = cnt + 1
    return counts


def main():
    try:
        records = parse_junit_xml(INPUT_XML)
    except Exception as exc:
        print(f"ERROR: failed to parse junit xml: {exc}")
        raise
    # keep only failures and errors in CSV/JSON as primary (but include all for completeness)
    write_csv(records, OUT_CSV)
    write_json(records, OUT_JSON)
    counts = summarize(records)
    total = len(records)
    print(f"Parsed {total} testcases. counts={counts}")
    print(f"Wrote CSV -> {OUT_CSV}")
    print(f"Wrote JSON -> {OUT_JSON}")


if __name__ == "__main__":
    main()


