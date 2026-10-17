"""Deterministic Candidate Ranking Module for Digital Archaeologist (RepoRescue).

Scores repository tree entries against issue descriptions using keyword extraction,
path segmentation, and weighted frequency matching without AI hallucination.
"""

from __future__ import annotations

import os
import re
from typing import Any

# Standard English stopwords + non-discriminating issue / code terms
STOPWORDS = {
    # English common words
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor",
    "not", "now", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should", "shouldn't",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "were",
    "weren't", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "won't", "would", "wouldn't", "you", "your", "yours", "yourself",
    # Non-differentiating issue vocabulary
    "issue", "bug", "error", "problem", "failed", "failure", "fix", "fixed",
    "reproduce", "expected", "actual", "behavior", "version", "step", "steps",
    "help", "please", "using", "github", "repo", "repository", "code", "line",
    "lines", "file", "files", "project", "def", "class", "function", "return",
    "true", "false", "none", "null", "undefined", "import", "package",
}

# Ignored binary, media, lock, and compiled file extensions
IGNORED_EXTENSIONS = {
    # Images & Media & Design files
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".mp4", ".mp3",
    ".ai", ".psd", ".sketch", ".fig",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Data & Archives
    ".lock", ".sum", ".csv", ".tsv", ".parquet", ".zip", ".tar", ".gz", ".7z",
    # Binaries & Compiled
    ".pyc", ".pyo", ".pyd", ".exe", ".dll", ".so", ".dylib", ".wasm", ".class",
    ".o", ".obj", ".bin",
    # Minified assets & maps
    ".min.js", ".min.css", ".map",
    # Marker files & static txt
    ".typed",
}

# Recognized source code file extensions to prioritize
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh",
}


def _split_into_tokens(text: str) -> list[str]:
    """Tokenize string into lowercase alphanumeric words, splitting snake_case,

    camelCase, and kebab-case.
    """
    if not text:
        return []

    # Insert space before camelCase capitals (e.g. "authService" -> "auth Service")
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    # Split on non-alphanumeric characters (slashes, underscores, dots, hyphens, spaces)
    raw_tokens = re.findall(r"[A-Za-z0-9]+", s1)
    
    # Filter short tokens and lowercase
    return [t.lower() for t in raw_tokens if len(t) >= 2]


def extract_keywords(issue_text: str) -> dict[str, int]:
    """Extract informative keywords from issue text with term frequencies."""
    tokens = _split_into_tokens(issue_text)
    freqs: dict[str, int] = {}
    for tok in tokens:
        if tok not in STOPWORDS and not tok.isdigit():
            freqs[tok] = freqs.get(tok, 0) + 1
    return freqs


def _is_candidate_file(path: str) -> bool:
    """Determine if a file path is a valid source code candidate."""
    lower_path = path.lower()
    
    # Check ignored extensions
    for ext in IGNORED_EXTENSIONS:
        if lower_path.endswith(ext):
            return False

    # Ignore hidden folders/files (.git, .github, etc.)
    segments = lower_path.split("/")
    for seg in segments:
        if seg.startswith(".") and seg not in (".", ".."):
            return False

    # Ignore marker / typestub files
    base = os.path.basename(lower_path)
    if base in ("py.typed", ".gitkeep", ".keep", ".gitignore"):
        return False

    # Ignore docs and vendor/node_modules directories
    if any(x in segments for x in ("vendor", "node_modules", "dist", "build", "site-packages", "docs")):
        return False

    return True


def rank_candidate_files(
    issue_text: str,
    tree_entries: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Score file paths against keywords extracted from the issue title and body.

    Args:
        issue_text: Concatenated issue title and body (or title given extra weight).
        tree_entries: List of git tree entries with 'path' and 'type' keys.
        limit: Maximum number of ranked candidates to return (default: 3).

    Returns:
        List of candidate dictionaries:
        [
            {
                'path': 'src/auth/login.py',
                'score': 12,
                'reason': 'Matches keywords: auth, login'
            },
            ...
        ]
    """
    if not issue_text or not tree_entries:
        return []

    keyword_weights = extract_keywords(issue_text)
    if not keyword_weights:
        return []

    scored_candidates: list[dict[str, Any]] = []

    for entry in tree_entries:
        path = entry.get("path", "")
        if not path or not _is_candidate_file(path):
            continue

        filename = os.path.basename(path)
        filename_no_ext, ext = os.path.splitext(filename)
        path_tokens = _split_into_tokens(path)
        filename_tokens = set(_split_into_tokens(filename_no_ext))

        matched_terms: set[str] = set()
        score = 0

        for token in path_tokens:
            if token in keyword_weights:
                term_weight = keyword_weights[token]
                matched_terms.add(token)

                # Base score proportional to keyword frequency in issue
                score += 3 + min(term_weight, 5)

                # Bonus points if the match is in the file's own basename
                if token in filename_tokens:
                    score += 5

        # Exact filename match bonus (e.g. issue talks about "auth.py")
        if filename_no_ext.lower() in keyword_weights:
            score += 10
            matched_terms.add(filename_no_ext.lower())

        # Prioritize recognized source code files over generic text files
        if ext.lower() in SOURCE_EXTENSIONS and score > 0:
            score += 6

        # Penalize test files slightly so implementation files rank higher
        if "test" in path.lower() or "tests" in path.lower():
            score = max(1, int(score * 0.7))


        if score > 0:
            term_list = sorted(list(matched_terms))[:4]
            terms_str = ", ".join(f"'{t}'" for t in term_list)
            reason = f"Path contains issue keyword(s): {terms_str}"
            if any(t in filename_tokens for t in matched_terms):
                reason += f" (matches filename {filename})"

            scored_candidates.append({
                "path": path,
                "score": score,
                "reason": reason,
                "matched_terms": term_list,
            })

    # Sort descending by score, then alphabetically by path for tie-breaking
    scored_candidates.sort(key=lambda c: (-c["score"], c["path"]))

    return scored_candidates[:limit]
