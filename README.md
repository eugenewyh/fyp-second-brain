# Second Brain — FYP (TP068819)

Graph-based multi-agent AI system for autonomous research and lifelong personal knowledge management.

**Student:** Wong Yan Hao  
**Programme:** B.Sc. (Hons) Computer Science (Artificial Intelligence)

## Current Phase

**Phase 3** — Hybrid retrieval (personal + web + arXiv).

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

## Project structure

```
src/second_brain/     Core package (config, memory, ingestion, graph)
scripts/              CLI entry points
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
| 5 | Evaluation + packaging |