#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys
import pytest

LIST_FILE = Path("reports/failed_test_files.txt")
OUT_XML = Path("reports/failed_rerun.xml")


def load_list():
    if not LIST_FILE.exists():
        print(f"List file not found: {LIST_FILE}", file=sys.stderr)
        return []
    lines = [l.strip() for l in LIST_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    # normalize slashes
    normalized = []
    for l in lines:
        p = Path(l)
        if not p.exists():
            # try replacing backslashes with forward slashes
            p2 = Path(l.replace("\\", "/"))
            if p2.exists():
                normalized.append(str(p2))
            else:
                # try trimming trailing characters
                if "\\" in l or "/" in l:
                    normalized.append(l)
                else:
                    normalized.append(str(Path("backend/tests") / l))
        else:
            normalized.append(str(p))
    return normalized


def main():
    files = load_list()
    if not files:
        print("No files to run.", file=sys.stderr)
        sys.exit(0)
    # run pytest with the list
    args = files + ["-q", f"--junitxml={OUT_XML}"]
    print("Running pytest on", len(files), "files")
    ret = pytest.main(args)
    sys.exit(ret)


if __name__ == "__main__":
    main()


