"""
Collect an inventory of LLM call sites in the codebase.

This script is intentionally stdlib-only and conservative:
- It parses Python files with `ast` when possible.
- On SyntaxError, it falls back to regex-based line scanning.

Output:
- Markdown table with one row per detected call site.
- A small summary markdown with counts per classification, task_type, and prompt/system usage flags.

Usage (from repo root):
  python tools/collect_llm_calls.py --root backend/app --out docs/llm_calls_inventory.md --summary docs/inventory_summary.md
"""

from __future__ import annotations

import argparse
import ast
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

LLM_ATTR_NAMES = {"generate", "chat", "complete", "completions"}
SYSTEM_PROMPT_KW = {"system_prompt", "system", "messages"}
PROMPTY_SYMBOLS = {"PromptService", "PromptType", "prompt_service", "prompt_type"}


@dataclass(frozen=True)
class CallSite:
    file: str
    line: int
    container: str
    call: str
    task_type: str
    has_system_prompt: str  # "yes" | "no" | "unknown"
    prompt_source: str      # "inline" | "prompt_service" | "unknown"
    classification: str     # "component" | "agent" | "tool" | "infra" | "utility" | "unknown"


def _classify_by_path(rel_path: str) -> str:
    p = rel_path.replace("\\", "/")
    if "/agents/" in p:
        return "agent"
    if "/api/routes/" in p:
        return "infra"
    if "/scripts/" in p or p.endswith("_script.py") or "/tmp_" in p:
        return "utility"
    if "/core/" in p:
        return "infra"
    if "/services/" in p:
        # Services are a mixed bag in this repo; start with unknown to avoid false certainty.
        return "unknown"
    return "unknown"


def _safe_source_segment(src: str, node: ast.AST) -> str:
    try:
        seg = ast.get_source_segment(src, node)
        if seg:
            return " ".join(seg.split())
    except Exception:
        pass
    return "<unavailable>"


def _extract_task_type_from_call(call: ast.Call) -> str:
    # Try keywords first: task_type=TaskType.PLANNING
    for kw in call.keywords or []:
        if kw.arg == "task_type":
            v = kw.value
            # TaskType.X
            if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name):
                if v.value.id == "TaskType":
                    return f"TaskType.{v.attr}"
            # String literal
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                return v.value
            return ast.dump(v, include_attributes=False)
    return "unknown"


def _infer_has_system_prompt(call: ast.Call, src: str) -> str:
    # Conservative: only "yes" when explicit system prompt / system message is present.
    for kw in call.keywords or []:
        if kw.arg in ("system_prompt",):
            return "yes"
        if kw.arg == "messages":
            # Look for role="system" in a literal list/dict.
            if isinstance(kw.value, (ast.List, ast.Tuple)):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Dict):
                        for k, v in zip(elt.keys, elt.values):
                            if isinstance(k, ast.Constant) and k.value == "role":
                                if isinstance(v, ast.Constant) and v.value == "system":
                                    return "yes"
    # If call uses messages kw but can't confirm, keep unknown
    for kw in call.keywords or []:
        if kw.arg in SYSTEM_PROMPT_KW:
            return "unknown"
    return "no"


def _infer_prompt_source(call_src: str) -> str:
    # Rough heuristic for Phase 0: detect prompt service symbols in same call expression.
    for sym in PROMPTY_SYMBOLS:
        if sym in call_src:
            return "prompt_service"
    # Most calls pass inline `prompt=...` strings; still unknown if variable.
    if "prompt=" in call_src or "messages=" in call_src:
        return "inline"
    return "unknown"


class _ContainerTracker(ast.NodeVisitor):
    def __init__(self, src: str, rel_path: str):
        self.src = src
        self.rel_path = rel_path
        self._stack: List[str] = []
        self.calls: List[CallSite] = []

    def _current_container(self) -> str:
        return ".".join(self._stack) if self._stack else "<module>"

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        # Detect `.generate(...)` / `.chat(...)` etc.
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in LLM_ATTR_NAMES:
            call_src = _safe_source_segment(self.src, node)
            task_type = _extract_task_type_from_call(node)
            has_system_prompt = _infer_has_system_prompt(node, self.src)
            prompt_source = _infer_prompt_source(call_src)
            self.calls.append(
                CallSite(
                    file=self.rel_path,
                    line=getattr(node, "lineno", 1),
                    container=self._current_container(),
                    call=call_src,
                    task_type=task_type,
                    has_system_prompt=has_system_prompt,
                    prompt_source=prompt_source,
                    classification=_classify_by_path(self.rel_path),
                )
            )
        self.generic_visit(node)


