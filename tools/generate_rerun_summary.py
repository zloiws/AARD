#!/usr/bin/env python3
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
import json, csv, re

LOG = Path("reports/failed_rerun.log")
PERFILE_DIR = Path("reports/failed_rerun_perfile")
OUT_CSV = Path("reports/failed_rerun_summary.csv")
OUT_JSON = Path("reports/failed_rerun_summary.json")


def parse_log_map():
    """Parse reports/failed_rerun.log for lines 'RUN (i): path' to map index->path"""
    mapping = {}
    if not LOG.exists():
        return mapping
    for line in LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"RUN \((\d+)\):\s+(.*)", line)
        if m:
            idx = int(m.group(1))
            path = m.group(2).strip()
            mapping[idx] = path
    return mapping


def summarize_xmls(mapping):
    rows = []
    for xml in sorted(PERFILE_DIR.glob("failed_rerun_*.xml")):
        # extract index from filename
        m = re.search(r"failed_rerun_(\d+)\.xml$", xml.name)
        idx = int(m.group(1)) if m else None
        test_file = mapping.get(idx, "") if idx is not None else ""
        failures = 0
        errors = 0
        short_message = ""
        try:
            tree = ET.parse(xml)
            root = tree.getroot()
            for tc in root.findall(".//testcase"):
                if tc.find("failure") is not None:
                    failures += 1
                    if not short_message:
                        short_message = (tc.find("failure").attrib.get("message") or (tc.find("failure").text or "")).strip()
                if tc.find("error") is not None:
                    errors += 1
                    if not short_message:
                        short_message = (tc.find("error").attrib.get("message") or (tc.find("error").text or "")).strip()
        except Exception as exc:
            short_message = f"parse_error: {exc}"
        rows.append({"index": idx or -1, "file": test_file, "xml": str(xml), "failures": failures, "errors": errors, "message": short_message})
    return rows


def write_outputs(rows):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["index", "file", "xml", "failures", "errors", "message"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    with OUT_JSON.open("w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)


def main():
    mapping = parse_log_map()
    rows = summarize_xmls(mapping)
    write_outputs(rows)
    total_failures = sum(r["failures"] for r in rows)
    total_errors = sum(r["errors"] for r in rows)
    print(f"Wrote {OUT_CSV} and {OUT_JSON} ({len(rows)} files). failures={total_failures}, errors={total_errors}")


if __name__ == "__main__":
    main()


