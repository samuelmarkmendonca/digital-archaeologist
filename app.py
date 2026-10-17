"""Digital Archaeologist (RepoRescue) - Streamlit Web Application.

An automated triage companion that maps GitHub issues to candidate source files
using deterministic keyword ranking and grounded Gemini/Gemma AI reasoning.
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv

import gemma_service
import github_service
import ranking

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Digital Archaeologist | RepoRescue",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished typography and visual cards
st.markdown(
    """
    <style>
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .file-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        background-color: #238636;
        color: white;
        font-weight: 600;
        font-size: 0.85rem;
        margin-right: 8px;
    }
    .score-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        background-color: #1f6feb;
        color: white;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .candidate-box {
        border-left: 4px solid #1f6feb;
        background: rgba(31, 111, 235, 0.05);
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session_state() -> None:
    """Initialize Streamlit session state keys."""
    if "results" not in st.session_state:
        st.session_state["results"] = None
    if "repo_input" not in st.session_state:
        st.session_state["repo_input"] = ""
    if "issue_input" not in st.session_state:
        st.session_state["issue_input"] = ""


init_session_state()

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("⚙️ Settings")
    
    st.markdown("### 🔑 API Keys")
    env_gemini_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=env_gemini_key if not env_gemini_key.startswith("your_") else "",
        type="password",
        help="Required for AI triage synthesis. Get one at https://aistudio.google.com/.",
    )
    
    env_github_token = os.getenv("GITHUB_TOKEN", "")
    github_token_input = st.text_input(
        "GitHub Token (Optional)",
        value=env_github_token,
        type="password",
        help="Optional personal access token to lift GitHub rate limits from 60 to 5,000 requests/hour.",
    )

    st.markdown("### 🧠 Model Selection")
    default_model = os.getenv("GEMMA_MODEL", "gemini-2.5-flash")
    model_options = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemma-4-26b-a4b-it",
    ]
    selected_model = st.selectbox(
        "AI Model",
        options=model_options,
        index=model_options.index(default_model) if default_model in model_options else 0,
    )

    st.markdown("---")
    st.markdown("### ⚡ Quick Presets")
    st.caption("Click to test with real open-source repositories & issues:")

    if st.button("📦 requests #6443 (HTTP & Session)", use_container_width=True):
        st.session_state["repo_input"] = "https://github.com/psf/requests"
        st.session_state["issue_input"] = "https://github.com/psf/requests/issues/6443"

    if st.button("🌶️ flask #5000 (Routing & Context)", use_container_width=True):
        st.session_state["repo_input"] = "https://github.com/pallets/flask"
        st.session_state["issue_input"] = "https://github.com/pallets/flask/issues/5000"

    st.markdown("---")
    st.caption("RepoRescue — Digital Archaeologist v1.0")


# --- Main Application Header ---
st.title("🔍 Digital Archaeologist (RepoRescue)")
st.markdown(
    "Automated triage tool and **Code Trail** navigator for open-source contributors. "
    "Paste a GitHub repository and issue URL to deterministically locate candidate files and receive grounded AI investigation advice."
)

# --- Input Section ---
col1, col2 = st.columns([1, 1])

with col1:
    repo_url = st.text_input(
        "GitHub Repository URL",
        value=st.session_state["repo_input"],
        placeholder="https://github.com/owner/repository",
        help="Link to any public GitHub repository.",
    )

with col2:
    issue_url = st.text_input(
        "GitHub Issue URL",
        value=st.session_state["issue_input"],
        placeholder="https://github.com/owner/repository/issues/123",
        help="Link to an issue inside the specified repository.",
    )

investigate_clicked = st.button("🚀 Investigate Issue", type="primary", use_container_width=True)


