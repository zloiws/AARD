from app.core.database import get_engine
from sqlalchemy import text

def main():
    eng = get_engine()
    with eng.connect() as conn:
        try:
            cols = conn.execute(text(\"\"\"select column_name, data_type from information_schema.columns where table_name='plan_templates';\"\"\")).fetchall()
            print('columns:')
            for c in cols:
                print(' -', c[0], c[1])
        except Exception as e:
            print('Error fetching columns:', e)
        try:
            cnt = conn.execute(text('select count(*) from plan_templates;')).fetchone()[0]
            print('rows in plan_templates:', cnt)
        except Exception as e:
            print('Could not count rows:', e)

if __name__ == '__main__':
    main()

