"""Gemma AI Archaeology Service for Digital Archaeologist.

Harnesses Google's open-weights Gemma models (Gemma 4 / Gemma 3) via the Google GenAI SDK.
Smartly combines deterministic Knowledge Graph pre-compression with Gemma's semantic reasoning
to produce executive architectural summaries and token-optimized AI agent context payloads.
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Fixed to Gemma track models
GEMMA_MODELS = [
    "gemma-4-26b-a4b-it",  # Gemma 4 26B Flagship
    "gemma-4-31b-it",      # Gemma 4 31B Dense
    "gemma-3-27b-it",      # Gemma 3 27B Legacy
]
DEFAULT_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")


def _build_archaeology_prompt(
    repo_info: dict[str, Any],
    readme_text: str,
    graph_data: dict[str, Any],
) -> str:
    """Construct a dense, pre-compressed archaeological synthesis prompt for Gemma."""
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
        }
        for n in graph_data.get("nodes", [])[:35]
    ]

    condensed_edges = graph_data.get("edges", [])[:40]

    prompt_parts = [
        "You are an expert codebase archaeologist and software systems architect powered by Gemma.",
        "",
        "## Context & Mission",
        "A developer or team has returned to a long-abandoned or inherited project.",
        "Instead of reading raw source files, you are provided with a pre-computed Codebase Knowledge Graph.",
        "Analyze the repository structure, entry points, and dependency topology to produce an architectural resurrection report.",
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
        "## Codebase Knowledge Graph Topology:",
        "```json",
        json.dumps({"nodes": condensed_nodes, "edges": condensed_edges}, indent=2),
        "```",
        "",
        "## Report Guidelines",
        "Produce a structured Markdown report with EXACTLY these 5 sections:",
        "",
        "### 1. 🏛️ Executive Codebase Summary",
        "In 2 paragraphs, explain what this project actually does, its core purpose, and target domain.",
        "",
        "### 2. 🧩 Architectural Topology & Module Breakdown",
        "Explain how the major components and files identified in the Knowledge Graph connect and divide responsibilities.",
        "",
        "### 3. 🚀 Entry Points & Execution Lifecycle",
        "Identify the primary entry points (e.g. main/app scripts, APIs, CLIs, or UI components) and trace the execution path.",
        "",
        "### 4. 🧭 Project Resurrection Guide",
        "Give actionable advice for a developer dusting off this abandoned code: dependencies to check, key files to inspect first, and likely areas of tech debt.",
        "",
        "### 5. 🤖 Token-Efficient AI Agent Context Prompt",
        "Provide a compact, copy-pasteable context block (inside a markdown fence) that can be passed to external AI coding agents so they understand the whole architecture without reading raw files.",
        "",
        "## Grounding Rules:",
        "- Rely strictly on the supplied Knowledge Graph nodes, edges, and README.",
        "- Do not hallucinate non-existent modules or classes.",
    ]

    return "\n".join(prompt_parts)


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
        return (
            "> ⚠️ **Gemini API Key Required for Gemma Synthesis**\n\n"
            "To view the Gemma-generated Codebase Resurrection Guide and AI agent context prompt, "
            "set your `GEMINI_API_KEY` in your `.env` file or enter it in the app sidebar.\n\n"
            "The **Knowledge Graph**, **dependency topology**, and **token reduction metrics** "
            "are completely functional without an API key!"
        )

    primary_model = model or os.getenv("GEMMA_MODEL") or DEFAULT_MODEL

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return (
            "> ⚠️ **`google-genai` SDK Not Installed**\n\n"
            "Run `.venv\\Scripts\\pip install google-genai` to enable Gemma analysis."
        )

    prompt = _build_archaeology_prompt(repo_info, readme_text, graph_data)

    # Smart Gemma Harnessing: Low temperature for grounded architectural analysis
    gen_config = types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.9,
    )

    client = genai.Client(api_key=key.strip())

    # Candidate sequence of Gemma models for resilient fallback
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
                prefix = f"> 🧠 *Synthesized by **{candidate_model}***\n\n" if candidate_model != primary_model else ""
                return prefix + response.text
        except Exception as e:
            last_error = str(e)
            # If 429 quota or 404 model not found, attempt next Gemma model in sequence
            continue

    # If all Gemma attempts failed, provide descriptive notice
    if "RESOURCE_EXHAUSTED" in last_error or "429" in last_error:
        return (
            "> ⏳ **Gemma API Rate Limit Reached (429)**\n\n"
            "The Gemma API quota was temporarily reached. Please wait a moment and re-excavate."
        )
    if "API_KEY_INVALID" in last_error or "400" in last_error and "key" in last_error.lower():
        return (
            "> ❌ **Invalid API Key**\n\n"
            "The provided `GEMINI_API_KEY` is not valid. Verify your key at https://aistudio.google.com/."
        )
    return (
        f"> ⚠️ **Gemma Synthesis Unavailable**: Encountered error across Gemma models:\n\n"
        f"```text\n{last_error}\n```\n\n"
        "You can still inspect the interactive Knowledge Graph and token economics below."
    )
