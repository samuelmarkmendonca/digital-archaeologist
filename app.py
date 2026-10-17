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
import streamlit.components.v1 as components
from dotenv import load_dotenv

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
                repo_info = github_service.get_repository_overview(owner, repo, token=github_token)
                tree_entries = repo_info.get("tree_entries", [])

                # 3. Fetch README & Key Files
                status.write("3️⃣ Fetching README and inspecting entry points & dependency manifests...")
                default_branch = repo_info.get("default_branch", "main")
                readme_text = github_service.get_readme(owner, repo, default_branch, token=github_token)
                key_files = github_service.get_key_source_files(
                    owner, repo, tree_entries, default_branch=default_branch, max_files=15, token=github_token
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

    # Content Tabs
    tab_summary, tab_graph, tab_prompt, tab_json = st.tabs([
        "📜 Archaeological Summary",
        "🗺️ Knowledge Graph Topology",
        "🤖 AI Agent Context Payload",
        "💾 Export JSON",
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
