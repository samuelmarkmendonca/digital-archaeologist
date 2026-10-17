"""GitHub API Service for Digital Archaeologist (RepoRescue).

Handles URL validation, repository metadata, recursive git tree exploration,
issue fetching, and raw file content retrieval via the GitHub REST API v3.
"""

from __future__ import annotations

import base64
import io
import os
import re
import urllib.parse
import zipfile
from typing import Any

import requests

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_USER_AGENT = "Digital-Archaeologist/1.0"
REQUEST_TIMEOUT_SECONDS = 15

# In-memory cache for archives when rate limits are exceeded
_ZIP_CACHE: dict[tuple[str, str], dict[str, str]] = {}


def _get_headers(token: str | None = None) -> dict[str, str]:
    """Build standard headers for GitHub REST API requests."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    if token and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Parse a GitHub repository URL into ('owner', 'repo').

    Supported formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo/
    - https://github.com/owner/repo.git
    - github.com/owner/repo

    Raises:
        ValueError: If the URL is invalid or does not target github.com.
    """
    if not repo_url or not isinstance(repo_url, str):
        raise ValueError("Repository URL must be a non-empty string.")

    raw_url = repo_url.strip()
    if not raw_url.startswith(("http://", "https://")):
        raw_url = f"https://{raw_url}"

    parsed = urllib.parse.urlparse(raw_url)
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("github.com", "www.github.com"):
        raise ValueError(f"Invalid host '{hostname}'. Only 'github.com' repositories are supported.")

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        raise ValueError("Invalid repository URL format. Expected: 'https://github.com/owner/repo'.")

    owner = path_parts[0]
    repo = path_parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not re.match(r"^[A-Za-z0-9_.-]+$", owner) or not re.match(r"^[A-Za-z0-9_.-]+$", repo):
        raise ValueError(f"Invalid characters in repository path: '{owner}/{repo}'.")

    return owner, repo


def parse_issue_url(issue_url: str, expected_owner: str, expected_repo: str) -> int:
    """Parse issue number from URL matching expected repository.

    Format: 'https://github.com/owner/repo/issues/42'

    Raises:
        ValueError: If URL format is invalid, does not match owner/repo, or has non-numeric ID.
    """
    if not issue_url or not isinstance(issue_url, str):
        raise ValueError("Issue URL must be a non-empty string.")

    raw_url = issue_url.strip()
    if not raw_url.startswith(("http://", "https://")):
        raw_url = f"https://{raw_url}"

    parsed = urllib.parse.urlparse(raw_url)
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("github.com", "www.github.com"):
        raise ValueError(f"Invalid host '{hostname}'. Expected github.com.")

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    # Expected: [owner, repo, "issues", issue_number]
    if len(path_parts) < 4 or path_parts[2].lower() != "issues":
        raise ValueError("Invalid issue URL format. Expected: 'https://github.com/owner/repo/issues/{number}'.")

    url_owner = path_parts[0]
    url_repo = path_parts[1]
    if url_repo.endswith(".git"):
        url_repo = url_repo[:-4]

    if url_owner.lower() != expected_owner.lower() or url_repo.lower() != expected_repo.lower():
        raise ValueError(
            f"Issue belongs to '{url_owner}/{url_repo}', which does not match active repository '{expected_owner}/{expected_repo}'."
        )

    try:
        issue_number = int(path_parts[3])
        if issue_number <= 0:
            raise ValueError
        return issue_number
    except ValueError:
        raise ValueError(f"Invalid issue number '{path_parts[3]}'. Expected a positive integer.")


def _handle_response_errors(response: requests.Response, context: str) -> None:
    """Provide user-friendly error messages based on HTTP status codes."""
    if response.status_code == 200:
        return
    if response.status_code == 404:
        raise RuntimeError(f"{context} was not found (HTTP 404). Verify that it exists and is public.")
    if response.status_code == 403:
        rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
        if rate_limit_remaining == "0":
            raise RuntimeError(
                "GitHub API rate limit exceeded (HTTP 403). "
                "Add a personal GITHUB_TOKEN to your .env file to unlock 5,000 requests/hour."
            )
        raise RuntimeError(f"Access forbidden by GitHub API (HTTP 403) while fetching {context.lower()}.")
    if response.status_code >= 500:
        raise RuntimeError(f"GitHub service encountered an internal error (HTTP {response.status_code}).")
    raise RuntimeError(f"GitHub API error (HTTP {response.status_code}): {response.text[:200]}")


