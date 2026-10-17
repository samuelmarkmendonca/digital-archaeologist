"""Digital Archaeologist - Codebase Excavation & Knowledge Graph Platform.

Reconstructs unfamiliar codebases, configuration files, and abandoned projects.
Maps dependencies, detects undocumented behaviors, and delivers a token-optimized
navigable technical explanation with Cytoscape.js Knowledge Graph visualization
and Markdown architectural summary.
"""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

import cytoscape_component
import gemma_service
import github_service
import graph_service

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Digital Archaeologist | Codebase Excavator",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom High-Tech Dark Theme Styling
st.markdown(
    """
    <style>
    /* Dark Obsidian & Glassmorphism Aesthetics */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1300px;
    }
    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10b981 0%, #06b6d4 50%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.6rem;
    }
    .metric-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 14px 18px;
        text-align: center;
        backdrop-filter: blur(8px);
    }
    .metric-val {
        font-size: 1.45rem;
        font-weight: 700;
        color: #f1f5f9;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }
    .savings-pill {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        background: linear-gradient(135deg, #059669 0%, #0284c7 100%);
        color: white;
        font-weight: 700;
        font-size: 0.95rem;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
    }
    .badge-entry {
        background: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid #059669;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session_state() -> None:
    """Initialize state variables."""
    if "archaeology_results" not in st.session_state:
        st.session_state["archaeology_results"] = None
    if "repo_input" not in st.session_state:
        st.session_state["repo_input"] = ""


init_session_state()

# --- Header ---
st.markdown("<div class='hero-title'>⛏️ Digital Archaeologist</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='hero-subtitle'>Excavate unfamiliar or abandoned codebases • "
    "Reconstruct system architecture & undocumented behavior • "
    "Visualize interactive Cytoscape.js knowledge graphs with 90%+ token optimization.</div>",
    unsafe_allow_html=True,
)

# --- Simple Input Section ---
# As requested: "front end should simple, only input git url and output summary and graph"
col_url, col_btn = st.columns([5, 1])

with col_url:
    repo_url = st.text_input(
        "GitHub Repository URL",
        value=st.session_state["repo_input"],
        placeholder="https://github.com/owner/repository",
        label_visibility="collapsed",
    )

with col_btn:
    excavate_clicked = st.button("⛏️ Excavate", type="primary", use_container_width=True)

# Preset chips for instant 1-click test
chip1, chip2, chip3, chip4, chip_info = st.columns([1.1, 1.1, 1.1, 1.1, 2.6])
with chip1:
    if st.button("📦 pallets/flask", use_container_width=True, help="Python Web Microframework"):
        st.session_state["repo_input"] = "https://github.com/pallets/flask"
        st.rerun()
with chip2:
    if st.button("⚡ tiangolo/fastapi", use_container_width=True, help="Modern Async Python API"):
        st.session_state["repo_input"] = "https://github.com/tiangolo/fastapi"
        st.rerun()
with chip3:
    if st.button("🌐 psf/requests", use_container_width=True, help="HTTP for Humans"):
        st.session_state["repo_input"] = "https://github.com/psf/requests"
        st.rerun()
with chip4:
    if st.button("🚂 expressjs/express", use_container_width=True, help="Node.js Web Framework"):
        st.session_state["repo_input"] = "https://github.com/expressjs/express"
        st.rerun()
with chip_info:
    st.caption("👈 Click a sample repo or paste any public GitHub repository URL above.")

# Clean Collapsible Settings (Keeps UI simple while allowing custom keys)
with st.expander("⚙️ Advanced Settings & API Keys (Optional)", expanded=False):
    cfg1, cfg2, cfg3 = st.columns(3)
    with cfg1:
        env_gemini_key = os.getenv("GEMINI_API_KEY", "")
        api_key_input = st.text_input(
            "Google Gemini / Gemma API Key",
            value=env_gemini_key if not env_gemini_key.startswith("your_") else "",
            type="password",
            help="For Gemma semantic reasoning. If empty, the app runs in deterministic mode.",
        )
    with cfg2:
        model_options = [
            "gemma-4-26b-a4b-it",
            "gemma-4-31b-it",
            "gemma-3-27b-it",
            "gemini-2.5-flash",
        ]
        selected_model = st.selectbox("Gemma Model Track", options=model_options, index=0)
    with cfg3:
        env_github_token = os.getenv("GITHUB_TOKEN", "")
        github_token_input = st.text_input(
            "GitHub Token (Optional)",
            value=env_github_token,
            type="password",
            help="Optional access token to increase GitHub rate limit to 5,000 req/hr.",
        )

# --- Excavation Pipeline Execution ---
active_url = repo_url.strip() if repo_url else st.session_state.get("repo_input", "").strip()

if excavate_clicked:
    if not active_url:
        st.warning("⚠️ Please provide a GitHub Repository URL to excavate.")
    else:
        with st.status("🔍 Excavating codebase artifacts & constructing knowledge graph...", expanded=True) as status:
            try:
                # 1. Parse URL
                status.write("1️⃣ Validating repository URL...")
                owner, repo = github_service.parse_repo_url(active_url)

                # 2. Fetch Metadata & Tree
                status.write(f"2️⃣ Fetching repository metadata & Git tree for `{owner}/{repo}`...")
                repo_info = github_service.get_repository_overview(owner, repo, token=github_token_input)
                tree_entries = repo_info.get("tree_entries", [])

                # 3. Fetch README & Key Files
                status.write("3️⃣ Inspecting entry points, manifests & source signatures...")
                default_branch = repo_info.get("default_branch", "main")
                readme_text = github_service.get_readme(owner, repo, default_branch, token=github_token_input)
                key_files = github_service.get_key_source_files(
                    owner, repo, tree_entries, default_branch=default_branch, max_files=30, token=github_token_input
                )

                # 4. Build Token-Optimized Cytoscape Knowledge Graph
                status.write("4️⃣ Constructing Cytoscape.js Knowledge Graph & detecting undocumented behaviors...")
                graph_data = graph_service.build_knowledge_graph(
                    repo_name=f"{owner}/{repo}",
                    tree_entries=tree_entries,
                    file_contents=key_files,
                )

                # 5. Gemma Archaeological Synthesis
                status.write(f"5️⃣ Synthesizing architectural report with {selected_model}...")
                ai_summary = gemma_service.generate_archaeology_summary(
                    repo_info=repo_info,
                    readme_text=readme_text,
                    graph_data=graph_data,
                    api_key=api_key_input,
                    model=selected_model,
                )

                status.update(label="✅ Excavation complete! Knowledge Graph generated.", state="complete", expanded=False)

                st.session_state["archaeology_results"] = {
                    "owner": owner,
                    "repo": repo,
                    "repo_info": repo_info,
                    "graph_data": graph_data,
                    "ai_summary": ai_summary,
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


# --- Output Display: Summary and Cytoscape.js Graph ---
res = st.session_state.get("archaeology_results")
if res:
    owner = res["owner"]
    repo = res["repo"]
    repo_info = res["repo_info"]
    graph_data = res["graph_data"]
    ai_summary = res["ai_summary"]
    token_stats = graph_data.get("token_stats", {})
    summary_metrics = graph_data.get("summary_metrics", {})
    cytoscape_json = graph_data.get("cytoscape_json", {})

    st.markdown("---")

    # Hero Banner
    banner_left, banner_right = st.columns([3, 1])
    with banner_left:
        st.subheader(f"🏺 [{owner}/{repo}](https://github.com/{owner}/{repo})")
        desc = repo_info.get("description") or "Excavated software repository"
        st.markdown(f"*{desc}*")
        st.caption(
            f"**Primary Language**: {repo_info.get('language') or 'Mixed'} | "
            f"**Default Branch**: `{repo_info.get('default_branch')}` | "
            f"**Analyzed Blobs**: {len(repo_info.get('tree_entries', []))}"
        )
    with banner_right:
        savings = token_stats.get("token_reduction_percent", "90%+")
        st.markdown(
            f"<div style='text-align: right; padding-top: 10px;'>"
            f"<span class='savings-pill'>⚡ {savings} Token Optimization</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Metric Cards
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-val' style='color:#10b981;'>{summary_metrics.get('entry_points_detected', 0)}</div>"
            f"<div class='metric-label'>Entry Points</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-val' style='color:#06b6d4;'>{summary_metrics.get('total_files_analyzed', 0)}</div>"
            f"<div class='metric-label'>Modules Analyzed</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-val' style='color:#8b5cf6;'>{summary_metrics.get('total_dependencies', 0)}</div>"
            f"<div class='metric-label'>Dependencies Mapped</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-val' style='color:#f59e0b;'>{summary_metrics.get('undocumented_quirks_detected', 0)}</div>"
            f"<div class='metric-label'>Undocumented Quirks</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with m5:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-val' style='color:#38bdf8;'>{token_stats.get('knowledge_graph_tokens', 0):,}</div>"
            f"<div class='metric-label'>Graph Tokens vs {token_stats.get('raw_codebase_tokens', 0):,} Raw</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.write("")

    # Two Primary Tabs: Summary in MD format & Knowledge Graph in Cytoscape.js JSON
    tab_graph, tab_summary, tab_json = st.tabs([
        "🗺️ Cytoscape.js Knowledge Graph",
        "📜 Architectural Summary (Markdown)",
        "💾 Cytoscape.js JSON Format",
    ])

    with tab_graph:
        st.markdown("### 🗺️ Interactive Cytoscape.js Knowledge Graph")
        st.caption(
            "Interactive module dependency topology rendered with **Cytoscape.js**. "
            "Click on any node to view full details, exported symbols, dependencies, and detected undocumented behaviors."
        )

        # Render Cytoscape.js Interactive Component
        cyto_html = cytoscape_component.generate_cytoscape_html(cytoscape_json, height=680)
        components.html(cyto_html, height=710, scrolling=False)

        # Action bar under graph
        col_dl, col_blank = st.columns([1, 3])
        with col_dl:
            st.download_button(
                label="⬇️ Download Cytoscape JSON",
                data=json.dumps(cytoscape_json, indent=2),
                file_name=f"{repo}_cytoscape_knowledge_graph.json",
                mime="application/json",
                use_container_width=True,
            )

    with tab_summary:
        st.markdown("### 📜 Executive Codebase Summary & Resurrection Guide")
        
        # Download summary button
        col_sum_dl, _ = st.columns([1, 4])
        with col_sum_dl:
            st.download_button(
                label="⬇️ Download Summary (.md)",
                data=ai_summary,
                file_name=f"{repo}_archaeology_summary.md",
                mime="text/markdown",
                use_container_width=True,
            )

        # Render Markdown output
        st.markdown(ai_summary)

    with tab_json:
        st.markdown("### 💾 Cytoscape.js JSON Format")
        st.caption(
            "Exact JSON structure matching the **Cytoscape.js JSON specification** (`elements.nodes` and `elements.edges`). "
            "Ready for import into external graph visualizers, Cytoscape Desktop, or AI coding agents."
        )

        st.json(cytoscape_json)
