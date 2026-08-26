# Nous — FYP (TP068819)

**Nous** (mind / intellect) — graph-based multi-agent AI system for autonomous research and lifelong personal knowledge management.

**Student:** Wong Yan Hao  
**Programme:** B.Sc. (Hons) Computer Science (Artificial Intelligence)

## Current Phase

**Agent layer + Mission Control** — Hermes-like memory & goal loops around the LangGraph research engine; live agent monitor UI. See [`docs/AGENT_LAYER.md`](docs/AGENT_LAYER.md).

## Prerequisites

- Python 3.12+
- **Groq API key** (default LLM — fast cloud inference): [console.groq.com](https://console.groq.com/keys)
- [Ollama](https://ollama.com/) running locally **for embeddings only**
- Model: `nomic-embed-text`

```bash
ollama pull nomic-embed-text
```

Set in `.env`:
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
LLM_MODEL=openai/gpt-oss-120b
GROQ_FALLBACK_MODEL=qwen/qwen3-32b
```

To use local Ollama for the LLM instead, set `LLM_PROVIDER=ollama` and `LLM_MODEL=qwen3:8b` (or another Ollama model).

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

20 queries grounded in the **dlm vault** ([`evaluation/benchmarks.json`](evaluation/benchmarks.json)). The old Java 52-query set was retired (those lectures are not ingested).

```bash
# Preview
python scripts/run_evaluation.py --dry-run

# Smoke (Ask + honest gap)
python scripts/run_evaluation.py --ids PV01,PV03,EG01 --sleep 8

# Full suite (pace the API)
python scripts/run_evaluation.py --sleep 15 -o evaluation/results/nous_dlm.json

# Resume
python scripts/run_evaluation.py --sleep 15 --resume evaluation/results/nous_dlm.json -o evaluation/results/nous_dlm.json

python scripts/generate_eval_report.py evaluation/results/nous_dlm.json
```

**Baseline comparison:** Same questions in Claude/Grok **chat** (no vault), score 1–5 in a copy of [`evaluation/baseline_template.csv`](evaluation/baseline_template.csv):

```bash
python scripts/compare_baselines.py evaluation/results/nous_dlm.json evaluation/baselines_scored.csv
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
evaluation/           20-query DLM benchmark, UAT template, results
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