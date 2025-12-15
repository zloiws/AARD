from app.core.database import engine
from sqlalchemy import text

def main():
    with engine.begin() as conn:
        print("Renaming agents -> agents_old (if exists)")
        conn.execute(text("ALTER TABLE IF EXISTS agents RENAME TO agents_old"))
        print("Done")

if __name__ == "__main__":
    main()


