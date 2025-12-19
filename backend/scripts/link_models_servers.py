import os

from sqlalchemy import create_engine, text


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE ollama_models SET server_id = (SELECT id FROM ollama_servers WHERE url LIKE '%10.39.0.6%') WHERE model_name LIKE '%huihui_ai/qwen3-vl-abliterated%';"))
        conn.execute(text("UPDATE ollama_models SET server_id = (SELECT id FROM ollama_servers WHERE url LIKE '%10.39.0.101%') WHERE model_name LIKE '%qwen3:8b%';"))
    print("Linked models to servers")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


