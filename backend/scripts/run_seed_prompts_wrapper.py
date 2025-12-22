#!/usr/bin/env python3
"""
Wrapper to run seed_prompts_from_disk with repo root on sys.path.
Use this to avoid ModuleNotFoundError when running as a script.
"""
import sys
from pathlib import Path

# Insert backend directory so `app` package (backend/app) is importable as top-level `app`
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from backend.scripts import seed_prompts_from_disk as seed_module


def main():
    return seed_module.main()


if __name__ == "__main__":
    raise SystemExit(main())


