#!/usr/bin/env python3
from pathlib import Path

def fix_file(path: Path):
    b = path.read_bytes()
    if b.find(b'\\n') != -1:
        nb = b.replace(b'\\n', b'\n')
        path.write_bytes(nb)
        print('fixed', path)

def main():
    targets = [
        Path('backend/analyze_migration_issue.py'),
    ]
    for t in targets:
        if t.exists():
            fix_file(t)

if __name__ == '__main__':
    main()


