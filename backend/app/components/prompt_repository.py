"""
File-backed prompt repository for prompt-centric components.

Note: The repo currently uses DB-backed prompts in many places. This repository is a
non-invasive bridge to introduce explicit prompt artifacts on disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class ComponentPromptRepository:
    def __init__(self, prompts_root: Optional[Path] = None):
        # Default: <repo_root>/prompts/components
        if prompts_root is None:
            repo_root = Path(__file__).resolve().parents[3]  # backend/app/components -> repo root
            prompts_root = repo_root / "prompts" / "components"
        self.prompts_root = prompts_root

    def get_system_prompt(self, component_name: str) -> str:
        path = self.prompts_root / f"{component_name}.system"
        return path.read_text(encoding="utf-8")


