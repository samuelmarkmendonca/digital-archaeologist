# 📋 Digital Archaeologist — Implementation Plan

> **Problem**: Developers returning to abandoned side projects or inheriting dormant codebases struggle to understand how the system works. Moreover, passing full codebases to AI coding agents causes severe token bloat and context degradation.
> **Solution**: Digital Archaeologist excavates the codebase, generates an architectural summary, and builds a **Token-Efficient Knowledge Graph** providing up to 90%+ context token savings for downstream LLMs.

---

## 📑 Core Execution Phases

### Phase 1: Environment & Project Setup
- Python 3.10+ virtual environment (`.venv/`).
- Core dependencies: `streamlit`, `requests`, `google-genai`, `python-dotenv`.
- Configuration: `.env.example`, `.gitignore`.

### Phase 2: GitHub Repository Excavation Service (`github_service.py`)
- Parse and validate GitHub repository URLs.
- Fetch repository metadata and recursive git trees (`GET /git/trees/{branch}?recursive=1`).
- Fetch README artifacts and dependency manifests (`package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`).
- Fetch contents of top entry points and core modules for AST/regex parsing.

### Phase 3: Knowledge Graph Engine & Token Economics (`graph_service.py`)
- Regex-based AST symbol and import extraction across Python, JavaScript, TypeScript, Go, and Rust.
- Identify entry points (`app.py`, `main.py`, `index.js`, etc.) and internal modules.
- Construct topological nodes and edges representing dependencies.
- Generate visual Mermaid diagrams for interactive UI rendering.
- Compute token metrics: Estimated Raw Codebase Tokens vs. Knowledge Graph Tokens and % reduction.

### Phase 4: Gemini / Gemma Architectural Synthesis (`gemma_service.py`)
- Ingest repository overview, README excerpt, and condensed Knowledge Graph topology.
- Produce 5-point Archaeological Report:
  1. Executive Codebase Summary (what the project does and its problem domain).
  2. Architectural Topology & Module Breakdown.
  3. Entry Points & Execution Lifecycle.
  4. Project Resurrection Guide (where to pick up, dependencies, tech debt).
  5. Token-Efficient AI Agent Context Prompt (ready for Cursor, Devin, Claude, ChatGPT).
- Implement robust fallback if API key is not yet configured.

### Phase 5: Streamlit Web UI & AI Exporter (`app.py`)
- Modern dark/light UI with token reduction badge and excavation status tracker.
- Presets for popular codebases (Flask, FastAPI, Requests).
- Tab 1: 📜 Archaeological Summary & Resurrection Guide.
- Tab 2: 🗺️ Knowledge Graph Topology (Mermaid diagram & node table).
- Tab 3: 🤖 Copy-Paste AI Agent Context Payload.
- Tab 4: 💾 Export `knowledge_graph.json`.

### Phase 6: End-to-End Validation & Polish
- Validate against repositories of varying sizes and languages.
- Test export payloads in external LLM prompts.
