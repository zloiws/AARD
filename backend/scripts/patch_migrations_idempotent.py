import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "alembic" / "versions"

create_table_pattern = re.compile(r"op\.create_table\(\s*['\"](?P<table>[\w_]+)['\"]", re.MULTILINE)

def patch_file(path: Path):
    text = path.read_text(encoding="utf-8")
    # If file already patched (contains our guard), skip
    if "select to_regclass" in text:
        return False

    def repl(match):
        table = match.group("table")
        select_stmt = f"select to_regclass('public.{table}')"
        guard = (
            "conn = op.get_bind()\n"
            f"    if not conn.execute(sa.text({select_stmt!r})).scalar():\n"
            "        op.create_table("
        )
        return guard

    new_text, count = create_table_pattern.subn(repl, text)
    if count > 0:
        path.write_text(new_text, encoding="utf-8")
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
        print("Patched files:", patched)
    else:
        print("No files patched.")

if __name__ == "__main__":
    main()


