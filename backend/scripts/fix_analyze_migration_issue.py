#!/usr/bin/env python3
from pathlib import Path


def main():
    p = Path('backend/analyze_migration_issue.py')
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if 'create_tables = re.findall' in line:
            lines[idx] = "                create_tables = re.findall(r'op\\\\.create_table\\\\([\\\\'\\\\\\\"]([^\\\\'\\\\\\\"]+)[\\\\'\\\\\\\"]\\\\)', content)"
            break
    p.write_text("\n".join(lines) + "\n", encoding='utf-8')
    print('patched analyze_migration_issue.py')

if __name__ == '__main__':
    main()


