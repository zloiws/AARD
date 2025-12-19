#!/usr/bin/env python3
"""
Simple utility to fix files containing backslash-escaped double quotes ("")
by replacing occurrences of `"` with `"` in a controlled list of files.
Run from repository root: python backend/scripts/fix_escaped_quotes.py
"""
from pathlib import Path

files_to_fix = [
    "backend/app/api/routes/execution_graph.py",
    "backend/app/api/routes/meta.py",
    "backend/scripts/restore_from_commit_fixed.py",
    "backend/scripts/restore_from_commit.py",
    "backend/scripts/list_ollama_servers_models.py",
    "backend/scripts/inspect_table_columns.py",
    "backend/scripts/generate_apply_patches_from_log.py",
]

def fix_file(p: Path) -> bool:
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        print(f"SKIP read error {p}: {e}")
        return False
    if '"' not in text:
        return False
    new_text = text.replace('"', '"')
    # Also fix any occurrences of triple-quote escaped like """" -> '"""'
    new_text = new_text.replace('"""', '"""')
    p.write_text(new_text, encoding="utf-8")
    print(f"Fixed: {p}")
    return True

def main():
    repo_root = Path.cwd()
    fixed = []
    for rel in files_to_fix:
        p = repo_root.joinpath(rel)
        if p.exists():
            if fix_file(p):
                fixed.append(str(rel))
        else:
            print(f"Not found (skip): {rel}")

    print("Done. Files fixed:", fixed)

if __name__ == "__main__":
    main()


