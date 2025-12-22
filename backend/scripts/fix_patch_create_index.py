#!/usr/bin/env python3
from pathlib import Path


def main():
    p = Path('backend/scripts/patch_create_index_if_not_exists.py')
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if 'op\\.create_index' in line:
            # Replace the regex string with a single-quoted raw string variant
            lines[i] = r"""pattern = re.compile(
    r'op\.create_index\(\s*[\'"](?P<idx>[^\'"]+)[\'"]\s*,\s*[\'"](?P<table>[^\'"]+)[\'"]\s*,\s*\[(?P<cols>[^\]]+)\](?P<rest>[^)]*)\)',
    re.MULTILINE,
)"""
            break
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('patched patch_create_index_if_not_exists.py')

if __name__ == '__main__':
    main()


