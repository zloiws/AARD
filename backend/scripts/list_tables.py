#!/usr/bin/env python3
from app.core.config import get_settings
from sqlalchemy import create_engine, text


def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
        )).fetchall()
        print([r[0] for r in rows])

if __name__ == "__main__":
    main()


