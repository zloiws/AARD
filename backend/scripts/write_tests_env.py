import os
from pathlib import Path

keys = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "SECRET_KEY",
    "OLLAMA_URL_1",
    "OLLAMA_MODEL_1",
]

out = []
for k in keys:
    v = os.environ.get(k)
    if v is not None:
        out.append(f"{k}={v}")

tests_env = Path(__file__).resolve().parents[1] / "tests" / ".env"
tests_env.parent.mkdir(parents=True, exist_ok=True)
tests_env.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {tests_env} with {len(out)} entries")