def _fetch_tree_from_zipball(owner: str, repo: str) -> dict[str, Any]:
    """Fallback when GitHub API rate limit is exceeded.
    
    Downloads the public repository archive directly and extracts the tree and source files into memory.
    """
    for branch in ("main", "master"):
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        try:
            r = requests.get(zip_url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=20)
            if r.status_code == 200:
                zf = zipfile.ZipFile(io.BytesIO(r.content))
                namelist = zf.namelist()
                if not namelist:
                    continue
                prefix = namelist[0]
                tree_entries: list[dict[str, Any]] = []
                file_map: dict[str, str] = {}
                for name in namelist:
                    if name.endswith("/"):
                        continue
                    rel_path = name[len(prefix):]
                    tree_entries.append({"path": rel_path, "type": "blob"})
                    ext = os.path.splitext(rel_path)[1].lower()
                    if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".json", ".yaml", ".yml", ".toml", ".md"):
                        try:
                            file_map[rel_path] = zf.read(name).decode("utf-8", errors="replace")
                        except Exception:
                            pass

                _ZIP_CACHE[(owner.lower(), repo.lower())] = file_map
                return {
                    "name": repo,
                    "description": f"Excavated from GitHub ({owner}/{repo})",
                    "language": "Mixed",
                    "default_branch": branch,
                    "tree_entries": tree_entries,
                }
        except Exception:
            continue
    raise RuntimeError(
        f"GitHub API rate limit exceeded and public archive download failed for '{owner}/{repo}'. "
        "Please provide a personal GITHUB_TOKEN in the sidebar or wait for the rate limit window to reset."
    )


