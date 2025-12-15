#!/usr/bin/env python3
from pathlib import Path

def main():
    p = Path('backend/analyze_migration_issue.py')
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if 'create_tables = re.findall' in line:
            # Use a double-quoted raw string for clarity; use triple-quoted raw literal here to avoid escaping hell
            lines[i] = r'''                create_tables = re.findall(r"op\.create_table\([\'\"]([^\'\"]+)[\'\"]\)", content)'''
            break
    p.write_text('\\n'.join(lines) + '\\n', encoding='utf-8')
    print('patched regex line')

if __name__ == "__main__":
    main()


