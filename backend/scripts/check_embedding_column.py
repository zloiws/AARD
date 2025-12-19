from app.core.database import get_engine
from sqlalchemy import text


def main():
    engine = get_engine()
    with engine.connect() as conn:
        res = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'agent_memories';"
        ))
        rows = res.fetchall()
        if not rows:
            print("No table agent_memories found or no columns returned")
            return
        for r in rows:
            print(r.column_name, r.data_type)

if __name__ == "__main__":
    main()