def get_repository_overview(owner: str, repo: str, token: str | None = None) -> dict[str, Any]:
    """Fetch repo metadata and recursive git tree entries.
    
    Gracefully falls back to public repository archives if GitHub API rate limits are encountered.

    Returns:
        dict: {
            'name': str,
            'description': str | None,
            'language': str | None,
            'default_branch': str,
            'tree_entries': list[dict]
        }
    """
    headers = _get_headers(token)

    # 1. Fetch Repository Metadata
    repo_endpoint = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    try:
        repo_resp = requests.get(repo_endpoint, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        if repo_resp.status_code == 403 and (not token or not token.strip()):
            # API rate limit reached -> seamless fallback to public zipball
            return _fetch_tree_from_zipball(owner, repo)
    except requests.RequestException:
        return _fetch_tree_from_zipball(owner, repo)

    _handle_response_errors(repo_resp, f"Repository '{owner}/{repo}'")
    repo_data = repo_resp.json()

    default_branch = repo_data.get("default_branch") or "main"

    # 2. Fetch Recursive Git Tree
    tree_endpoint = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
    try:
        tree_resp = requests.get(tree_endpoint, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        if tree_resp.status_code == 403 and (not token or not token.strip()):
            return _fetch_tree_from_zipball(owner, repo)
    except requests.RequestException:
        return _fetch_tree_from_zipball(owner, repo)

    _handle_response_errors(tree_resp, f"Git tree for '{owner}/{repo}' on branch '{default_branch}'")
    tree_data = tree_resp.json()

    all_entries = tree_data.get("tree", [])
    file_entries = [entry for entry in all_entries if entry.get("type") == "blob"]

    return {
        "name": repo_data.get("name", repo),
        "description": repo_data.get("description"),
        "language": repo_data.get("language"),
        "default_branch": default_branch,
        "tree_entries": file_entries,
    }


def get_issue(owner: str, repo: str, issue_number: int, token: str | None = None) -> dict[str, Any]:
    """Fetch issue title, markdown body, html_url, and number."""
    headers = _get_headers(token)
    issue_endpoint = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}"

    try:
        resp = requests.get(issue_endpoint, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to connect to GitHub API: {e}")

    _handle_response_errors(resp, f"Issue #{issue_number} in '{owner}/{repo}'")
    issue_data = resp.json()

    # Note: Pull Requests are also returned by the issues endpoint in GitHub API,
    # but contain a 'pull_request' key if they are PRs.
    return {
        "title": issue_data.get("title", ""),
        "body": issue_data.get("body") or "",
        "url": issue_data.get("html_url", f"https://github.com/{owner}/{repo}/issues/{issue_number}"),
        "number": issue_number,
    }


def get_file_text(
    owner: str,
    repo: str,
    path: str,
    ref: str,
    token: str | None = None,
    max_chars: int = 6000,
) -> str:
    """Fetch file content decoded as UTF-8, safely truncated to max_chars.
    
    First tries raw.githubusercontent.com to avoid consuming GitHub REST API rate limits.
    Falls back to the GitHub REST API if needed.
    """
    # 1. Try raw.githubusercontent.com (fast, bypasses REST API 60 req/hr rate limits)
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    if token and token.strip():
        headers["Authorization"] = f"token {token.strip()}"
    try:
        raw_resp = requests.get(raw_url, headers=headers, timeout=8)
        if raw_resp.status_code == 200:
            text = raw_resp.text
            if len(text) > max_chars:
                return text[:max_chars] + f"\n\n... [Truncated: content exceeded {max_chars} characters]"
            return text
    except Exception:
        pass

    # 2. Fallback to GitHub REST API
    api_headers = _get_headers(token)
    encoded_path = urllib.parse.quote(path)
    content_endpoint = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{encoded_path}?ref={ref}"

    try:
        resp = requests.get(content_endpoint, headers=api_headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        return f"[Error: Network timeout while reading {path}: {e}]"

    if resp.status_code != 200:
        return f"[Error: Unable to fetch {path} (HTTP {resp.status_code})]"

    data = resp.json()
    raw_b64 = data.get("content", "")
    encoding = data.get("encoding", "")

    if encoding == "base64" and raw_b64:
        try:
            decoded_bytes = base64.b64decode(raw_b64)
            text = decoded_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            return f"[Error: Decoding file content failed: {e}]"
    else:
        text = str(raw_b64)

    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n... [Truncated: content exceeded {max_chars} characters]"
    return text


def get_readme(owner: str, repo: str, default_branch: str = "main", token: str | None = None) -> str:
    """Fetch repository README content if available."""
    # Try raw README first
    for readme_name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{readme_name}"
        try:
            r = requests.get(raw_url, timeout=5)
            if r.status_code == 200 and r.text.strip():
                return r.text[:8000]
        except Exception:
            pass

    headers = _get_headers(token)
    endpoint = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme?ref={default_branch}"
    try:
        resp = requests.get(endpoint, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code == 200:
            data = resp.json()
            raw_b64 = data.get("content", "")
            if raw_b64:
                return base64.b64decode(raw_b64).decode("utf-8", errors="replace")[:8000]
    except Exception:
        pass
    return ""


def get_key_source_files(
    owner: str,
    repo: str,
    tree_entries: list[dict[str, Any]],
    default_branch: str = "main",
    max_files: int = 30,
    token: str | None = None,
) -> dict[str, str]:
    """Fetch the contents of the most important entry points, manifests, and core files.

    Prioritizes entry points (app.py, main.py, index.js), config files, and core package modules.
    """
    priority_names = {
        "package.json", "pyproject.toml", "cargo.toml", "go.mod", "dockerfile",
        "main.py", "app.py", "index.py", "server.py", "wsgi.py", "asgi.py",
        "index.js", "index.ts", "server.js", "server.ts", "app.js", "app.ts",
        "main.go", "main.rs", "lib.rs",
    }

    selected_paths: list[str] = []
    
    # 1. Select priority entrypoints and manifests
    for entry in tree_entries:
        path = entry.get("path", "")
        filename = path.split("/")[-1].lower()
        if filename in priority_names and path not in selected_paths:
            selected_paths.append(path)
            if len(selected_paths) >= max_files:
                break

    # 2. Select top source files in primary source directories (src/, package folder, etc.)
    # Exclude tests, docs, vendor, examples
    if len(selected_paths) < max_files:
        for entry in tree_entries:
            path = entry.get("path", "")
            if path in selected_paths:
                continue
            lower_path = path.lower()
            if any(x in lower_path for x in ("test", "tests", "doc", "docs", "dist", "vendor", "example", "examples", "benchmark")):
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"):
                selected_paths.append(path)
                if len(selected_paths) >= max_files:
                    break

    # 3. Fallback to any remaining recognized code files
    if len(selected_paths) < max_files:
        for entry in tree_entries:
            path = entry.get("path", "")
            if path not in selected_paths:
                ext = os.path.splitext(path)[1].lower()
                if ext in (".py", ".js", ".ts", ".go", ".rs", ".java"):
                    selected_paths.append(path)
                    if len(selected_paths) >= max_files:
                        break

    # Fetch contents (use in-memory cached archive if available)
    cache_key = (owner.lower(), repo.lower())
    cached_files = _ZIP_CACHE.get(cache_key, {})

    contents: dict[str, str] = {}
    for path in selected_paths:
        if path in cached_files:
            contents[path] = cached_files[path]
        else:
            text = get_file_text(owner, repo, path, default_branch, token=token, max_chars=4000)
            contents[path] = text

    return contents

