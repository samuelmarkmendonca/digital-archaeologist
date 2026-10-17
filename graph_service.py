"""Knowledge Graph Generation Service for Digital Archaeologist.

Parses repository file trees, manifests, and source code to construct a dense,
token-efficient structural knowledge graph (nodes and edges) designed for
downstream AI coding agents and returning developers.
"""

from __future__ import annotations

import os
import re
from typing import Any

# Standard source code extensions and language mapping
LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React (JS)",
    ".tsx": "React (TS)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".sh": "Shell",
}

ENTRY_POINT_NAMES = {
    "main.py", "app.py", "index.py", "server.py", "wsgi.py", "asgi.py",
    "index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts",
    "main.go", "main.rs", "lib.rs", "index.html"
}

IGNORED_DIRECTORIES = {
    "node_modules", "vendor", "venv", ".venv", "env", ".git", ".github",
    "dist", "build", "target", "__pycache__", ".next", ".cache", "site-packages"
}


def _is_relevant_file(path: str) -> bool:
    """Check if file should be part of the codebase graph."""
    parts = path.split("/")
    if any(p in IGNORED_DIRECTORIES or (p.startswith(".") and p not in (".", "..")) for p in parts):
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in LANGUAGE_EXTENSIONS or os.path.basename(path).lower() in ("dockerfile", "makefile")


def parse_imports_and_symbols(content: str, ext: str) -> tuple[list[str], list[str]]:
    """Lightweight regex parser to extract imported modules and declared symbols."""
    imports: list[str] = []
    symbols: list[str] = []

    if not content:
        return imports, symbols

    if ext == ".py":
        # Python imports: import foo, from foo.bar import baz
        for match in re.finditer(r"^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\.,\s]+))", content, re.MULTILINE):
            mod = match.group(1) or match.group(2)
            if mod:
                for m in mod.split(","):
                    clean = m.strip().split()[0].split(".")[0]
                    if clean and clean not in imports:
                        imports.append(clean)

        # Python classes and functions
        for match in re.finditer(r"^\s*(?:def|class)\s+([A-Za-z0-9_]+)", content, re.MULTILINE):
            sym = match.group(1)
            if not sym.startswith("_") and sym not in symbols:
                symbols.append(sym)

    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        # JS/TS imports: import ... from './foo' or require('./foo')
        for match in re.finditer(r"(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))", content):
            src = match.group(1) or match.group(2)
            if src:
                clean = os.path.basename(src).split(".")[0]
                if clean and clean not in imports:
                    imports.append(clean)

        # JS/TS functions and classes
        for match in re.finditer(r"(?:export\s+(?:default\s+)?(?:class|function|const|let)\s+([A-Za-z0-9_]+)|class\s+([A-Za-z0-9_]+))", content):
            sym = match.group(1) or match.group(2)
            if sym and sym not in symbols:
                symbols.append(sym)

    return imports[:8], symbols[:10]


