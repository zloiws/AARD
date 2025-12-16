"""
Seed prompts from disk (prompts/components/*.system) into DB as Prompt records.

Idempotent: will not create duplicate prompt names; will create a new version if text differs.

Usage:
  python backend/scripts/seed_prompts_from_disk.py
"""
from pathlib import Path
import json
from datetime import datetime

from app.core.database import get_session_local
from app.services.prompt_service import PromptService
from app.models.prompt import PromptType


def load_prompt_files(root: Path) -> dict:
    prompts = {}
    pdir = root / "prompts" / "components"
    if not pdir.exists():
        return prompts
    for f in pdir.glob("*.system"):
        name = f.stem  # filename without extension
        text = f.read_text(encoding="utf-8")
        prompts[name] = text
    return prompts


def main():
    repo_root = Path(__file__).resolve().parents[2]
    prompts = load_prompt_files(repo_root)
    if not prompts:
        print("No prompts found in prompts/components/")
        return 0

    SessionLocal = get_session_local()
    db = SessionLocal()
    svc = PromptService(db)
    created = 0
    updated = 0

    try:
        for name, text in prompts.items():
            # Normalize name: use the filename as prompt name
            # Use PromptService.get_latest_version to check
            latest = svc.get_latest_version(name)
            if not latest:
                # Create new prompt
                svc.create_prompt(name=name, prompt_text=text, prompt_type=PromptType.SYSTEM, level=0, created_by="seed_script")
                created += 1
                print(f"Created prompt: {name}")
            else:
                if latest.prompt_text.strip() != text.strip():
                    # create a new version
                    svc.create_version(parent_prompt_id=latest.id, prompt_text=text, created_by="seed_script")
                    updated += 1
                    print(f"Created new version for prompt: {name} (was v{latest.version})")
                else:
                    print(f"No change for prompt: {name} (v{latest.version})")
        print(f"Done. Created: {created}, Updated: {updated}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())


