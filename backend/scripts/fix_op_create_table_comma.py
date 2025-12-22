import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "alembic" / "versions"

def fix_file(path: Path):
    s = path.read_text(encoding="utf-8")
    if "op.create_table(," not in s:
        return False

    # Find patterns where earlier we inserted conn.execute(sa.text("select to_regclass('public.table')"))
    pattern_conn = re.compile(r'conn\.execute\(sa\.text\(\s*"select to_regclass\(\'public\.([a-z0-9_]+)\'\)"\s*\)\)\.scalar\(\s*\)')
    # For each op.create_table(, we need to find nearest preceding conn.execute occurrence
    parts = s.split("op.create_table(,")
    new_parts = [parts[0]]
    for i in range(1, len(parts)):
        prefix = new_parts[-1]
        # search for last conn.execute before this split
        m = list(pattern_conn.finditer(prefix))
        table = None
        if m:
            table = m[-1].group(1)
        else:
            # fallback: try to find table name in following lines (unlikely)
            table = "unknown_table"
        replacement = f"op.create_table('{table}',"
        new_parts.append(replacement + parts[i])
    new_s = "".join(new_parts)
    path.write_text(new_s, encoding="utf-8")
    return True

def main():
    patched = []
    for f in sorted(ROOT.glob("*.py")):
        if f.name.startswith("__"):
            continue
        try:
            if fix_file(f):
                patched.append(f.name)
        except Exception as e:
            print("Failed", f.name, e)
    if patched:
        print("Fixed files:", patched)
    else:
        print("No fixes needed.")

if __name__ == "__main__":
    main()


