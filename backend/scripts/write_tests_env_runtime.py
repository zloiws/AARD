import sys
from pathlib import Path

# Ensure backend dir is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings

settings = get_settings()

keys = {
    "POSTGRES_HOST": settings.postgres_host,
    "POSTGRES_PORT": str(settings.postgres_port),
    "POSTGRES_DB": settings.postgres_db,
    "POSTGRES_USER": settings.postgres_user,
    "POSTGRES_PASSWORD": settings.postgres_password,
    "SECRET_KEY": settings.secret_key,
    "OLLAMA_URL_1": settings.ollama_url_1,
    "OLLAMA_MODEL_1": settings.ollama_model_1,
}

out = "\n".join(f"{k}={v}" for k, v in keys.items() if v is not None)

tests_env = Path(__file__).resolve().parents[1] / "tests" / ".env"
tests_env.parent.mkdir(parents=True, exist_ok=True)
tests_env.write_text(out, encoding="utf-8")
print(f"Wrote {tests_env} with {len(out.splitlines())} entries")


