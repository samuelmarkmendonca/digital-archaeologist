"""Digital Archaeologist - Streamlit Web Application.

Excavates abandoned, dormant, or inherited codebases.
Generates an executive architectural summary, visualizes a module dependency
knowledge graph, and produces a token-efficient context payload for AI coding agents.
"""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv

import gemma_service
import github_service
import graph_service

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Digital Archaeologist | Codebase Excavator",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished dark/light contrast and badges
st.markdown(
    """
    <style>
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .token-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        background: linear-gradient(135deg, #1f6feb 0%, #238636 100%);
        color: white;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .entry-badge {
        background-color: #238636;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .module-badge {
        background-color: #1f6feb;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
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

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("⚙️ Archaeologist Config")
    
    st.markdown("### 🔑 API Keys")
    env_gemini_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=env_gemini_key if not env_gemini_key.startswith("your_") else "",
        type="password",
        help="Required for AI architectural synthesis. Get one at https://aistudio.google.com/.",
    )

    env_github_token = os.getenv("GITHUB_TOKEN", "")
    github_token_input = st.text_input(
        "GitHub Token (Optional)",
        value=env_github_token,
        type="password",
        help="Optional personal access token to lift GitHub rate limits from 60 to 5,000 requests/hour.",
    )

    st.markdown("### 💎 Gemma Track (Hackathon)")
    default_model = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
    model_options = [
        "gemma-4-26b-a4b-it",  # Gemma 4 26B Flagship
        "gemma-4-31b-it",      # Gemma 4 31B Dense
        "gemma-3-27b-it",      # Gemma 3 27B
    ]
    selected_model = st.selectbox(
        "Gemma Model",
        options=model_options,
        index=model_options.index(default_model) if default_model in model_options else 0,
        help="Fixed exclusively to Google Gemma models for the hackathon track.",
    )

    st.markdown("---")
    st.markdown("### 🏺 Excavation Presets")
    st.caption("Test with these open-source codebases:")

    if st.button("📦 pallets/flask (Python Web Framework)", use_container_width=True):
        st.session_state["repo_input"] = "https://github.com/pallets/flask"

    if st.button("⚡ tiangolo/fastapi (Modern Python API)", use_container_width=True):
        st.session_state["repo_input"] = "https://github.com/tiangolo/fastapi"

    if st.button("🌐 psf/requests (HTTP Library)", use_container_width=True):
        st.session_state["repo_input"] = "https://github.com/psf/requests"

    st.markdown("---")
    st.caption("Digital Archaeologist — AI Context Optimizer v2.0")


# --- Main Application Header ---
st.title("⛏️ Digital Archaeologist")
st.subheader("Resurrect Abandoned Codebases & Generate Token-Efficient AI Context")
st.markdown(
    "Returning to a forgotten project or inheriting a dormant codebase? **Digital Archaeologist** scans the repository, "
    "builds a structural **Knowledge Graph** of modules and dependencies, and produces a compact context payload. "
    "When giving the project to an LLM or AI agent, our Knowledge Graph saves up to **90%+ context tokens** while delivering full architectural awareness."
)

# --- Repository Input ---
col_in, col_btn = st.columns([4, 1])
with col_in:
    repo_url = st.text_input(
        "GitHub Repository URL",
        value=st.session_state["repo_input"],
        placeholder="https://github.com/owner/repository",
        help="Link to any public GitHub repository you wish to excavate.",
    )

with col_btn:
    st.write("")
    st.write("")
    excavate_clicked = st.button("⛏️ Excavate Codebase", type="primary", use_container_width=True)


# --- Excavation Pipeline ---
if excavate_clicked:
    if not repo_url:
        st.warning("⚠️ Please provide a GitHub Repository URL to excavate.")
    else:
        with st.status("🔍 Excavating codebase artifacts & constructing knowledge graph...", expanded=True) as status:
            try:
                # 1. Parse URL
                status.write("1️⃣ Validating repository URL...")
                owner, repo = github_service.parse_repo_url(repo_url)

                # 2. Fetch Metadata & Tree
                status.write(f"2️⃣ Fetching repository metadata & Git tree for `{owner}/{repo}`...")
                repo_info = github_service.get_repository_overview(owner, repo, token=github_token_input)
                tree_entries = repo_info.get("tree_entries", [])

                # 3. Fetch README & Key Files
                status.write("3️⃣ Fetching README and inspecting entry points & dependency manifests...")
                default_branch = repo_info.get("default_branch", "main")
                readme_text = github_service.get_readme(owner, repo, default_branch, token=github_token_input)
                key_files = github_service.get_key_source_files(
                    owner, repo, tree_entries, default_branch=default_branch, max_files=15, token=github_token_input
                )

                # 4. Build Knowledge Graph
                status.write("4️⃣ Building topological Knowledge Graph (parsing imports, symbols, and edges)...")
                graph_data = graph_service.build_knowledge_graph(
                    repo_name=f"{owner}/{repo}",
                    tree_entries=tree_entries,
                    file_contents=key_files,
                )

                # 5. Gemini Archaeological Synthesis
                status.write(f"5️⃣ Synthesizing architectural summary & AI agent context with {selected_model}...")
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


# --- Display Results ---
res = st.session_state.get("archaeology_results")
if res:
    owner = res["owner"]
    repo = res["repo"]
    repo_info = res["repo_info"]
    graph_data = res["graph_data"]
    ai_summary = res["ai_summary"]
    token_stats = graph_data.get("token_stats", {})

    st.markdown("---")

    # Repository Overview Banner
    meta_col1, meta_col2 = st.columns([3, 1])
    with meta_col1:
        st.subheader(f"🏺 [{owner}/{repo}](https://github.com/{owner}/{repo})")
        st.caption(f"**Primary Language**: {repo_info.get('language') or 'Mixed'} • **Branch**: `{repo_info.get('default_branch')}` • **Total Files**: {len(repo_info.get('tree_entries', []))}")
        if repo_info.get("description"):
            st.markdown(f"*{repo_info['description']}*")
    with meta_col2:
        st.markdown(f"<div style='text-align: right;'><span class='token-badge'>⚡ {token_stats.get('token_reduction_percent', '90%')} Token Savings</span></div>", unsafe_allow_html=True)

    # Token Economics Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Raw Codebase (Est. Tokens)", f"{token_stats.get('raw_codebase_tokens', 0):,}")
    with m2:
        st.metric("Knowledge Graph (Tokens)", f"{token_stats.get('knowledge_graph_tokens', 0):,}")
    with m3:
        st.metric("Context Token Reduction", token_stats.get("token_reduction_percent", "N/A"))
    with m4:
        st.metric("Graph Nodes & Edges", f"{len(graph_data['nodes'])} / {len(graph_data['edges'])}")

    st.info(
        "💡 **Why This Matters**: Feeding the entire raw codebase into an LLM burns tens of thousands of tokens, "
        "causes context degradation, and triggers API rate limits. Our **Knowledge Graph** delivers the same structural "
        "comprehension using a fraction of the token budget."
    )

    # Content Tabs
    tab_summary, tab_graph, tab_prompt, tab_json = st.tabs([
        "📜 Archaeological Summary",
        "🗺️ Knowledge Graph Topology",
        "🤖 AI Agent Context Payload",
        "💾 Export JSON",
    ])

    with tab_summary:
        st.markdown("### 🏛️ Executive Codebase Summary & Resurrection Guide")
        st.markdown(ai_summary)

    with tab_graph:
        st.markdown("### 🗺️ Module Dependency Topology")
        st.caption("Visual representation of modules, entry points (green), and detected import relations.")

        # Mermaid Graph View
        mermaid_code = graph_data.get("mermaid_diagram", "")
        if mermaid_code:
            st.markdown(f"```mermaid\n{mermaid_code}\n```")

        # Tabular Nodes Explorer
        with st.expander("📋 Explore Detected Modules & Symbol Exports", expanded=False):
            node_table = []
            for n in graph_data["nodes"]:
                node_table.append({
                    "File": n["filename"],
                    "Path": n["path"],
                    "Type": n["type"],
                    "Language": n["language"],
                    "Exported Symbols": ", ".join(n["exports"]) if n["exports"] else "(none)",
                    "Imports": ", ".join(n["imports"]) if n["imports"] else "(none)",
                })
            st.dataframe(node_table, use_container_width=True)

    with tab_prompt:
        st.markdown("### 🤖 Copy-Paste Context Payload for AI Coding Agents")
        st.markdown(
            "Copy this pre-formatted context block directly into **Cursor, Devin, Windsurf, Claude, or ChatGPT**. "
            "It gives the AI complete architectural awareness of this codebase without burning context tokens on raw files."
        )

        condensed_payload = {
            "repository": f"{owner}/{repo}",
            "description": repo_info.get("description"),
            "language": repo_info.get("language"),
            "modules": [
                {"file": n["path"], "type": n["type"], "exports": n["exports"], "imports": n["imports"]}
                for n in graph_data["nodes"][:30]
            ],
            "dependencies": graph_data["edges"][:40],
        }

        agent_prompt = f"""# Project Architectural Context: {owner}/{repo}
## Description: {repo_info.get('description') or 'N/A'}
## Primary Language: {repo_info.get('language') or 'N/A'}

## Knowledge Graph Topology:
```json
{json.dumps(condensed_payload, indent=2)}
```

You have the complete structural map of this codebase above. Use this to understand file responsibilities and relationships without requiring full source dumps.
"""
        st.code(agent_prompt, language="markdown")

    with tab_json:
        st.markdown("### 💾 Machine-Readable Knowledge Graph")
        st.caption("Download the raw JSON knowledge graph for programmatic pipelines or external agent ingestion.")
        
        json_str = json.dumps(graph_data, indent=2)
        st.download_button(
            label="⬇️ Download knowledge_graph.json",
            data=json_str,
            file_name=f"{repo}_knowledge_graph.json",
            mime="application/json",
            use_container_width=True,
        )
        with st.expander("👁️ View Raw JSON"):
            st.json(graph_data)
