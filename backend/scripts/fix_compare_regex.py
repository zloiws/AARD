#!/usr/bin/env python3
from pathlib import Path

def main():
    p = Path('backend/compare_migrations_vs_models.py')
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if 'create_tables = re.findall' in line:
            lines[i] = r'''            create_tables = re.findall(r'op\.create_table\(\s*[\'"]([^\'"]+)[\'"]', content, re.MULTILINE)'''
            break
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('patched compare_migrations_vs_models.py')

if __name__ == '__main__':
    main()


