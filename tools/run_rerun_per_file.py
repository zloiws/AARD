#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

LIST_FILE = Path("reports/failed_test_files.txt")
LOG = Path("reports/failed_rerun.log")
OUT_DIR = Path("reports/failed_rerun_perfile")

def find_existing_path(entry: str) -> Path | None:
    p = Path(entry)
    if p.exists():
        return p
    p2 = Path(entry.replace("\\", "/"))
    if p2.exists():
        return p2
    # try to find by basename
    name = Path(entry).name
    if name:
        candidates = list(Path("backend/tests").rglob(name))
        if candidates:
            return candidates[0]
    return None

def main():
    if not LIST_FILE.exists():
        print("No list file", file=sys.stderr)
        sys.exit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("w", encoding="utf-8") as logfh:
        lines = [l.strip() for l in LIST_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
        found = []
        for i, entry in enumerate(lines, start=1):
            path = find_existing_path(entry)
            if not path:
                logfh.write(f"SKIP (not found): {entry}\n")
                continue
            found.append(path)
            logfh.write(f"RUN ({i}): {path}\n")
            # run pytest for this single file, capture output
            xml_out = OUT_DIR / f"failed_rerun_{i}.xml"
            cmd = [sys.executable, "-m", "pytest", str(path), "-q", f"--junitxml={xml_out}"]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            logfh.write(proc.stdout or "")
            logfh.write(proc.stderr or "")
            logfh.write("\n" + ("-"*80) + "\n")
        logfh.write(f"Completed. Ran {len(found)} files out of {len(lines)} entries.\n")
    print("Done. See", LOG)

if __name__ == "__main__":
    main()


