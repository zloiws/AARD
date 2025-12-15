#!/usr/bin/env python3
"""
Fix escaped quote artifacts in backend .py files.
"""
from pathlib import Path

def main():
    root = Path('backend')
    changed = []
    for f in root.rglob('*.py'):
        b = f.read_bytes()
        # First fix triple-quoted patterns, then single escaped quotes
        nb = b.replace(b'\"""', b'"""').replace(b'\"', b'"')
        if nb != b:
            f.write_bytes(nb)
            changed.append(str(f))
            print('fixed', f)
    print('total_fixed', len(changed))

if __name__ == '__main__':
    main()


