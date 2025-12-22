"""CLI for database migrations and maintenance wrappers."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cmd_migrate(args):
    """Run alembic upgrade head using existing run_alembic_upgrade.py if present."""
    # Prefer to reuse existing script to minimize behavior changes
    script = ROOT / "run_alembic_upgrade.py"
    if script.exists():
        print("Using existing run_alembic_upgrade.py to perform upgrade")
        # import as module to reuse logic
        import run_alembic_upgrade as runner  # type: ignore

        runner.main()
        return 0
    else:
        print("No run_alembic_upgrade.py found; calling alembic via subprocess")
        import subprocess

        return subprocess.call([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=str(ROOT))


def cmd_check(args):
    """Run DB checks (wrap existing check scripts)."""
    script = ROOT / "check_tables.py"
    if script.exists():
        print("Running check_tables.py")
        import check_tables as checker  # type: ignore

        checker.main()
        return 0
    else:
        print("No check_tables.py found; nothing to run")
        return 0


def cmd_stamp(args):
    """Stamp alembic revision (pass-through to alembic stamp)."""
    import subprocess

    rev = args.revision or "head"
    return subprocess.call([sys.executable, "-m", "alembic", "stamp", rev], cwd=str(ROOT))


def cmd_repair(args):
    """Repair common issues (e.g., remove stale locks)."""
    # Best-effort: show instructions rather than attempt destructive fixes.
    print("Repair helper:")
    print(" - If locks exist in Chocolatey or other tools, remove them manually.")
    print(" - For alembic conflicts, consider creating merge migrations.")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="migrations")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("migrate", help="Run migrations (upgrade head)")
    s.set_defaults(func=cmd_migrate)
    s = sub.add_parser("check", help="Run DB checks")
    s.set_defaults(func=cmd_check)
    s = sub.add_parser("stamp", help="Stamp alembic to a revision")
    s.add_argument("--revision", "-r", help="Revision to stamp", default="head")
    s.set_defaults(func=cmd_stamp)
    s = sub.add_parser("repair", help="Show repair guidance")
    s.set_defaults(func=cmd_repair)
    return p


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, "func"):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())


