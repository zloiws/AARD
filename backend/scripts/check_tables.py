import sys
from pathlib import Path

from sqlalchemy import text

# ensure backend dir on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, get_engine


def main():
    engine = get_engine()
    expected = sorted(Base.metadata.tables.keys())
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
        )).fetchall()
        actual = sorted([r[0] for r in rows])

    expected_set = set(expected)
    actual_set = set(actual)

    missing = sorted(list(expected_set - actual_set))
    extra = sorted(list(actual_set - expected_set))

    print("Expected tables (from models):", len(expected), expected)
    print("Actual tables in DB:", len(actual), actual)
    print("Missing tables:", missing)
    print("Extra tables (in DB but not in models):", extra)

    # Return non-zero exit if missing critical tables
    if missing:
        print("Some expected tables are missing.")
        sys.exit(2)
    print("All expected tables present.")

if __name__ == '__main__':
    main()


