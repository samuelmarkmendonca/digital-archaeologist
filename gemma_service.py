"""Google Gemini / Gemma AI Integration Service for Digital Archaeologist (RepoRescue).

Constructs strictly grounded prompts with factual repository context, issue text,
and verified source snippets, preventing hallucinations while generating structured
triage guides.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

# Load local environment variables from .env
load_dotenv()

DEFAULT_MODEL = os.getenv("GEMMA_MODEL", "gemini-2.5-flash")


def _build_prompt(repo_info: dict[str, Any], issue: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    """Build a grounded prompt for the Gemini/Gemma model."""
    repo_name = repo_info.get("name", "Unknown repository")
    repo_desc = repo_info.get("description") or "No description provided."
    repo_lang = repo_info.get("language") or "Not specified"

    issue_title = issue.get("title", "Untitled issue")
    issue_body = issue.get("body", "") or "No issue description provided."
    issue_num = issue.get("number", 0)

    prompt_parts = [
        "You are an expert open-source triage companion and developer onboarding assistant.",
        "",
        "## Context",
        f"- Repository: {repo_name} (Language: {repo_lang})",
        f"- Repository Description: {repo_desc}",
        f"- Issue #{issue_num}: {issue_title}",
        "",
        "### Issue Description:",
        "```markdown",
        issue_body[:4000],  # Bound issue body to protect context
        "```",
        "",
        "## Candidate Source Files",
        "The following files were selected by a deterministic keyword-ranking engine based on the issue description.",
        "Inspect ONLY the supplied paths and code snippets below:",
        "",
    ]

    for idx, candidate in enumerate(candidates, start=1):
        path = candidate.get("path", "unknown")
        reason = candidate.get("reason", "N/A")
        snippet = candidate.get("snippet", "[No snippet available]")

        prompt_parts.extend([
            f"### Candidate {idx}: `{path}`",
            f"- **Ranking Rationale**: {reason}",
            "- **Code Snippet**:",
            "```",
            snippet,
            "```",
            "",
        ])

    prompt_parts.extend([
        "## Instructions",
        "Generate a structured, evidence-grounded markdown response following EXACTLY these 5 sections:",
        "",
        "### 1. Plain-English Issue Summary",
        "Summarize the problem in 1–2 clear sentences for a newcomer.",
        "",
        "### 2. Code Observations",
        "State what the supplied code snippets actually show (factual observations only, e.g. functions, classes, imports, configs).",
        "",
        "### 3. Relevance to Issue",
        "Explain why each candidate file may be involved in or affected by the reported problem.",
        "",
        "### 4. Concrete Next Investigation Steps",
        "Provide 3 to 5 actionable steps the developer should take next (e.g. specific tests to run, functions to inspect, logs or breakpoints to set).",
        "",
        "### 5. What Cannot Be Determined",
        "List what cannot be confirmed or diagnosed from the supplied snippets alone without running the code or examining other files.",
        "",
        "## Strict Grounding Rules:",
        "- ONLY reference the files, symbols, and snippets supplied above.",
        "- DO NOT invent non-existent file names, imaginary line numbers, or test results.",
        "- DO NOT claim the bug is confirmed, solved, or diagnosed.",
        "- Maintain a clear distinction between verified code facts and working hypotheses.",
    ])

    return "\n".join(prompt_parts)


def analyze_issue_with_gemma(
    repo_info: dict[str, Any],
    issue: dict[str, Any],
    candidates: list[dict[str, Any]],
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """Send structured prompt to Gemini / Gemma with factual repository context,

    issue text, and actual file snippets. Returns grounded Markdown analysis.

    Falls back cleanly with an informative message if the API key is missing
    or network/quota errors occur.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or key.strip() == "" or "your_" in key.lower():
        return (
            "> ⚠️ **Gemini API Key Required for AI Analysis**\n\n"
            "To view the AI-generated Code Trail synthesis and action checklist, set your `GEMINI_API_KEY` "
            "in your `.env` file or enter it in the app sidebar.\n\n"
            "The deterministic candidate files and snippets above are completely functional without an API key!"
        )

    model_name = model or os.getenv("GEMMA_MODEL") or DEFAULT_MODEL

    try:
        from google import genai
    except ImportError:
        return (
            "> ⚠️ **`google-genai` SDK Not Installed**\n\n"
            "Run `.venv\\Scripts\\pip install google-genai` to enable AI analysis."
        )

    prompt = _build_prompt(repo_info, issue, candidates)

    try:
        client = genai.Client(api_key=key.strip())
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        if response and response.text:
            return response.text
        return "> ⚠️ Gemini returned an empty response. Please retry in a moment."
    except Exception as e:
        err_msg = str(e)
        if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
            return (
                "> ⏳ **API Rate Limit Reached (429)**\n\n"
                "The Gemini API quota was temporarily exceeded. Please wait a minute and re-run your investigation."
            )
        if "API_KEY_INVALID" in err_msg or "400" in err_msg and "key" in err_msg.lower():
            return (
                "> ❌ **Invalid Gemini API Key**\n\n"
                "The provided `GEMINI_API_KEY` is not valid. Verify your key at https://aistudio.google.com/."
            )
        return (
            f"> ⚠️ **AI Analysis Unavailable**: Encountered an error while contacting the model ({model_name}):\n\n"
            f"```text\n{err_msg}\n```\n\n"
            "You can still inspect the ranked candidate files and code snippets directly above."
        )
