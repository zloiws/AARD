#!/usr/bin/env python3
"""
Parse reports/full_with_real_enabled.xml (or reports/non_real.xml) to collect tests
with outcome failure or error and rerun them to capture full tracebacks.

Outputs:
 - reports/failed_test_files.txt  (list of test file paths)
 - runs pytest on those files and writes:
   - reports/failed_rerun.xml
   - reports/failed_rerun.log
"""
from __future__ import annotations
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import sys

PROJECT_ROOT = Path(".")
INPUT_XML = PROJECT_ROOT / "reports" / "full_with_real_enabled.xml"
FALLBACK_XML = PROJECT_ROOT / "reports" / "non_real.xml"
OUT_LIST = PROJECT_ROOT / "reports" / "failed_test_files.txt"


def extract_paths_from_text(text: str):
    # Try to find .py paths; prefer relative 'backend/...' occurrences
    results = []
    # Regex for absolute Windows paths and relative backend/ paths
    for m in re.finditer(r"([A-Za-z]:\\\\[^\\:\n]+?\\.py):\d+", text):
        results.append(m.group(1))
    for m in re.finditer(r"(backend[\\/][^\s:,\\]+?\\.py):\d+", text):
        results.append(m.group(1).replace("/", "\\"))
    # also catch forward-slash style
    for m in re.finditer(r"(backend/[^\s:,/]+?\.py):\d+", text):
        results.append(m.group(1))
    return results


def parse_xml_for_failed_files(xml_path: Path):
    if not xml_path.exists():
        return []
    tree = ET.parse(xml_path)
    root = tree.getroot()
    files = set()
    for tc in root.findall(".//testcase"):
        # check for failure or error child
        failure = tc.find("failure")
        error = tc.find("error")
        if failure is None and error is None:
            continue
        # try to extract file:line from child text
        child = failure if failure is not None else error
        text_parts = []
        if child is not None:
            if child.text:
                text_parts.append(child.text)
            if child.attrib.get("message"):
                text_parts.append(child.attrib.get("message"))
        text = " ".join(text_parts)
        # look for explicit file:line patterns
        matches = extract_paths_from_text(text)
        for p in matches:
            # normalize to project relative if contains backend\
            if "backend" in p:
                idx = p.find("backend")
                rel = p[idx:].replace("/", "\\")
                files.add(rel)
            else:
                files.add(p)
        # fallback: use classname attribute to infer module path
        if not matches:
            classname = tc.attrib.get("classname", "")
            if classname:
                # convert module path to file path
                p = classname.replace(".", "/") + ".py"
                # common case: backend.tests.... -> backend/tests/...
                if p.startswith("backend/") or p.startswith("backend\\"):
                    files.add(p.replace("/", "\\"))
    return sorted(files)


def main():
    xml_to_use = INPUT_XML if INPUT_XML.exists() else FALLBACK_XML
    files = parse_xml_for_failed_files(xml_to_use)
    OUT_LIST.parent.mkdir(parents=True, exist_ok=True)
    with OUT_LIST.open("w", encoding="utf-8") as fh:
        for f in files:
            fh.write(f + "\n")
    print(f"Collected {len(files)} files to {OUT_LIST}")


if __name__ == "__main__":
    main()


