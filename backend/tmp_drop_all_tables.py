from app.core.database import engine
from sqlalchemy import inspect, text


def main():
    insp = inspect(engine)
    tables = [t for t in insp.get_table_names() if t != 'alembic_version']
    if not tables:
        print("No tables to drop.")
        return
    with engine.begin() as conn:
        for t in tables:
            print(f"Dropping table {t}")
            conn.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))
    print("Dropped all tables (except alembic_version).")

if __name__ == "__main__":
    main()


