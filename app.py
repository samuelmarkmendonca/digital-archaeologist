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

# Load environment variables with override=True to catch runtime .env changes
load_dotenv(override=True)


def render_cytoscape_html(elements: list[dict[str, Any]], layout_name: str = "cose") -> str:
    """Generate standalone HTML for an interactive Cytoscape.js network graph."""
    elements_json = json.dumps(elements)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
      <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
          background-color: #0e1117;
          color: #c9d1d9;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
          overflow: hidden;
        }}
        #cy {{
          width: 100vw;
          height: 520px;
          display: block;
        }}
        #overlay {{
          position: absolute;
          top: 12px;
          left: 12px;
          background: rgba(22, 27, 34, 0.9);
          backdrop-filter: blur(8px);
          border: 1px solid rgba(48, 54, 61, 0.9);
          border-radius: 8px;
          padding: 10px 14px;
          font-size: 13px;
          max-width: 420px;
          pointer-events: none;
          z-index: 100;
          box-shadow: 0 4px 16px rgba(0,0,0,0.6);
        }}
        .legend {{
          position: absolute;
          bottom: 12px;
          right: 12px;
          background: rgba(22, 27, 34, 0.9);
          border: 1px solid rgba(48, 54, 61, 0.9);
          border-radius: 8px;
          padding: 8px 14px;
          font-size: 12px;
          z-index: 100;
          display: flex;
          gap: 14px;
        }}
        .dot {{
          width: 10px;
          height: 10px;
          border-radius: 50%;
          display: inline-block;
          margin-right: 5px;
        }}
      </style>
    </head>
    <body>
      <div id="overlay">
        <strong id="node-title">🗺️ Interactive Cytoscape Knowledge Graph</strong>
        <div id="node-detail" style="color: #8b949e; margin-top: 4px; font-size: 12px; line-height: 1.4;">
          Scroll to zoom • Drag nodes freely • Click any node to inspect exports & imports
        </div>
      </div>
      <div class="legend">
        <span><span class="dot" style="background:#2ea44f;"></span>Entrypoint</span>
        <span><span class="dot" style="background:#1f6feb;"></span>Module</span>
        <span><span class="dot" style="background:#d29922;"></span>Config / Manifest</span>
      </div>
      <div id="cy"></div>
      <script>
        var elements = {elements_json};
        var cy = cytoscape({{
          container: document.getElementById('cy'),
          elements: elements,
          style: [
            {{
              selector: 'node',
              style: {{
                'label': 'data(label)',
                'color': '#f0f6fc',
                'font-size': '11px',
                'text-valign': 'bottom',
                'text-margin-y': 5,
                'background-color': '#1f6feb',
                'border-width': 2,
                'border-color': '#388bfd',
                'width': 28,
                'height': 28
              }}
            }},
            {{
              selector: 'node[type = "entrypoint"]',
              style: {{
                'background-color': '#2ea44f',
                'border-color': '#3fb950',
                'shape': 'diamond',
                'width': 36,
                'height': 36
              }}
            }},
            {{
              selector: 'node[type = "config"]',
              style: {{
                'background-color': '#d29922',
                'border-color': '#e3b341',
                'shape': 'hexagon',
                'width': 26,
                'height': 26
              }}
            }},
            {{
              selector: 'edge',
              style: {{
                'width': 1.8,
                'line-color': '#30363d',
                'target-arrow-color': '#388bfd',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'opacity': 0.75
              }}
            }},
            {{
              selector: 'node:selected',
              style: {{
                'border-width': 4,
                'border-color': '#ff7b72',
                'background-color': '#f85149'
              }}
            }}
          ],
          layout: {{
            name: '{layout_name}',
            animate: true,
            animationDuration: 700,
            padding: 30
          }}
        }});

        cy.on('tap', 'node', function(evt){{
          var n = evt.target;
          document.getElementById('node-title').innerHTML = '📄 ' + n.data('label') + ' (' + n.data('language') + ')';
          document.getElementById('node-detail').innerHTML = 
            '<b>Path:</b> ' + n.data('path') + '<br/>' +
            '<b>Type:</b> ' + n.data('type') + '<br/>' +
            '<b>Exports:</b> ' + n.data('exports') + '<br/>' +
            '<b>Imports:</b> ' + n.data('imports');
        }});

        cy.on('tap', function(evt){{
          if(evt.target === cy){{
            document.getElementById('node-title').innerHTML = '🗺️ Interactive Cytoscape Knowledge Graph';
            document.getElementById('node-detail').innerHTML = 'Scroll to zoom • Drag nodes freely • Click any node to inspect exports & imports';
          }}
        }});
      </script>
    </body>
    </html>
    """


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

# --- Load Secrets from Environment ---
raw_gemini_key = os.getenv("GEMINI_API_KEY", "")
gemini_key = raw_gemini_key.strip().strip('"').strip("'").strip()

raw_github_token = os.getenv("GITHUB_TOKEN", "")
clean_github_token = raw_github_token.strip().strip('"').strip("'").strip()
github_token = clean_github_token if clean_github_token else None

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("⛏️ Digital Archaeologist")
    
    # Environment Status
    if gemini_key and not gemini_key.startswith("your_"):
        st.success("🟢 Gemma API Key Loaded (.env)")
    else:
        st.warning("⚠️ Add `GEMINI_API_KEY` to your `.env` file")

    if github_token:
        st.success("🟢 GitHub Token Active (5,000 req/hr)")
    else:
        st.caption("ℹ️ Unauthenticated GitHub API (60 req/hr)")

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
                repo_info = github_service.get_repository_overview(owner, repo, token=github_token)
                tree_entries = repo_info.get("tree_entries", [])

                # 3. Fetch README & Key Files
                status.write("3️⃣ Inspecting entry points, manifests & source signatures...")
                default_branch = repo_info.get("default_branch", "main")
                readme_text = github_service.get_readme(owner, repo, default_branch, token=github_token)
                key_files = github_service.get_key_source_files(
                    owner, repo, tree_entries, default_branch=default_branch, max_files=15, token=github_token
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
                    api_key=gemini_key,
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
        st.metric(
            "Raw Codebase (Est. Tokens)",
            f"{token_stats.get('raw_codebase_tokens', 0):,}",
            help="Exact sum of all source file sizes retrieved from the GitHub Git Tree API, divided by ~4 bytes/token (standard BPE tokenization).",
        )
    with m2:
        st.metric(
            "Knowledge Graph (Tokens)",
            f"{token_stats.get('knowledge_graph_tokens', 0):,}",
            help="Token size of the serialized Knowledge Graph JSON payload (nodes, symbol exports, and dependency edges) divided by ~4 bytes/token.",
        )
    with m3:
        st.metric(
            "Context Token Reduction",
            token_stats.get("token_reduction_percent", "N/A"),
            help="Mathematical percentage of context saved: (1 - (Graph Tokens / Raw Tokens)) * 100.",
        )
    with m4:
        st.metric(
            "Graph Nodes & Edges",
            f"{len(graph_data['nodes'])} / {len(graph_data['edges'])}",
            help="Nodes represent identified source code modules/entry points; edges represent verified import/dependency linkages.",
        )

    st.info(
        f"💡 **Token Economics Math**: The raw codebase totals **{token_stats.get('raw_codebase_bytes', 0):,} bytes** across {len(graph_data['nodes'])} files. "
        f"At standard BPE tokenization (~4 bytes/token), feeding this entire project raw would cost **~{token_stats.get('raw_codebase_tokens', 0):,} tokens**. "
        f"Our compact topological Knowledge Graph packs the full architectural context into only **~{token_stats.get('knowledge_graph_tokens', 0):,} tokens** — a **{token_stats.get('token_reduction_percent', '90%')} reduction**!"
    )

    # Two Primary Tabs: Summary in MD format & Knowledge Graph in Cytoscape.js JSON
    tab_graph, tab_summary, tab_json = st.tabs([
        "🗺️ Cytoscape.js Knowledge Graph",
        "📜 Architectural Summary (Markdown)",
        "💾 Cytoscape.js JSON Format",
    ])

    with tab_summary:
        st.markdown("### 🏛️ Executive Codebase Summary & Resurrection Guide")
        
        # Download button for the markdown summary
        st.download_button(
            label="⬇️ Download Archaeological Summary (ARCHAEOLOGY_REPORT.md)",
            data=ai_summary,
            file_name=f"{repo}_ARCHAEOLOGY_REPORT.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.write("")
        st.markdown(ai_summary)
        
        with st.expander("📋 View / Copy Raw Markdown Content"):
            st.code(ai_summary, language="markdown")

    with tab_graph:

        
        st.markdown("### 🗺️ Interactive Cytoscape.js Knowledge Graph")
        st.caption("Physics-directed interactive topology. Drag nodes, scroll to zoom, and tap any node to inspect exports & imports.")

        graph_col1, graph_col2 = st.columns([3, 1])
        with graph_col2:
            layout_choice = st.selectbox(
                "Graph Layout Engine",
                options=["cose", "concentric", "circle", "breadthfirst", "grid"],
                index=0,
                help="Choose physics simulation (cose), concentric, or circular layout",
            )
        with graph_col1:
            st.markdown(f"**Visualizing top {len(graph_data.get('cytoscape_elements', []))} elements** with interactive physics simulation.")

        # Render Interactive Cytoscape Graph
        cy_elements = graph_data.get("cytoscape_elements", [])
        if cy_elements:
            cy_html = render_cytoscape_html(cy_elements, layout_name=layout_choice)
            components.html(cy_html, height=540)
        else:
            st.info("No source files found to construct network graph.")

        # Secondary static views in expander
        with st.expander("📐 Alternative Views (Mermaid Diagram & Node Table)", expanded=False):
            mermaid_code = graph_data.get("mermaid_diagram", "")
            if mermaid_code:
                st.markdown("**Static Mermaid Diagram:**")
                st.markdown(f"```mermaid\n{mermaid_code}\n```")

            st.markdown("**Detailed Node Explorer:**")
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
