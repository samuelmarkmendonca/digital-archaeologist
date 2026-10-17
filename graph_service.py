"""Knowledge Graph Generation Service for Digital Archaeologist.

Parses repository file trees, manifests, and source code to construct a dense,
token-efficient structural knowledge graph formatted specifically in Cytoscape.js JSON,
with robust multi-language import resolution, dependency mapping, and undocumented behavior detection.
"""

from __future__ import annotations

import json
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
    ".sql": "SQL",
}

ENTRY_POINT_NAMES = {
    "main.py", "app.py", "index.py", "server.py", "wsgi.py", "asgi.py", "cli.py",
    "manage.py", "run.py", "index.js", "index.ts", "app.js", "app.ts", "server.js",
    "server.ts", "main.go", "main.rs", "lib.rs", "index.html", "entrypoint.sh"
}

IGNORED_DIRECTORIES = {
    "node_modules", "vendor", "venv", ".venv", "env", ".git", ".github",
    "dist", "build", "target", "__pycache__", ".next", ".cache", "site-packages"
}


def is_relevant_file(path: str) -> bool:
    """Check if file should be part of the codebase graph."""
    parts = path.split("/")
    if any(p in IGNORED_DIRECTORIES or (p.startswith(".") and p not in (".", "..")) for p in parts):
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in LANGUAGE_EXTENSIONS or os.path.basename(path).lower() in ("dockerfile", "makefile")


def detect_undocumented_behaviors(content: str, filename: str, ext: str) -> list[str]:
    """Inspect file content for undocumented behaviors, hidden gotchas, and quirks.
    
    Identifies:
    - Undeclared or hidden environment variables
    - Hardcoded IPs, ports, and dev bindings
    - Dangerous dynamic execution (eval, exec, reflection)
    - Silent exception swallowing (except: pass)
    - Forced debug / test bypasses
    """
    quirks: list[str] = []
    if not content:
        return quirks

    # 1. Hidden environment variable lookups
    env_matches = re.findall(
        r"(?:os\.environ\.get\(['\"]([A-Za-z0-9_]+)['\"]|os\.environ\[['\"]([A-Za-z0-9_]+)['\"]|os\.getenv\(['\"]([A-Za-z0-9_]+)['\"]|process\.env\.([A-Za-z0-9_]+))",
        content,
    )
    found_envs = {m for group in env_matches for m in group if m}
    if found_envs:
        quirks.append(f"Reads hidden env var(s): {', '.join(sorted(found_envs)[:4])}")

    # 2. Hardcoded network host/port bindings
    if re.search(r"0\.0\.0\.0|127\.0\.0\.1|localhost:\d+", content):
        quirks.append("Contains hardcoded localhost / 0.0.0.0 network binding")

    # 3. Dynamic evaluation / code execution
    if re.search(r"\b(eval|exec|__import__)\s*\(", content):
        quirks.append("Uses dynamic code execution (`eval` / `exec` / `__import__`)")

    # 4. Silent exception swallowing
    if re.search(r"except(?:\s+[A-Za-z0-9_]+)?\s*:\s*(?:pass|\.\.\.)", content):
        quirks.append("Silently swallows exceptions (`except: pass`) without logging")
    elif re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", content):
        quirks.append("Silently swallows errors with empty catch block")

    # 5. Debug mode hardcoded enabled
    if re.search(r"\bdebug\s*=\s*True\b", content, re.IGNORECASE):
        quirks.append("Has hardcoded `debug=True` flag enabled")

    # 6. Global mutable state
    if re.search(r"^\s*global\s+[A-Za-z0-9_]+", content, re.MULTILINE):
        quirks.append("Relies on global mutable state (`global` keyword)")

    return quirks[:4]


