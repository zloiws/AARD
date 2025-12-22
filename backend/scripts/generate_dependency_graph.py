#!/usr/bin/env python3
"""
Generate import dependency graph for backend/app modules.
Writes:
 - backend/docs/dependency_graph.dot
 - backend/docs/dependency_graph.png (if `dot` available)
 - backend/docs/services_inventory.json

The script groups modules by the first two path components under `app`
(e.g. `app.api.routes` -> `app.api`) to keep the graph readable.
"""
import ast
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
OUT_DIR = ROOT / "docs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def module_from_path(py_path: Path) -> str:
    # convert backend/app/.../file.py -> app....file
    rel = py_path.relative_to(ROOT)
    parts = rel.with_suffix("").parts
    return ".".join(parts)


def top_group(module_name: str) -> str:
    # expects names starting with "app"
    parts = module_name.split(".")
    if len(parts) >= 2:
        return ".".join(parts[:2])
    return module_name


def collect_imports() -> dict:
    edges = defaultdict(lambda: defaultdict(int))
    examples = defaultdict(lambda: defaultdict(list))
    nodes = set()

    for py in APP_DIR.rglob("*.py"):
        if py.match("**/__pycache__/**"):
            continue
        try:
            src = py.read_text(encoding="utf-8")
        except Exception:
            continue
        try:
            tree = ast.parse(src)
        except Exception:
            continue

        src_module = module_from_path(py)  # e.g. app.api.routes.chat
        src_group = top_group(src_module)
        nodes.add(src_group)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module
                if not mod:
                    continue
                if mod.startswith("app."):
                    tgt_group = top_group(mod)
                    edges[src_group][tgt_group] += 1
                    examples[src_group][tgt_group].append(str(py.relative_to(ROOT)))
                    nodes.add(tgt_group)
                elif mod == "app":
                    edges[src_group]["app"] += 1
                    examples[src_group]["app"].append(str(py.relative_to(ROOT)))
                    nodes.add("app")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name.startswith("app."):
                        tgt_group = top_group(name)
                        edges[src_group][tgt_group] += 1
                        examples[src_group][tgt_group].append(str(py.relative_to(ROOT)))
                        nodes.add(tgt_group)
                    elif name == "app":
                        edges[src_group]["app"] += 1
                        examples[src_group]["app"].append(str(py.relative_to(ROOT)))
                        nodes.add("app")

    return {"nodes": sorted(nodes), "edges": edges, "examples": examples}


def write_dot(nodes, edges, out_path: Path):
    lines = ["digraph imports {", "  rankdir=LR;", "  node [shape=box];"]
    for n in nodes:
        safe = n.replace(".", "_")
        lines.append(f'  "{safe}" [label="{n}"];')

    for src, targets in edges.items():
        src_safe = src.replace(".", "_")
        for tgt, weight in targets.items():
            tgt_safe = tgt.replace(".", "_")
            lines.append(f'  "{src_safe}" -> "{tgt_safe}" [label="{weight}"];')

    lines.append("}")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_json(nodes, edges, examples, out_path: Path):
    data = {"nodes": nodes, "edges": []}
    for src, targets in edges.items():
        for tgt, weight in targets.items():
            data["edges"].append(
                {"source": src, "target": tgt, "weight": weight, "examples": examples[src][tgt][:3]}
            )
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def try_render_dot(dot_path: Path, png_path: Path) -> bool:
    try:
        subprocess.run(["dot", "-V"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        print("Graphviz `dot` not available; skipping PNG render.")
        return False
    try:
        subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], check=True)
        return True
    except Exception as exc:
        print("Failed to render PNG:", exc)
        return False


def main():
    print("Scanning imports in", APP_DIR)
    result = collect_imports()
    nodes = result["nodes"]
    edges = result["edges"]
    examples = result["examples"]

    dot_path = OUT_DIR / "dependency_graph.dot"
    png_path = OUT_DIR / "dependency_graph.png"
    json_path = OUT_DIR / "services_inventory.json"

    write_dot(nodes, edges, dot_path)
    write_json(nodes, edges, examples, json_path)
    rendered = try_render_dot(dot_path, png_path)

    print("Wrote:", dot_path)
    print("Wrote:", json_path)
    if rendered:
        print("Wrote:", png_path)
    else:
        print("PNG not created.")


if __name__ == "__main__":
    main()


