from app.core.database import engine
from sqlalchemy import text


def main():
    with engine.begin() as conn:
        try:
            conn.execute(text("DROP INDEX IF EXISTS ix_execution_traces_trace_id"))
            print("Dropped unique ix_execution_traces_trace_id")
        except Exception as e:
            print("Failed to drop unique index:", e)
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_traces_trace_id ON execution_traces (trace_id)"))
            print("Created non-unique idx_traces_trace_id")
        except Exception as e:
            print("Failed to create idx_traces_trace_id:", e)

if __name__ == '__main__':
    main()


