# Second Brain — FYP (TP068819)

Graph-based multi-agent AI system for autonomous research and lifelong personal knowledge management.

**Student:** Wong Yan Hao  
**Programme:** B.Sc. (Hons) Computer Science (Artificial Intelligence)

## Current Phase

**Phase 5** — Evaluation, baselines, UAT, and release packaging.

## Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com/) running locally
- Models: `nomic-embed-text`, `llama3.2:3b`

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

## Setup

```bash
cd fyp-second-brain
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Usage

### Verify setup

```bash
python scripts/verify_setup.py
```

### Ingest documents

Drop PDFs or text files into `data/documents/`, then:

```bash
python scripts/ingest.py --input data/documents
```

### Ingest from a custom folder

```bash
python scripts/ingest.py --input "/path/to/your/documents"
```

### Query your knowledge base

Single question:

```bash
python scripts/query.py "What is polymorphism in Java?"
```

Interactive mode:

```bash
python scripts/query.py
```

### Multi-agent research (Phase 2)

Autonomous research with planner, retriever, analyst, verifier, and synthesizer agents:

```bash
python scripts/research.py "What are servlets in Java?"
python scripts/research.py "Explain EJB architecture" --verbose
```

### Hybrid retrieval (Phase 3)

The retriever agent routes queries to personal documents, Tavily web search, and arXiv. Add your Tavily API key to `.env`:

```bash
TAVILY_API_KEY=tvly-your-key-here
```

arXiv works without an API key. If `TAVILY_API_KEY` is unset, web search is skipped and arXiv + personal docs are still used.

### Desktop app (Phase 4)

Requires [Node.js](https://nodejs.org/) and [Rust](https://rustup.rs/).

```bash
# From project root — sidecar starts automatically with the app
cd desktop
npm install
npm run tauri dev
```

The Tauri app spawns the Python sidecar (`sidecar/server.py`) on `http://127.0.0.1:8765`.

To run the sidecar standalone (for debugging):

```bash
./scripts/start_sidecar.sh
```

Desktop features:
- **Research** — full multi-agent workflow with report viewer
- **Quick Query** — fast personal RAG
- **Documents** — ingest folders via file picker
- **Settings** — Ollama models, Tavily API key, feature toggles

### Evaluation (Phase 5)

52 benchmark queries in [`evaluation/benchmarks.json`](evaluation/benchmarks.json):

```bash
# Preview all 52 queries
python scripts/run_evaluation.py --dry-run

# Run a quick subset (2 queries)
python scripts/run_evaluation.py --limit 2

# Run full suite (~60–90 min for all 52 research+query)
python scripts/run_evaluation.py

# Resume interrupted run
python scripts/run_evaluation.py --resume evaluation/results/run_YYYYMMDD_HHMMSS.json

# Generate markdown report
python scripts/generate_eval_report.py evaluation/results/run_YYYYMMDD_HHMMSS.json
```

**Baseline comparison:** Run the same queries through Claude and Grok manually, score 1–5 in [`evaluation/baseline_template.csv`](evaluation/baseline_template.csv), then:

```bash
python scripts/compare_baselines.py evaluation/results/run_*.json evaluation/baseline_scores.csv
```

**UAT:** Use [`evaluation/uat_questionnaire.md`](evaluation/uat_questionnaire.md) with 5–8 participants.

**Release build:**

```bash
./scripts/package_release.sh
```

## Project structure

```
src/second_brain/     Core package (config, memory, ingestion, graph)
sidecar/              FastAPI HTTP server for desktop app
desktop/              Tauri 2.0 + Svelte frontend
evaluation/           52 benchmark queries, UAT template, results
scripts/              CLI entry points + evaluation runners
data/documents/       User document drop folder
data/chroma/          Persistent vector database (gitignored)
tests/                Unit tests
```

## Development roadmap

| Phase | Goal |
|-------|------|
| 0 | Setup + ingestion into Chroma |
| 1 | Personal document RAG in terminal |
| 2 | Multi-agent workflow with self-critique |
| 3 | Hybrid retrieval (personal + web + arXiv) |
| 4 | Tauri 2.0 desktop app (Svelte) |
| 5 | Evaluation + packaging (current) |