# --- Execution Pipeline ---
if investigate_clicked:
    if not repo_url or not issue_url:
        st.warning("⚠️ Please provide both a Repository URL and an Issue URL.")
    else:
        with st.status("🔍 Excavating codebase and analyzing issue...", expanded=True) as status:
            try:
                # 1. Parse URLs
                status.write("1️⃣ Validating repository and issue URLs...")
                owner, repo = github_service.parse_repo_url(repo_url)
                issue_number = github_service.parse_issue_url(issue_url, owner, repo)

                # 2. Fetch Repo Metadata & Tree
                status.write(f"2️⃣ Fetching repository metadata & Git tree for `{owner}/{repo}`...")
                repo_info = github_service.get_repository_overview(owner, repo, token=github_token_input)

                # 3. Fetch Issue Details
                status.write(f"3️⃣ Fetching Issue #{issue_number} details...")
                issue_data = github_service.get_issue(owner, repo, issue_number, token=github_token_input)

                # 4. Deterministic Ranking
                status.write("4️⃣ Tokenizing issue and deterministically ranking candidate files...")
                combined_issue_text = f"{issue_data['title']} {issue_data['title']} {issue_data['body']}"
                candidates = ranking.rank_candidate_files(
                    issue_text=combined_issue_text,
                    tree_entries=repo_info.get("tree_entries", []),
                    limit=3,
                )

                # 5. Retrieve File Snippets
                status.write("5️⃣ Retrieving source code snippets for top candidate files...")
                for candidate in candidates:
                    snippet = github_service.get_file_text(
                        owner=owner,
                        repo=repo,
                        path=candidate["path"],
                        ref=repo_info.get("default_branch", "main"),
                        token=github_token_input,
                        max_chars=6000,
                    )
                    candidate["snippet"] = snippet

                # 6. Gemma / Gemini Grounded Synthesis
                status.write(f"6️⃣ Synthesizing Code Trail with {selected_model}...")
                ai_explanation = gemma_service.analyze_issue_with_gemma(
                    repo_info=repo_info,
                    issue=issue_data,
                    candidates=candidates,
                    api_key=api_key_input,
                    model=selected_model,
                )

                status.update(label="✅ Code Trail generated successfully!", state="complete", expanded=False)

                # Save into session state
                st.session_state["results"] = {
                    "owner": owner,
                    "repo": repo,
                    "repo_info": repo_info,
                    "issue_data": issue_data,
                    "candidates": candidates,
                    "ai_explanation": ai_explanation,
                }

            except ValueError as val_err:
                status.update(label="❌ Invalid Input", state="error", expanded=True)
                st.error(f"Input Error: {val_err}")
            except RuntimeError as run_err:
                status.update(label="❌ API Error", state="error", expanded=True)
                st.error(f"{run_err}")
            except Exception as e:
                status.update(label="❌ Unexpected Error", state="error", expanded=True)
                st.error(f"An unexpected error occurred: {e}")


# --- Results Rendering ---
results = st.session_state.get("results")
if results:
    owner = results["owner"]
    repo = results["repo"]
    repo_info = results["repo_info"]
    issue_data = results["issue_data"]
    candidates = results["candidates"]
    ai_explanation = results["ai_explanation"]

    st.markdown("---")

    # Header Card with Meta Info
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.subheader(f"📌 Issue #{issue_data['number']}: [{issue_data['title']}]({issue_data['url']})")
        st.caption(f"**Repository**: [{owner}/{repo}](https://github.com/{owner}/{repo}) • **Language**: {repo_info.get('language') or 'N/A'} • **Branch**: `{repo_info.get('default_branch')}`")
        if repo_info.get("description"):
            st.markdown(f"*{repo_info['description']}*")
    with header_col2:
        st.metric("Candidate Files Identified", len(candidates))

    # Tabs for organized viewing
    tab_trail, tab_ai, tab_graph = st.tabs(["🧭 Code Trail (Candidates)", "🤖 Grounded AI Triage", "🔮 Knowledge Graph (Preview)"])

    with tab_trail:
        st.markdown("### 🎯 Deterministically Ranked Candidate Files")
        st.caption("These files were selected by keyword frequency matching between the issue description and repository file paths.")

        if not candidates:
            st.info("No source files in the repository matched the issue keywords directly. Check the repository root files or issue text.")
        else:
            for idx, cand in enumerate(candidates, start=1):
                path = cand["path"]
                score = cand["score"]
                reason = cand["reason"]
                snippet = cand.get("snippet", "")
                github_file_url = f"https://github.com/{owner}/{repo}/blob/{repo_info.get('default_branch', 'main')}/{path}"

                with st.container():
                    st.markdown(
                        f"""
                        <div class="candidate-box">
                            <span class="file-badge">Candidate {idx}</span>
                            <span class="score-badge">Relevancy Score: {score}</span>
                            <h4 style="margin-top: 8px;"><a href="{github_file_url}" target="_blank">📄 {path}</a></h4>
                            <p style="margin-bottom: 0; color: #888;">{reason}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.expander(f"👁️ View Code Snippet ({path})", expanded=(idx == 1)):
                        # Detect syntax language from file extension
                        ext = os.path.splitext(path)[1].lstrip(".") or "text"
                        st.code(snippet, language=ext)

    with tab_ai:
        st.markdown("### 🤖 Grounded AI Triage & Next Steps")
        st.markdown(ai_explanation)

    with tab_graph:
        st.markdown("### 🔮 Codebase Knowledge Graph (Post-MVP Preview)")
        st.info(
            "**Post-MVP Feature**: This planned component produces a token-efficient topological graph "
            "(`knowledge_graph.json` + visual dependencies) so downstream AI agents can ingest the entire "
            "project architecture while consuming up to 75% fewer context tokens."
        )
        
        # Conceptual preview of graph schema
        sample_nodes = [{"id": c["path"], "type": "candidate_file"} for c in candidates]
        sample_edges = []
        if len(candidates) > 1:
            for i in range(len(candidates) - 1):
                sample_edges.append({"source": candidates[i]["path"], "target": candidates[i+1]["path"], "relation": "references"})

        st.json({
            "repository": f"{owner}/{repo}",
            "core_mission": "Codebase summarization & issue triage",
            "nodes": sample_nodes,
            "edges": sample_edges,
            "status": "Scheduled strictly post-MVP",
        })
