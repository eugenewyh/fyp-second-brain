# Nous — FYP (TP068819)

**Nous** (mind / intellect) — graph-based multi-agent AI system for autonomous research and lifelong personal knowledge management.

**Student:** Wong Yan Hao  
**Programme:** B.Sc. (Hons) Computer Science (Artificial Intelligence)

## Download

**[Latest release (macOS `.dmg`)](https://github.com/eugenewyh/fyp-second-brain/releases/latest)** — no setup; NVIDIA AI included.

> This repo is **private**. Download links work for collaborators; invite evaluators on GitHub or share release assets directly.

| Platform | Install |
|----------|---------|
| macOS (Apple Silicon) | Download `.dmg`, drag to Applications. If blocked, right-click → **Open** once. |
| Windows | See [releases](https://github.com/eugenewyh/fyp-second-brain/releases) when a Windows build is published. |
| From source | [Development setup](#development-from-source) below |

Install details and maintainer publish steps: [`docs/RELEASE.md`](docs/RELEASE.md).

## Current Phase

**Agent layer + Mission Control** — Hermes-like memory & goal loops around the LangGraph research engine; live agent monitor UI. See [`docs/AGENT_LAYER.md`](docs/AGENT_LAYER.md).

## Prerequisites

### Development (from source)

- Python 3.12+
- **NVIDIA Build NIM** (default LLM — included via `NOUS_NVIDIA_API_KEY` in release builds; dev uses `.env`)
- **Embeddings:** bundled **fastembed** (`BAAI/bge-small-en-v1.5`) — no Ollama required for vault search
- [Ollama](https://ollama.com/) optional for local chat only (`LLM_PROVIDER=ollama`)

Set in `.env` (dev):

```bash
LLM_PROVIDER=nvidia
NOUS_NVIDIA_API_KEY=nvapi_your_key_here
LLM_MODEL=nvidia/nemotron-3-super-120b-a12b
LLM_FALLBACK_MODEL=nvidia/nemotron-3-nano-30b-a3b
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

Optional BYOK providers (Groq, OpenRouter, etc.) are configured in **Settings → Models**.

To use local Ollama for the LLM instead, set `LLM_PROVIDER=ollama` and `LLM_MODEL=qwen3:8b`.

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

Drop PDFs, Word (.docx), or text files into `data/documents/` (nested topic folders are supported), then:

```bash
python scripts/ingest.py --input data/documents
```

After upgrading ingest or embedding settings, reset and re-ingest so nested files, PDF text, and the BM25 index stay in sync:

```bash
python scripts/ingest.py --input data/documents --reset
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
- **Settings** — NVIDIA included; optional BYOK providers; feature toggles

User data in release builds lives in the OS app-data folder (`~/Library/Application Support/com.tp068819.nous` on macOS, `%APPDATA%\com.tp068819.nous` on Windows), not inside the app bundle.

### Evaluation (Phase 5)

20 queries grounded in the **Plants** demo vault ([`evaluation/benchmarks.json`](evaluation/benchmarks.json)). Prepare the corpus first:

```bash
python scripts/prepare_eval_corpus.py
```

```bash
# Preview
python scripts/run_evaluation.py --dry-run

# Smoke (Ask + honest gap)
python scripts/run_evaluation.py --ids PV01,PV03,EG01 --sleep 8

# Full suite (pace the API)
python scripts/run_evaluation.py --sleep 15 -o evaluation/results/nous_plants.json

# Resume
python scripts/run_evaluation.py --sleep 15 --resume evaluation/results/nous_plants.json -o evaluation/results/nous_plants.json

python scripts/generate_eval_report.py evaluation/results/nous_plants.json
```

**Baseline comparison:** Same questions in Claude/Grok **chat** (no vault), score 1–5 in a copy of [`evaluation/baseline_template.csv`](evaluation/baseline_template.csv):

```bash
python scripts/compare_baselines.py evaluation/results/nous_plants.json evaluation/baselines_scored.csv
```

**UAT:** Use [`evaluation/uat_questionnaire.md`](evaluation/uat_questionnaire.md) with 5–8 participants.

**Release build** (macOS — run on a Mac; Windows — use `build_sidecar_bundle.ps1` + `npm run tauri build` on Windows):

```bash
export NOUS_NVIDIA_API_KEY=nvapi-...   # required — Nous-included AI for users
# optional: GEMINI_API_KEY, TAVILY_API_KEY
./scripts/package_release.sh
```

Smoke-test the sidecar bundle without installing the `.app`:

```bash
./scripts/build_sidecar_bundle.sh
./scripts/smoke_release.sh
```

Artifacts: `desktop/src-tauri/target/release/bundle/dmg/` (`.dmg`) or Windows installer under `bundle/nsis/`.

Publish to GitHub Releases:

```bash
./scripts/publish_github_release.sh --tag v0.1.0-fyp
```

See [`docs/RELEASE.md`](docs/RELEASE.md).

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