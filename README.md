# ⛏️ Digital Archaeologist

> **Excavate Unfamiliar & Abandoned Codebases • Reconstruct Architecture & Undocumented Behavior • Interactive Cytoscape.js Knowledge Graph • 90%+ Token Optimization for AI Agents**

Digital Archaeologist is built for developers, teams, and AI agents handed an unfamiliar repository, a set of complex configuration files, or a dormant, long-abandoned side project. 

Instead of reading hundreds of forgotten files or dumping raw source code into an LLM (which burns tens of thousands of tokens and triggers context rot), Digital Archaeologist provides an automated, token-optimized pipeline:
1. **Fetch & Reformat**: Excavates repository structure, manifests, and key entry points via GitHub REST API, stripping noise for up to **90%+ token reduction**.
2. **Gemma Reverse-Engineering**: Synthesizes a structured **Markdown Architectural Summary**, tracing execution lifecycles and exposing **undocumented behaviors, hidden environment flags, and quirks**.
3. **Cytoscape.js Knowledge Graph**: Deterministically models dependencies into standard **Cytoscape.js JSON format** and renders an interactive, navigable graph.
4. **Simple Front-End**: Clean, focused interface requiring **only the GitHub URL** to output the complete technical explanation and interactive graph.

---

## 🌟 Key Features

- **🏛️ Executive Codebase Summary (Markdown)**: Reconstructs how the system works at a high level, its core domain, and component hierarchy.
- **🗺️ Interactive Cytoscape.js Knowledge Graph**: Interactive force-directed canvas with node inspector, degree sizing, layout switching (`cose`, `concentric`, `breadthfirst`), and color-coded entity types (Entrypoints, Modules, Services, Configs, Utils).
- **🕵️ Undocumented Behavior & Quirk Detection**: Automatically flags hidden `os.environ` / `os.getenv` lookups, hardcoded `0.0.0.0` bindings, dynamic `eval`/`exec`, silent exception swallowing (`except: pass`), and global mutable state.
- **⚡ 90%+ Token Optimization**: Compares estimated raw codebase token size against the condensed Knowledge Graph, yielding 85%–95% token savings for downstream LLM prompts and AI coding agents (Devin, Cursor, Windsurf, Claude).
- **🧭 Project Resurrection Guide**: Delivers a step-by-step checklist to resurrect the dormant codebase: dependencies to install, missing environment variables, key files to inspect first, and high-risk technical debt.
- **💾 Cytoscape.js JSON Export**: Download standard `elements.nodes` and `elements.edges` JSON for external graph visualizers or automated pipelines.

---

## 🔄 End-to-End Pipeline

```text
GitHub Repo URL
      │
      ▼
1. Fetch Tree & Entrypoints (github_service.py)
      │
      ▼
2. Token Optimization & AST Signature Reformatting (graph_service.py)
   [Eliminates bloat & whitespace -> 90%+ token reduction]
      │
      ▼
3. Gemma Semantic Reverse-Engineering (gemma_service.py via google-genai)
   [Reconstructs architecture, traces execution, identifies undocumented gotchas]
      │
      ▼
4. Dual Artifact Generation:
   ├── 📜 Markdown Summary (.md)
   └── 🗺️ Cytoscape.js JSON Graph (knowledge_graph.json)
      │
      ▼
5. Interactive Front-End (app.py + cytoscape_component.py)
   [Only inputs Git URL -> displays interactive Cytoscape graph & Markdown report]
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose & Rationale |
|---|---|---|
| **Frontend / Web UI** | [Streamlit](https://streamlit.io/) + Vanilla CSS | Clean, simple interface: single Git URL input, token savings hero cards, tabbed outputs. |
| **Graph Visualization** | [Cytoscape.js](https://js.cytoscape.org/) | Interactive force-directed graph canvas with zoom/pan, layout switcher, and node inspector drawer. |
| **HTTP Client** | [Requests](https://requests.readthedocs.io/) | GitHub REST v3 API client for recursive trees, READMEs, manifests, and source blobs. |
| **Knowledge Graph Engine** | Pure Python (`re`, standard library) | AST/regex parsing of imports, exported symbols, undocumented behavior detection, and token economics. |
| **AI / LLM Integration** | [Google GenAI SDK](https://github.com/googleapis/python-genai) (`google-genai`) | **Gemma Track**: Gemma 4 (`gemma-4-26b-a4b-it`) / Gemma 3 for architectural synthesis and resurrection advice. |
| **Configuration** | [python-dotenv](https://github.com/theskumar/python-dotenv) | Loads `GEMINI_API_KEY` and optional `GITHUB_TOKEN` from `.env`. |

---

## 💎 How Gemma is Harnessed in a Smart Way

Naively feeding raw source repositories into LLMs burns tokens, triggers rate limits, and causes catastrophic context rot. Digital Archaeologist implements a **Two-Tier Intelligence Pipeline**:

1. **Tier 1 (Deterministic Token Optimization)**: Python parses the full repository tree, extracts imports/exports, filters noise, identifies quirks, and maps modules into a compact node-edge topological model (`graph_service.py`). This cuts raw context volume by **85%–95%** *before* touching the model.
2. **Tier 2 (Gemma Semantic Reasoning)**: Gemma receives the pre-compressed Knowledge Graph + README + key entry point signatures at `temperature=0.2`. Gemma produces grounded explanations of system architecture, execution lifecycles, undocumented behaviors, and resurrection steps.
3. **Resilient Fallback**: Graceful cascade across the Gemma family (`gemma-4-26b-a4b-it` → `gemma-4-31b-it` → `gemma-3-27b-it`) and deterministic offline mode when no API key is provided.

---

## 📁 Repository Structure

```text
digital-archaeologist/
├── app.py                  # Streamlit application UI (simple input, summary & graph display)
├── cytoscape_component.py  # Interactive Cytoscape.js HTML component with toolbar & inspector
├── graph_service.py        # Token optimizer, quirk detector, and Cytoscape.js JSON builder
├── github_service.py       # GitHub REST API client (tree, README, key entry points)
├── gemma_service.py        # Gemma reverse-engineering and architectural prompt engine
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variable template
├── AGENTS.md               # Architecture specifications and contracts
└── README.md               # Project documentation
```

---

## 🚀 Quickstart Guide

### 1. Setup Environment

```bash
# Clone the repository
git clone https://github.com/samuelmarkmendonca/digital-archaeologist.git
cd digital-archaeologist

# Activate virtual environment
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set your Gemini API key in `.env`:

```ini
GEMINI_API_KEY="your-gemma-api-key-here"
```
*(Note: Digital Archaeologist is fully functional in deterministic mode even without an API key!)*

### 3. Launch Application

```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501`. Enter any public GitHub repository URL (e.g., `https://github.com/pallets/flask` or `https://github.com/psf/requests`) and click **⛏️ Excavate**!