def parse_imports_and_symbols(content: str, ext: str) -> tuple[list[str], list[str]]:
    """Robust regex parser to extract imported modules, submodules, and declared symbols."""
    imports: list[str] = []
    symbols: list[str] = []

    if not content:
        return imports, symbols

    if ext == ".py":
        for raw_line in content.splitlines():
            line = raw_line.strip()
            
            # 1. from <module> import <symbols> (handles relative imports like from .models, from . import utils)
            m_from = re.match(r"^from\s+([A-Za-z0-9_\.]+)\s+import\s+(.+)$", line)
            if m_from:
                mod = m_from.group(1).strip()
                imported = m_from.group(2).strip()
                # Relative import like 'from . import utils'
                if mod.replace(".", "") == "":
                    for sym in imported.split(","):
                        clean_sym = sym.strip().split()[0]
                        if clean_sym and clean_sym not in imports:
                            imports.append(clean_sym)
                else:
                    # e.g. .models -> models, requests.adapters -> adapters, requests
                    for sub in mod.split("."):
                        if sub and sub not in imports:
                            imports.append(sub)
                continue

            # 2. import <module> [as alias], <module2>
            m_imp = re.match(r"^import\s+([A-Za-z0-9_\.,\s]+)$", line)
            if m_imp:
                for item in m_imp.group(1).split(","):
                    mod_part = item.strip().split()[0]
                    for sub in mod_part.split("."):
                        if sub and sub not in imports:
                            imports.append(sub)
                continue

            # 3. Class and function symbols
            m_sym = re.match(r"^\s*(?:def|class)\s+([A-Za-z0-9_]+)", raw_line)
            if m_sym:
                sym = m_sym.group(1)
                if not sym.startswith("_") and sym not in symbols:
                    symbols.append(sym)

    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        for raw_line in content.splitlines():
            line = raw_line.strip()
            # ESM: import ... from './foo' or '../bar'
            m_esm = re.search(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]", line)
            if m_esm:
                src = m_esm.group(1)
                base = os.path.basename(src).split(".")[0]
                if base and base not in imports:
                    imports.append(base)
            # CommonJS: require('./foo')
            m_cjs = re.search(r"require\(['\"]([^'\"]+)['\"]\)", line)
            if m_cjs:
                src = m_cjs.group(1)
                base = os.path.basename(src).split(".")[0]
                if base and base not in imports:
                    imports.append(base)
            # Symbols
            m_sym = re.search(r"(?:export\s+(?:default\s+)?(?:class|function|const|let)\s+([A-Za-z0-9_]+)|class\s+([A-Za-z0-9_]+))", line)
            if m_sym:
                sym = m_sym.group(1) or m_sym.group(2)
                if sym and sym not in symbols:
                    symbols.append(sym)

    elif ext == ".go":
        for match in re.finditer(r"import\s+(?:\(\s*([^)]+)\s*\)|['\"]([^'\"]+)['\"])", content):
            block = match.group(1) or match.group(2) or ""
            for line in block.splitlines():
                clean = line.strip().strip('"').split("/")[-1]
                if clean and clean not in imports:
                    imports.append(clean)
        for match in re.finditer(r"^func\s+(?:\([^)]+\)\s+)?([A-Za-z0-9_]+)|^type\s+([A-Za-z0-9_]+)\s+struct", content, re.MULTILINE):
            sym = match.group(1) or match.group(2)
            if sym and sym not in symbols:
                symbols.append(sym)

    elif ext == ".rs":
        for match in re.finditer(r"use\s+([A-Za-z0-9_:]+);", content):
            for part in match.group(1).split("::"):
                if part and part not in ("crate", "self", "super") and part not in imports:
                    imports.append(part)
        for match in re.finditer(r"pub\s+(?:fn|struct|enum)\s+([A-Za-z0-9_]+)", content):
            sym = match.group(1)
            if sym and sym not in symbols:
                symbols.append(sym)

    return imports[:15], symbols[:12]