def build_knowledge_graph(
    repo_name: str,
    tree_entries: list[dict[str, Any]],
    file_contents: dict[str, str],
) -> dict[str, Any]:
    """Construct a connected knowledge graph of nodes and edges from repository files.

    Returns:
        dict: {
            'repository': str,
            'summary_metrics': dict,
            'nodes': list[dict],
            'edges': list[dict],
            'mermaid_diagram': str,
            'token_stats': dict
        }
    """
    relevant_files = [e["path"] for e in tree_entries if e.get("type") == "blob" and _is_relevant_file(e.get("path", ""))]

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_id_map: dict[str, str] = {}

    # Map file paths to exact byte sizes provided by GitHub's Git Tree API
    file_sizes = {e["path"]: e.get("size", 0) for e in tree_entries if e.get("type") == "blob"}

    total_raw_bytes = 0

    for path in relevant_files:
        filename = os.path.basename(path)
        ext = os.path.splitext(filename)[1].lower()
        language = LANGUAGE_EXTENSIONS.get(ext, "Other")
        is_entry = filename in ENTRY_POINT_NAMES or path.lower() in ("main.py", "app.py", "src/index.js")
        
        content = file_contents.get(path, "")
        # Use exact GitHub blob byte size if available, fallback to content length
        file_bytes = file_sizes.get(path, 0)
        total_raw_bytes += file_bytes if file_bytes > 0 else (len(content) if content else 1500)

        imports, symbols = parse_imports_and_symbols(content, ext)

        node_type = "entrypoint" if is_entry else ("module" if ext in (".py", ".js", ".ts", ".go", ".rs") else "config")
        node_id = path

        node = {
            "id": node_id,
            "filename": filename,
            "path": path,
            "type": node_type,
            "language": language,
            "exports": symbols,
            "imports": imports,
            "size_bytes": file_bytes,
        }
        nodes.append(node)
        node_id_map[filename.split(".")[0].lower()] = node_id

    # Construct edges based on imports matching internal files or folders
    edge_pairs: set[tuple[str, str]] = set()
    for node in nodes:
        src_id = node["id"]
        for imp in node["imports"]:
            target_key = imp.lower()
            if target_key in node_id_map and node_id_map[target_key] != src_id:
                target_id = node_id_map[target_key]
                pair = (src_id, target_id)
                if pair not in edge_pairs:
                    edge_pairs.add(pair)
                    edges.append({
                        "source": src_id,
                        "target": target_id,
                        "relation": "imports",
                    })

    # Generate visual Mermaid graph representation
    mermaid_lines = ["graph TD"]
    display_nodes = nodes[:25]
    display_ids = {n["id"] for n in display_nodes}

    for n in display_nodes:
        clean_id = re.sub(r"[^A-Za-z0-9_]", "_", n["id"])
        label = f"{n['filename']}<br/>({n['language']})"
        if n["type"] == "entrypoint":
            mermaid_lines.append(f'    {clean_id}["🚀 {label}"]')
            mermaid_lines.append(f"    style {clean_id} fill:#2ea44f,stroke:#1b7c31,color:#fff")
        else:
            mermaid_lines.append(f'    {clean_id}["📄 {label}"]')

    for edge in edges:
        if edge["source"] in display_ids and edge["target"] in display_ids:
            src_clean = re.sub(r"[^A-Za-z0-9_]", "_", edge["source"])
            tgt_clean = re.sub(r"[^A-Za-z0-9_]", "_", edge["target"])
            mermaid_lines.append(f"    {src_clean} -->|imports| {tgt_clean}")

    mermaid_diagram = "\n".join(mermaid_lines)

    # Standard LLM BPE tokenization metric (~4 bytes/chars per token in code)
    raw_tokens_estimate = max(1000, total_raw_bytes // 4)
    # The Knowledge Graph is serialized into dense JSON
    graph_chars = len(json.dumps(nodes)) + len(json.dumps(edges))
    graph_tokens_estimate = max(400, graph_chars // 4)
    savings_pct = max(0.0, round((1.0 - (graph_tokens_estimate / raw_tokens_estimate)) * 100, 1))

    # Format Cytoscape.js elements
    cytoscape_elements = generate_cytoscape_elements(nodes, edges)

    return {
        "repository": repo_name,
        "summary_metrics": {
            "total_files_analyzed": len(nodes),
            "total_dependencies": len(edges),
            "entry_points_detected": sum(1 for n in nodes if n["type"] == "entrypoint"),
        },
        "nodes": nodes,
        "edges": edges,
        "mermaid_diagram": mermaid_diagram,
        "cytoscape_elements": cytoscape_elements,
        "token_stats": {
            "raw_codebase_bytes": total_raw_bytes,
            "raw_codebase_tokens": raw_tokens_estimate,
            "knowledge_graph_tokens": graph_tokens_estimate,
            "token_reduction_percent": f"{savings_pct}%",
            "methodology": "Based on GitHub Git Tree blob byte sizes and BPE tokenization (~4 bytes/chars per token).",
        },
    }


def generate_cytoscape_elements(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], max_nodes: int = 40) -> list[dict[str, Any]]:
    """Format nodes and edges into the Cytoscape.js data schema for interactive visualization."""
    elements: list[dict[str, Any]] = []

    # Prioritize entrypoints first, up to max_nodes to keep visualization smooth
    selected_nodes = sorted(nodes, key=lambda n: (0 if n["type"] == "entrypoint" else 1))[:max_nodes]
    selected_ids = {n["id"] for n in selected_nodes}

    for n in selected_nodes:
        elements.append({
            "data": {
                "id": n["id"],
                "label": n["filename"],
                "path": n["path"],
                "type": n["type"],
                "language": n["language"],
                "exports": ", ".join(n["exports"][:4]) if n["exports"] else "None",
                "imports": ", ".join(n["imports"][:4]) if n["imports"] else "None",
            }
        })

    for e in edges:
        if e["source"] in selected_ids and e["target"] in selected_ids:
            elements.append({
                "data": {
                    "id": f"{e['source']}->{e['target']}",
                    "source": e["source"],
                    "target": e["target"],
                    "relation": e.get("relation", "imports"),
                }
            })

    return elements

