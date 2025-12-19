#!/usr/bin/env python3
"""
Activate specific Ollama servers and models for integration tests.
Marks servers by host (10.39.0.6, 10.39.0.101) and models by name as active.
Run from project root: .\\venv\\Scripts\\python.exe backend\\scripts\\activate_models.py
"""
from app.core.config import get_settings
from sqlalchemy import create_engine, text


def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        # Activate servers by host or url substring
        conn.execute(
            text(
                "UPDATE ollama_servers SET is_active = TRUE "
                "WHERE host IN ('10.39.0.6','10.39.0.101') "
                "OR server_url LIKE '%10.39.0.6%' OR server_url LIKE '%10.39.0.101%';"
            )
        )

        # Activate models by exact model name
        conn.execute(
            text(
                "UPDATE ollama_models SET is_active = TRUE "
                "WHERE model IN ('huihui_ai/qwen3-vl-abliterated:8b-instruct','qwen3:8b');"
            )
        )

        # Print verification rows
        rows = conn.execute(
            text(
                "SELECT s.host AS server_host, s.server_url AS server_url, s.is_active AS server_active, "
                "m.model AS model_name, m.is_active AS model_active "
                "FROM ollama_servers s LEFT JOIN ollama_models m ON m.server_id = s.id "
                "WHERE s.host IN ('10.39.0.6','10.39.0.101') "
                "OR s.server_url LIKE '%10.39.0.6%' OR s.server_url LIKE '%10.39.0.101%' "
                "OR m.model IN ('huihui_ai/qwen3-vl-abliterated:8b-instruct','qwen3:8b');"
            )
        ).fetchall()

        for r in rows:
            print(dict(r))


if __name__ == "__main__":
    main()