def build_knowledge_graph(
    repo_name: str,
    tree_entries: list[dict[str, Any]],
    file_contents: dict[str, str],
) -> dict[str, Any]:
    """Construct an interconnected knowledge graph formatted in Cytoscape.js JSON.

    Calculates deterministic token economics and establishes multi-tier edge matching
    (sibling directories, relative paths, and package module lookups).
    """
    relevant_files = [e["path"] for e in tree_entries if e.get("type") == "blob" and is_relevant_file(e.get("path", ""))]

    # Map file paths to exact byte sizes provided by GitHub's Git Tree API
    file_sizes = {e["path"]: e.get("size", 0) for e in tree_entries if e.get("type") == "blob"}

    total_raw_bytes = 0

    for path in relevant_files:
        filename = os.path.basename(path)
        ext = os.path.splitext(filename)[1].lower()
        language = LANGUAGE_EXTENSIONS.get(ext, "Other")
        is_entry = filename in ENTRY_POINT_NAMES or path.lower() in ("main.py", "app.py", "src/index.js", "src/main.rs", "src/requests/__init__.py")
        
        content = file_contents.get(path, "")
        # Use exact GitHub blob byte size if available, fallback to content length
        file_bytes = file_sizes.get(path, 0)
        total_raw_bytes += file_bytes if file_bytes > 0 else (len(content) if content else 1500)

        imports, symbols = parse_imports_and_symbols(content, ext)
        undocumented = detect_undocumented_behaviors(content, filename, ext)

        if is_entry:
            node_type = "entrypoint"
        elif ext in (".json", ".yaml", ".yml", ".toml", ".env", ".dockerfile") or filename.lower() in ("dockerfile", "makefile"):
            node_type = "config"
        elif any(k in path.lower() for k in ("service", "api", "handler", "controller", "session", "adapter")):
            node_type = "service"
        elif any(k in path.lower() for k in ("util", "helper", "common", "tool", "compat", "structure")):
            node_type = "util"
        else:
            node_type = "module"

        node = {
            "id": path,
            "filename": filename,
            "path": path,
            "type": node_type,
            "language": language,
            "exports": symbols,
            "imports": imports,
            "size_bytes": file_bytes,
        }
        all_nodes.append(node)
        node_by_id[path] = node

    # Multi-tier lookup index for edge resolution
    lookup_map: dict[str, list[str]] = {}
    for n in all_nodes:
        path = n["path"]
        fn = n["filename"]
        base = os.path.splitext(fn)[0].lower()
        for key in (path.lower(), fn.lower(), base):
            if key not in lookup_map:
                lookup_map[key] = []
            if path not in lookup_map[key]:
                lookup_map[key].append(path)

    # Resolve edges
    edges: list[dict[str, Any]] = []
    edge_pairs: set[tuple[str, str]] = set()
    node_degrees: dict[str, int] = {n["id"]: 0 for n in all_nodes}

    for node in all_nodes:
        src_id = node["id"]
        src_dir = os.path.dirname(src_id)

        for imp in node["imports"]:
            imp_clean = imp.strip().lower()
            if not imp_clean or imp_clean in ("__future__", "typing", "sys", "os", "re", "json", "time"):
                continue

            target_id = None

            # 1. Sibling file in same directory (e.g. src/requests/models.py)
            for ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs"):
                sibling_candidate = f"{src_dir}/{imp_clean}{ext}".lstrip("/")
                if sibling_candidate in node_by_id and sibling_candidate != src_id:
                    target_id = sibling_candidate
                    break

            # 2. Direct basename lookup (e.g. 'models' -> matching node)
            if not target_id and imp_clean in lookup_map:
                candidates = [cid for cid in lookup_map[imp_clean] if cid != src_id]
                if candidates:
                    # Pick candidate closest to source directory
                    candidates.sort(
                        key=lambda c: (os.path.dirname(c) == src_dir, -len(os.path.commonprefix([c, src_id]))),
                        reverse=True,
                    )
                    target_id = candidates[0]

            # 3. Path substring match (e.g. 'requests/models' or 'services/auth')
            if not target_id:
                for n_id in node_by_id:
                    if n_id != src_id:
                        lower_id = n_id.lower()
                        if f"/{imp_clean}." in f"/{lower_id}" or lower_id.endswith(f"/{imp_clean}"):
                            target_id = n_id
                            break

            if target_id and target_id != src_id:
                pair = (src_id, target_id)
                if pair not in edge_pairs:
                    edge_pairs.add(pair)
                    edge_id = f"e_{src_id.replace('/', '_')}_to_{target_id.replace('/', '_')}"
                    edges.append({
                        "id": edge_id,
                        "source": src_id,
                        "target": target_id,
                        "relation": "imports",
                    })
                    node_degrees[src_id] = node_degrees.get(src_id, 0) + 1
                    node_degrees[target_id] = node_degrees.get(target_id, 0) + 1

    # Filter out empty orphan nodes that have no content and no edges,
    # ensuring the rendered graph is clean, focused, and densely interconnected.
    display_nodes = [
        n for n in all_nodes
        if node_degrees.get(n["id"], 0) > 0 or n["has_content"] or n["is_entrypoint"] or n["type"] == "config"
    ]
    # If still too many nodes, bound to top 45 most relevant for UI responsiveness
    if len(display_nodes) > 45:
        display_nodes.sort(key=lambda n: (n["is_entrypoint"], node_degrees.get(n["id"], 0), n["has_content"]), reverse=True)
        display_nodes = display_nodes[:45]

    # Generate visual Mermaid graph representation
    mermaid_lines = ["graph TD"]
    display_nodes = nodes[:25]
    display_ids = {n["id"] for n in display_nodes}
    active_edges = [e for e in edges if e["source"] in display_ids and e["target"] in display_ids]

    # Re-calculate degrees for display
    active_degrees = {n["id"]: 0 for n in display_nodes}
    for e in active_edges:
        active_degrees[e["source"]] = active_degrees.get(e["source"], 0) + 1
        active_degrees[e["target"]] = active_degrees.get(e["target"], 0) + 1

    # Format Cytoscape.js JSON
    cyto_nodes = []
    for n in display_nodes:
        quirks_str = "; ".join(n["undocumented_behaviors"]) if n["undocumented_behaviors"] else "None detected"
        cyto_nodes.append({
            "data": {
                "id": n["id"],
                "label": n["filename"],
                "filename": n["filename"],
                "path": n["path"],
                "type": n["type"],
                "language": n["language"],
                "exports": n["exports"],
                "imports": n["imports"],
                "undocumented_behaviors": n["undocumented_behaviors"],
                "undocumented_str": quirks_str,
                "degree": active_degrees.get(n["id"], 0),
            }
        })

    cyto_edges = []
    for e in active_edges:
        cyto_edges.append({
            "data": {
                "id": e["id"],
                "source": e["source"],
                "target": e["target"],
                "label": e["relation"],
                "relation": e["relation"],
            }
        })

    cytoscape_elements_dict = {
        "nodes": cyto_nodes,
        "edges": cyto_edges,
    }

    cytoscape_elements_flat = cyto_nodes + cyto_edges

    cytoscape_json = {
        "format": "cytoscape.js",
        "version": "3.x",
        "repository": repo_name,
        "elements": cytoscape_elements_dict,
    }

    # Standard LLM BPE tokenization metric (~4 bytes/chars per token in code)
    raw_tokens_estimate = max(1000, total_raw_bytes // 4)
    # The Knowledge Graph is serialized into dense JSON
    graph_chars = len(json.dumps(nodes)) + len(json.dumps(edges))
    graph_tokens_estimate = max(400, graph_chars // 4)
    savings_pct = max(0.0, round((1.0 - (graph_tokens_estimate / raw_tokens_estimate)) * 100, 1))
    savings_factor = round(raw_tokens_estimate / max(1, graph_tokens_estimate), 1)

    total_quirks = sum(len(n["undocumented_behaviors"]) for n in display_nodes)

    # Format Cytoscape.js elements
    cytoscape_elements = generate_cytoscape_elements(nodes, edges)

    return {
        "repository": repo_name,
        "summary_metrics": {
            "total_files_analyzed": len(display_nodes),
            "total_dependencies": len(active_edges),
            "entry_points_detected": sum(1 for n in display_nodes if n["is_entrypoint"]),
            "undocumented_quirks_detected": total_quirks,
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

