import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "alembic" / "versions"

pattern = re.compile(
    r'op\.create_index\(\s*[\'"](?P<idx>[^\'"]+)[\'"]\s*,\s*[\'"](?P<table>[^\'"]+)[\'"]\s*,\s*\[(?P<cols>[^\]]+)\](?P<rest>[^)]*)\)',
    re.MULTILINE,
)

def cols_to_sql(cols_text: str) -> str:
    # cols_text like " 'col1', 'col2' " or " 'col' "
    cols = [c.strip().strip('\'" ') for c in cols_text.split(",") if c.strip()]
    return ", ".join(cols)

def patch_file(path: Path):
    s = path.read_text(encoding="utf-8")
    if "CREATE INDEX IF NOT EXISTS" in s or "CREATE UNIQUE INDEX IF NOT EXISTS" in s:
        return False

    def repl(m):
        idx = m.group("idx")
        table = m.group("table")
        cols = cols_to_sql(m.group("cols"))
        rest = m.group("rest") or ""
        unique = "unique=True" in rest or "unique = True" in rest
        stmt = "CREATE UNIQUE INDEX IF NOT EXISTS" if unique else "CREATE INDEX IF NOT EXISTS"
        return f'op.execute("{stmt} {idx} ON {table} ({cols});")'

    new_s, count = pattern.subn(repl, s)
    if count > 0:
        path.write_text(new_s, encoding="utf-8")
        return True
    return False

def main():
    patched = []
    for f in sorted(ROOT.glob("*.py")):
        if f.name.startswith("__"):
            continue
        try:
            if patch_file(f):
                patched.append(f.name)
        except Exception as e:
            print(f"Failed to patch {f.name}: {e}")
    if patched:
        print("Patched create_index in files:", patched)
    else:
        print("No create_index patches needed.")

if __name__ == "__main__":
    main()


