from app.core.database import get_engine
from sqlalchemy import text

def main():
    eng = get_engine()
    with eng.connect() as conn:
        try:
            r = conn.execute(text("select to_regclass('public.plan_templates')")).fetchone()
            print('plan_templates exists:', r[0])
        except Exception as e:
            print('Error checking plan_templates:', e)
        try:
            v = conn.execute(text("select version_num from alembic_version")).fetchall()
            print('alembic_version rows:', [row[0] for row in v])
        except Exception as e:
            print('Could not read alembic_version:', e)

if __name__ == '__main__':
    main()

