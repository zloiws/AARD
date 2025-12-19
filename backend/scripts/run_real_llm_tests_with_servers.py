#!/usr/bin/env python3
"""
Discover models on given Ollama servers, pick one model per server (first loaded),
export environment variables for settings, and run selected integration tests with real LLMs.

Usage: python -u backend/scripts/run_real_llm_tests_with_servers.py
"""
import os
import sys
import subprocess
import json
from urllib.parse import urljoin

import httpx

SERVERS = [
    "http://10.39.0.101:11434",
    "http://10.39.0.6:11434",
]

TEST_FILES = [
    "backend/tests/integration/test_agent_dialogs_real_llm.py",
    "backend/tests/integration/test_planning_with_dialogs.py",
]


def get_models_for_server(base_url: str):
    """Call /api/ps to retrieve loaded models, return list of names"""
    try:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            normalized = normalized[:-3]
        url = urljoin(normalized + "/", "api/ps")
        with httpx.Client(base_url=normalized, timeout=10.0) as client:
            r = client.get("/api/ps", timeout=10.0)
            r.raise_for_status()
            data = r.json()
            models = data.get("models") or []
            return [m.get("name") for m in models if m.get("name")]
    except Exception:
        return []


def main():
    print("Discovering models on configured Ollama servers...")
    models = []
    for s in SERVERS:
        m = get_models_for_server(s)
        print(f"{s} -> models: {m}")
        models.append((s, m))

    # Choose first model for each server, fallback to 'default' if none
    chosen = []
    for idx, (s, mlist) in enumerate(models, start=1):
        if mlist:
            chosen_model = mlist[0]
        else:
            chosen_model = None
        chosen.append((s, chosen_model))

    # Prepare env vars
    env = os.environ.copy()
    if chosen[0][1]:
        env["OLLAMA_URL_1"] = chosen[0][0]
        env["OLLAMA_MODEL_1"] = chosen[0][1]
        print(f"Using server1 {chosen[0][0]} model {chosen[0][1]}")
    else:
        print("Warning: no model found on server1")
    if len(chosen) > 1 and chosen[1][1]:
        env["OLLAMA_URL_2"] = chosen[1][0]
        env["OLLAMA_MODEL_2"] = chosen[1][1]
        print(f"Using server2 {chosen[1][0]} model {chosen[1][1]}")
    else:
        print("Warning: no model found on server2")

    # Disable tracing for tests
    env["ENABLE_TRACING"] = "0"
    # Request seeding of Ollama servers into test DB
    env["SEED_OLLAMA_SERVERS"] = "1"

    # Run pytest as subprocess so settings are read fresh
    cmd = [sys.executable, "-u", "-m", "pytest"] + TEST_FILES + ["-q", "-s"]
    print("Running pytest:", " ".join(cmd))
    proc = subprocess.run(cmd, env=env)
    return proc.returncode


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)


