# Agent layer (Hermes-like autonomy around LangGraph)

Nous keeps the **LangGraph research engine** for reliable, evaluable multi-agent research. On top of it sits a thin **agent layer** that makes the system feel autonomous:

1. **Auto-recall** — before planning, retrieve prior understanding in order: chat `memory.md` → matching **claims** → consolidated `project.md` → vault (Chroma).
2. **Auto-memory write** — after each run: research report + learning card under the chat, **claim cards** (create or revise), update chat `memory.md`, **consolidate** `project.md`, append `project-log.md`, re-index.
3. **Confidence** — heuristic score from retrieval, grounding, revisions, and gaps (stop signal for goals).
4. **Goal mode** — multi-pass loop (`POST /api/goals/stream`) that deepens open questions until confidence or max passes.
5. **Chat-first UI** — Project → Chat transcript with readable status lines; Details shows “This chat remembers” / “Project believes”; LangGraph stays the skill, not the primary chrome.

## Memory hierarchy

```
{project}/
  memory/
    project.md                 # consolidated understanding (Settled / Open / Revisions / Chats)
    project-log.md             # append-only history (not rewritten)
    claims/{slug}.md           # durable claim cards (active | superseded)
    agents/{session_id}/
      memory.md                # this chat’s durable understanding
      learnings/               # per-run learning cards
  research/                    # full reports
```

**Claims:** extracted from key findings; similar claims **revise** prior ones (`supersedes` + `Revises [[old-slug]]`).  
**Consolidation:** `project.md` is rebuilt from active claims + open questions (deterministic; optional fast-LLM polish).  
Legacy cards may still live under `memory/learnings/` (project-level). New writes with a `session_id` use the agents path.

## Model roles (peer-aligned)

Inspired by Hermes/Factory **main vs light** tiers and Khoj **bundled embeddings**:

| Role | Env | Used by |
|------|-----|---------|
| **Main (heavy)** | `LLM_MODEL` | Planner, synthesizer |
| **Fast (light)** | `LLM_FAST_MODEL` (optional) | Ask / chat, verifier, analyst |
| **Fallback** | `LLM_FALLBACK_MODEL` | Rate-limit failover |
| **Embeddings** | `EMBEDDING_PROVIDER` + `EMBEDDING_MODEL` | Vault Chroma search |

**Embedding providers:** `fastembed` (default, bundled — **Ollama not required**), `ollama`, `openai_compatible`. Changing provider/model sets `reindex_required` until you re-ingest.

Prefer a **stable paid/reliable** chat model for demos. Free OpenRouter trials are optional/experimental.

## Modes

| Mode | Plan review | Multi-pass | Memory |
|------|-------------|------------|--------|
| **Agent (goal)** | Off | Up to `MAX_GOAL_PASSES` (default 1) | Always |
| **Single-pass research** | Optional (default on) | Single pass (manual Continue) | Always |
| **Ask library** | N/A | RAG chat (fast model) | Read-only |

## Key paths

| Piece | Location |
|-------|----------|
| Learning cards + consolidation | `src/second_brain/memory/learning.py` |
| Claim cards | `src/second_brain/memory/claims.py` |
| Recall | `src/second_brain/memory/recall.py` |
| Embeddings | `src/second_brain/memory/embeddings.py` |
| LLM roles | `src/second_brain/memory/llm.py` |
| Goal loop | `src/second_brain/agent/goal_loop.py` |
| Graph hooks | `src/second_brain/graph.py` |
| Goal SSE | `sidecar/server.py` → `/api/goals/stream` |

## Env flags

- `AUTO_MEMORY` (default true)
- `AUTO_RECALL` (default true)
- `MAX_GOAL_PASSES` (default 1)
- `MAX_REVISIONS` (default 1)
- `MIN_GOAL_CONFIDENCE` (default 0.65)
- `AGENT_MODE_DEFAULT` (`goal`)
- `PLAN_REVIEW_DEFAULT` (true)
- `EMBEDDING_PROVIDER` (`fastembed` \| `ollama` \| `openai_compatible`)
- `LLM_FAST_MODEL` (optional light tier)

## What this is not

Not Hermes Agent runtime, not Factory Router / Custom Droids, not Streamlit, not free-form multi-agent group chat. The research **skill** remains the fixed five-node graph for quality and evaluation. Pipeline roles are not separate user-facing personas — each **chat session** is the agent the user talks to.