def _iter_py_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        # Skip venv-like folders defensively
        parts = {x.lower() for x in p.parts}
        if "venv" in parts or "__pycache__" in parts:
            continue
        yield p


def _regex_fallback_scan(src: str, rel_path: str) -> List[CallSite]:
    rows: List[CallSite] = []
    for i, line in enumerate(src.splitlines(), start=1):
        if ".generate(" in line or ".chat(" in line:
            call_src = " ".join(line.strip().split())
            task_type = "unknown"
            m = re.search(r"task_type\s*=\s*TaskType\.([A-Z_]+)", line)
            if m:
                task_type = f"TaskType.{m.group(1)}"
            has_system_prompt = "unknown" if "messages=" in line else "no"
            prompt_source = "inline" if "prompt=" in line or "messages=" in line else "unknown"
            rows.append(
                CallSite(
                    file=rel_path,
                    line=i,
                    container="<unknown>",
                    call=call_src,
                    task_type=task_type,
                    has_system_prompt=has_system_prompt,
                    prompt_source=prompt_source,
                    classification=_classify_by_path(rel_path),
                )
            )
    return rows


def collect_calls(root: Path, repo_root: Path) -> List[CallSite]:
    calls: List[CallSite] = []
    for py in _iter_py_files(root):
        rel = str(py.relative_to(repo_root))
        try:
            src = py.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            src = py.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
            v = _ContainerTracker(src, rel)
            v.visit(tree)
            calls.extend(v.calls)
        except SyntaxError:
            calls.extend(_regex_fallback_scan(src, rel))
    # Stable sort for deterministic output
    calls.sort(key=lambda c: (c.file, c.line, c.container, c.call))
    return calls


def _md_table(rows: List[CallSite]) -> str:
    headers = ["file", "line", "container", "classification", "task_type", "has_system_prompt", "prompt_source", "call"]
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        d = asdict(r)
        values = []
        for h in headers:
            v = str(d[h])
            v = v.replace("\n", " ").replace("|", "\\|")
            # Keep table readable
            if h == "call" and len(v) > 160:
                v = v[:157] + "..."
            values.append(v)
        out.append("| " + " | ".join(values) + " |")
    return "\n".join(out) + "\n"


def _summarize(rows: List[CallSite]) -> str:
    def count_by(key_fn):
        m: Dict[str, int] = {}
        for r in rows:
            k = key_fn(r)
            m[k] = m.get(k, 0) + 1
        return dict(sorted(m.items(), key=lambda kv: (-kv[1], kv[0])))

    by_class = count_by(lambda r: r.classification)
    by_task = count_by(lambda r: r.task_type)
    by_system = count_by(lambda r: r.has_system_prompt)
    by_prompt_src = count_by(lambda r: r.prompt_source)

    def fmt(d: Dict[str, int]) -> str:
        return "\n".join([f"- {k}: {v}" for k, v in d.items()]) + "\n"

    return (
        "# LLM Calls Inventory — Summary\n\n"
        f"Total call sites: **{len(rows)}**\n\n"
        "## By classification\n\n"
        + fmt(by_class)
        + "\n## By task_type\n\n"
        + fmt(by_task)
        + "\n## By has_system_prompt\n\n"
        + fmt(by_system)
        + "\n## By prompt_source\n\n"
        + fmt(by_prompt_src)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="backend/app", help="Root directory to scan (default: backend/app)")
    ap.add_argument("--out", default="docs/llm_calls_inventory.md", help="Markdown output path")
    ap.add_argument("--summary", default="docs/inventory_summary.md", help="Summary markdown output path")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    root = (repo_root / args.root).resolve()
    out_path = (repo_root / args.out).resolve()
    summary_path = (repo_root / args.summary).resolve()

    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")

    rows = collect_calls(root=root, repo_root=repo_root)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(
        "# LLM Calls Inventory\n\n"
        "Generated by `tools/collect_llm_calls.py`.\n\n"
        + _md_table(rows),
        encoding="utf-8",
    )
    summary_path.write_text(_summarize(rows), encoding="utf-8")

    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"Wrote summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


