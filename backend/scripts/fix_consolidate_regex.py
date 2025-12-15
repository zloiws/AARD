#!/usr/bin/env python3
from pathlib import Path

def main():
    p = Path('backend/scripts/consolidate_plans.py')
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if 'revision_match = re.search' in line:
            lines[i] = r"""                revision_match = re.search(r'revision\s*:\s*str\s*=\s*[\'\"](\d+)[\'\"]', content)"""
            break
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('patched consolidate_plans.py')

if __name__ == '__main__':
    main()


