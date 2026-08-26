# Nous — current status (agent handoff)

**Date:** 24 Aug 2026  
**Repo:** `fyp-second-brain`  
**Product name in the desktop bundle:** Nous  
**Python package:** `second_brain`

This file is the source of truth for *how the app works today*. Prefer it over `README.md`, `PROJECT_SUMMARY.md`, `DEMO.md`, and `docs/AGENT_LAYER.md` when those conflict.

---

## One-line product

Local-first **second brain**: each **channel** is a lifelong topic folder (vault memory). You talk in that channel. The **Manager** routes Teach / Research / Watch / Ask as jobs in the **same thread**. They share that topic’s memory.

Demo line: *A channel is a topic. You talk there. The Manager dispatches skills that share that memory.*

---

## Mental model (do not invert)

| Messaging idea | In Nous | Memory |
|----------------|---------|--------|
| **Channel** | Vault topic folder (`#FYP`, `#DLM`) | `{topic}/memory`, `IDEA.md`, reports, watches |
| **Chat** | One Manager thread per channel | Reads/writes **that channel only** |
| **Skills** | file / answer / research / watch (jobs) | Not sidebar people; LangGraph nodes stay inside Research |

**Do not:**

- Nest Memory / Teach / Research / Watch as separate chats under a channel
- Hire / add agents / New agent interview
- Put Planner / Retriever / Verifier / Analyst / Synthesizer in the sidebar
- Mix two topics in one session’s `projectPath`
- Treat pipeline roles as members

LangGraph five-node graph (**planner → retriever → analyst ⇄ verifier → synthesizer**) stays **inside Research** as status lines.

---

## User-facing surfaces

Desktop: Tauri 2 + Svelte 5 (`desktop/`). Home is chat (`ChatHome` → `AgentPane`).

**Sidebar**

- **+** — New channel only
- **Memory** (nav) — knowledge graph (`MemoryHome`), not a chat agent
- **Watch** (nav) — watch list / editor
- Flat channel list: `#Name` rows (one session per folder)

**Chat**

- Bootstrap (offline, no AI key, no channel): `ChatLanding`
- Empty channel: static opener, then Manager clarify (max 2) or dispatch
- Ready channel: one composer — “Message this channel…”
- All jobs (file / answer / research / watch) run in the open channel session

**Other**

- Document peek beside chat
- Settings / ingest sheets
- Command palette (`⌘K`)

---

## Jobs (Manager router)

User message → `take_turn` (`src/second_brain/agent/manager.py`) → job, then the desktop runs the skill **in the same session**.

| Job | What happens |
|-----|--------------|
| `answer` | RAG / recall from this channel |
| `file` | Digest notes/files → claims (`origin=dump`) |
| `research` | LangGraph run; report + claims if policy says so |
| `watch` | Create/run a standing brief |
| `refuse` | Thin memory, don’t pretend to know |
| `retarget` / `merge` / `split` | Topic-folder ops |

Dispatch-first: clear tasks run immediately. Vague messages get at most **two** clarifying asks.

---

## Memory contract (unchanged)

Reuse: `claims.py`, `digest_link.py`, `learning.py` (`persist_research_memory`), `recall.py`, `goal_loop.py`, `daily_review.py`, sidecar scheduler.

- One chat binds to one vault topic (`projectPath` / `project_path`).
- Writes require a topic path. Missing topic → skip write, `memory_written: false`.
- Claims live at `{topic}/memory/claims/{slug}.md`.
- Status: `settled` (legacy `active`) \| `contested` \| `superseded`.
- Origin: `dump` \| `watch` \| `research`. Dump is protected; watch must not silently overwrite dump.

---

## Architecture

```
desktop/          Tauri 2 + Svelte 5 + SvelteKit (static)
  src/lib/components/app/   UI (sidebar, chat, graph, watch, settings)
  src/lib/stores/           assistant, workspace, app, tabs, connection
  src/lib/assistant/        channel-agents (opener), channel-empty, intent
  src-tauri/                Rust shell; spawns Python sidecar

sidecar/server.py FastAPI HTTP + SSE for the desktop
src/second_brain/
  agent/manager.py    Grok-short router (ask vs dispatch)
  agent/policy.py     Job policy
  memory/             claims, digest, recall, channel emptiness
  graph.py            LangGraph research skill
  agents/             planner, retriever, analyst, verifier, synthesizer
```

---

## Key UI / client files

| File | Role |
|------|------|
| `desktop/src/lib/assistant/channel-agents.ts` | Empty-channel opener + composer placeholder |
| `desktop/src/lib/assistant/channel-empty.ts` | Pure emptiness check |
| `desktop/src/lib/components/app/WorkspaceChatTree.svelte` | Flat channel list |
| `desktop/src/lib/components/app/AgentPane.svelte` | Landing vs thread, `take_turn`, run skills in-session |
| `desktop/src/lib/stores/assistant.svelte.ts` | One session per `projectPath` (`ensureChannelSession`) |

---

## How to run

```bash
source .venv/bin/activate
cd desktop && npm install && npm run tauri dev
```

**Tests (fast):**

```bash
.venv/bin/python -m pytest tests/test_manager.py tests/test_channel_empty.py -q
cd desktop && npx vitest run src/lib/assistant/
```

---

## Intentional non-goals

- Per-agent sidebar members or hire flows
- Multi-speaker group chat / `@` routing (Manager routes instead)
- Agent DMs outside a channel
- Unbounded custom bots
- Character named “Manager” as a sidebar persona (router is internal speech)
