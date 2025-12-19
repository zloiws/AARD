from app.core.database import engine
from sqlalchemy import text


def main():
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("Ensured vector extension")
        except Exception as e:
            print("vector extension create failed:", e)
        try:
            conn.execute(text("ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS embedding vector(768)"))
            print("Added embedding column")
        except Exception as e:
            print("Add embedding failed:", e)
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_memories_embedding_hnsw ON agent_memories USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"))
            print("Created hnsw index (or skipped if unsupported)")
        except Exception as e:
            print("Index creation possibly unsupported:", e)

if __name__ == '__main__':
    main()


