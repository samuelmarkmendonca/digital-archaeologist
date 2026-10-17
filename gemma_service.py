"""Gemma AI Archaeology Service for Digital Archaeologist.

Harnesses Google's open-weights Gemma models (Gemma 4 / Gemma 3) and Gemini API via the Google GenAI SDK.
Combines deterministic token-optimized Knowledge Graph pre-compression with Gemma's semantic reasoning
to produce executive architectural summaries, identify undocumented behaviors, and synthesize
resurrection guides for unfamiliar and dormant codebases.
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Gemma track models prioritized, with resilient fallback
GEMMA_MODELS = [
    "gemma-4-26b-a4b-it",  # Gemma 4 26B Flagship
    "gemma-4-31b-it",      # Gemma 4 31B Dense
    "gemma-3-27b-it",      # Gemma 3 27B
    "gemini-2.5-flash",    # Cloud fallback if Gemma rate-limited
    "gemini-1.5-flash",    # Legacy fallback
]
DEFAULT_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")


def _build_archaeology_prompt(
    repo_info: dict[str, Any],
    readme_text: str,
    graph_data: dict[str, Any],
) -> str:
    """Construct a dense, pre-compressed, token-optimized archaeological synthesis prompt for Gemma."""
    repo_name = repo_info.get("name", "Unknown repository")
    repo_desc = repo_info.get("description") or "No description provided."
    repo_lang = repo_info.get("language") or "Mixed / Unspecified"

    # Pre-compressed knowledge graph representation designed specifically for Gemma
    condensed_nodes = [
        {
            "file": n["path"],
            "type": n["type"],
            "language": n["language"],
            "exports": n["exports"],
            "imports": n["imports"],
            "undocumented_behaviors": n.get("undocumented_behaviors", []),
        }
        for n in graph_data.get("nodes", [])[:35]
    ]

    condensed_edges = [
        {"from": e["source"], "to": e["target"], "rel": e.get("relation", "imports")}
        for e in graph_data.get("edges", [])[:40]
    ]

    token_stats = graph_data.get("token_stats", {})

    prompt_parts = [
        "You are an expert software systems archaeologist and reverse-engineering specialist powered by Gemma.",
        "",
        "## Mission",
        "A developer has encountered an unfamiliar, dormant, or long-abandoned codebase.",
        "Instead of dumping raw source files (which wastes thousands of tokens), you are given a token-optimized Knowledge Graph",
        f"that reduces token overhead by {token_stats.get('token_reduction_percent', '90%+')} while preserving full architectural topology.",
        "Your task is to reconstruct how the system actually works, map dependencies, identify undocumented behavior,",
        "and produce a navigable, crisp technical explanation in Markdown format.",
        "",
        "## Repository Overview",
        f"- Repository: {repo_name}",
        f"- Description: {repo_desc}",
        f"- Primary Language: {repo_lang}",
        f"- Default Branch: {repo_info.get('default_branch', 'main')}",
        "",
        "## README Artifact (Excerpt):",
        "```markdown",
        (readme_text[:2500] if readme_text else "No README file found in repository."),
        "```",
        "",
        "## Token-Optimized Codebase Topology & Detected Elements:",
        "```json",
        json.dumps({"nodes": condensed_nodes, "edges": condensed_edges}, indent=2),
        "```",
        "",
        "## Markdown Report Guidelines",
        "Generate a structured Markdown report with EXACTLY the following 5 sections:",
        "",
        "### 1. 🏛️ System Overview & Purpose",
        "In 2 tight paragraphs, explain what this project actually does, how the system works at a high level, and its core domain.",
        "",
        "### 2. 🧩 Architectural Topology & Dependency Map",
        "Detail how the modules identified in the Knowledge Graph divide responsibilities and interact. Trace how data and control pass between them.",
        "",
        "### 3. 🚀 Entry Points & Execution Lifecycle",
        "Highlight the detected entry points (e.g. main/app scripts, API routers, CLI entrypoints, or background workers) and trace the execution path from startup to shutdown.",
        "",
        "### 4. 🕵️ Undocumented Behavior & Hidden Gotchas",
        "Identify surprising, unwritten, or undocumented behaviors in this codebase: hidden environment variable lookups, hardcoded host/port configurations, implicit side effects, silent exception handling, or circular dependencies.",
        "",
        "### 5. 🧭 Project Resurrection Guide",
        "Provide an actionable, step-by-step checklist for a developer dusting off this project: required runtime/dependencies, configuration files to create (.env, configs), key files to inspect first, and areas with potential technical debt.",
        "",
        "## Grounding Rules:",
        "- Rely strictly on the supplied Knowledge Graph, detected quirks, and README.",
        "- Be factual and technical. Do not invent non-existent packages or files.",
    ]

    return "\n".join(prompt_parts)


def _generate_deterministic_fallback_summary(
    repo_info: dict[str, Any],
    readme_text: str,
    graph_data: dict[str, Any],
) -> str:
    """Generate an informative, deterministic markdown archaeology report when offline or API key is absent."""
    repo_name = repo_info.get("name", "Unknown Repository")
    repo_desc = repo_info.get("description") or "Open-source codebase."
    repo_lang = repo_info.get("language") or "Mixed"
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    token_stats = graph_data.get("token_stats", {})

    entry_points = [n for n in nodes if n.get("is_entrypoint")]
    configs = [n for n in nodes if n.get("type") == "config"]
    services = [n for n in nodes if n.get("type") == "service"]
    quirky_nodes = [n for n in nodes if n.get("undocumented_behaviors")]

    # Build fallback markdown
    md = [
        f"> 💡 *Deterministic Archaeological Analysis (Token Optimization: **{token_stats.get('token_reduction_percent', '92%')}** savings)*",
        "",
        "### 1. 🏛️ System Overview & Purpose",
        f"**{repo_name}** is a **{repo_lang}** software repository. {repo_desc}",
        f"The codebase contains **{len(nodes)}** analyzed source files with **{len(edges)}** detected module dependencies.",
        "",
        "### 2. 🧩 Architectural Topology & Dependency Map",
        f"The architecture is organized into **{len(entry_points)}** entry points, **{len(services)}** service/handler modules, and **{len(configs)}** configuration manifests.",
        f"- **Module Interconnections**: {len(edges)} cross-file import relations mapped deterministically in the Cytoscape.js Knowledge Graph.",
        f"- **Core Components**: {', '.join(n['filename'] for n in nodes[:8])}",
        "",
        "### 3. 🚀 Entry Points & Execution Lifecycle",
    ]

    if entry_points:
        for ep in entry_points:
            exports = f" (Exports: `{', '.join(ep['exports'][:4])}`)" if ep["exports"] else ""
            md.append(f"- **`{ep['path']}`** ({ep['language']}): Primary execution candidate{exports}.")
    else:
        md.append("- No canonical entry points (e.g. `main.py`, `app.py`, `index.js`) detected. Codebase likely serves as a library or utility suite.")

    md.extend([
        "",
        "### 4. 🕵️ Undocumented Behavior & Hidden Gotchas",
    ])

    if quirky_nodes:
        for qn in quirky_nodes[:6]:
            quirks = " • ".join(qn["undocumented_behaviors"])
            md.append(f"- **`{qn['path']}`**: {quirks}")
    else:
        md.append("- No obvious hidden environment lookups or dangerous code execution patterns flagged in initial AST scan.")

    first_files = ", ".join(f"`{ep['path']}`" for ep in entry_points[:3]) if entry_points else "Top-level source files"
    md.extend([
        "",
        "### 5. 🧭 Project Resurrection Guide",
        "1. **Environment Setup**: Inspect manifests (`requirements.txt`, `package.json`, `pyproject.toml`) for exact dependency pins.",
        "2. **Configuration**: Check for undeclared environment variables listed above before initiating local execution.",
        f"3. **First Files to Inspect**: {first_files}.",
        "4. **AI Agent Context**: The accompanying Cytoscape.js Knowledge Graph JSON can be provided directly to external coding assistants for complete architectural context.",
    ])

    return "\n".join(md)


def generate_archaeology_summary(
    repo_info: dict[str, Any],
    readme_text: str,
    graph_data: dict[str, Any],
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """Execute Gemma archaeological synthesis with smart fallback across Gemma models."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or key.strip() == "" or "your_" in key.lower():
        fallback_md = _generate_deterministic_fallback_summary(repo_info, readme_text, graph_data)
        banner = (
            "> ℹ️ **Notice: Running in Deterministic Mode** (No `GEMINI_API_KEY` provided)\n"
            "> Enter your Google Gemini/Gemma API key in the sidebar or `.env` to unlock deep semantic reasoning by Gemma.\n\n"
        )
        return banner + fallback_md

    primary_model = model or os.getenv("GEMMA_MODEL") or DEFAULT_MODEL

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        fallback_md = _generate_deterministic_fallback_summary(repo_info, readme_text, graph_data)
        return "> ⚠️ `google-genai` SDK not detected. Displaying deterministic analysis:\n\n" + fallback_md

    prompt = _build_archaeology_prompt(repo_info, readme_text, graph_data)

    gen_config = types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.9,
    )

    client = genai.Client(api_key=key.strip())

    models_to_try = [primary_model] + [m for m in GEMMA_MODELS if m != primary_model]

    last_error = ""
    for candidate_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=candidate_model,
                contents=prompt,
                config=gen_config,
            )
            if response and response.text:
                header = f"> 🧠 *Synthesized by **{candidate_model}** with token-optimized context*\n\n"
                return header + response.text
        except Exception as e:
            last_error = str(e)
            continue

    # If all Gemma/Gemini attempts failed, provide deterministic report + error message
    fallback_md = _generate_deterministic_fallback_summary(repo_info, readme_text, graph_data)
    error_notice = (
        f"> ⚠️ **Gemma API Call Notice** (Attempted: `{models_to_try[:2]}`):\n"
        f"> *{last_error[:180]}*\n"
        "> Showing deterministic archaeological report below:\n\n"
    )
    return error_notice + fallback_md
