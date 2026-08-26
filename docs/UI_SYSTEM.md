# Nous UI System — Product References & Craft Rules

Nous’s visual language is **not invented from scratch**. Each major surface has a primary product reference. When in doubt, **match the reference’s information hierarchy**, not a generic dashboard.

**Shell layout north star: Chat-first Agent OS** — left sidebar (Projects → Chats), **center chat transcript** (boxed user prompts, unbubbled ask/agent markdown, muted status lines), optional right **Details** drawer (plan / critique / summary — closed by default), bottom composer. Pipeline roles stay under the hood; progress is text, not a graph stepper.

**Shipped default:** Messenger shell — `AppShell.svelte` keeps `ChatHome.svelte` on screen. The **Manager** speaks first on a new chat (static opener, no model call). It creates the vault topic when it dispatches. The sidebar is a **chat list**, not a topic tree. Watch, Memory, Library, and Settings open as **plugin sheets**. Reports stay unbubbled. LangGraph specialists still run under the hood; Details names them.

**IA:** Chat/session = one Manager working a task. The Manager names and creates the vault folder (topic + shared memory) from what you say. Follow-ups in a chat update that agent’s memory and roll up into project memory.

---

## Reference map (authoritative)

| Priority | Product | Use for | Primary surfaces in Nous |
|----------|---------|---------|---------------------------|
| **1 — Study most** | **[Cursor](https://cursor.com/)** + chat threads | Agent communication | Agent chat transcript, status lines, composer |
| **2** | **[Elicit](https://elicit.com/)** | Research-grade synthesis | Final report, key findings, sources, citations, gaps |
| **3** | **[Linear](https://linear.app/)** | Overall polish & SpaceX/xAI feel | Shell, density, type, cards, status, loading, ⌘K |
| **4** | **[Khoj](https://github.com/khoj-ai/khoj)** + **Obsidian** | Personal KB + AI | Vault, search, **note graph**, hybrid personal/web framing |
| **5** | **[LangGraph Studio](https://www.langchain.com/blog/langgraph-studio-the-first-agent-ide)** | Research *skill* (not chrome) | Plan interrupt, node identity in status copy, critique history in Details |

**Rule:** Chat wins on Agent layout. Linear wins on **chrome, type, spacing, motion**. Elicit wins on **report structure**. Studio informs *what* agents do, not a primary graph canvas. **Keep** `GraphView` for vault notes; do **not** use `AgentGraph` (pipeline stepper) on the Agent page.

---

## 1. Chat-first Agent surface (hero)

**Why:** Communicating with agents and reading progress as prose is clearer than a dashboard of steppers, bars, and dumps.

### Patterns to ship

| Concept | Nous implementation |
|---------|---------------------|
| **Project → Chat** | Sidebar groups chats under vault projects |
| **Transcript** | Boxed user prompt · unbubbled ask/agent markdown (Cursor/Hermes) |
| **Status lines** | One readable sentence per stage (`status-copy.ts`) — collapsed when done |
| **Details drawer** | Optional: plan query bullets, critique verdict, paths |
| **Plan review** | In-thread interrupt card before retrieval |
| **Report** | Inline lead (summary + findings); longer sections collapsed; full Elicit column from **View report** |
| **Note graph** | Separate Graph mode (`GraphView` + `vault-graph`) |

### Layout

```
┌────────────┬──────────────────────────────┬─────────────────┐
│  Projects  │  Chat transcript             │  Details        │
│  · Chats   │  boxed user · unbubbled md   │  (optional)     │
├────────────┴──────────────────────────────┴─────────────────┤
│  Composer (Goal · Research · Ask)                           │
└─────────────────────────────────────────────────────────────┘
```

### Explicitly avoid

- Pipeline stepper / progress bars as primary chrome (`AgentGraph`)
- Chip dumps for confidence / memory / pass counts in the center stage
- Pasting full plan text or source lists into the transcript
- Always-open inspector that crowds the chat

**Sources:** Cursor agent UX, Linear density, Elicit reports.

---

## 2. Elicit → Synthesis / Report view

**Why:** Research output that feels **evidence-based**, not a chat bubble.

### Patterns to copy

| Elicit concept | Nous report UI |
|----------------|----------------|
| Structured research brief | Sections: Executive Summary · Key Findings · Detailed Analysis · Identified Gaps · Sources |
| **Key findings** first | Scannable bullets or numbered findings above long prose |
| **Sources as first-class** | Table or dense list: origin (Personal / Web / arXiv), title, page/url, chip |
| **Sentence-level citations** | Inline `[n]` → hover shows source; click opens it (excerpt jump later) |
| Customize inclusion | Toggle advanced: show plan, retrieval log, critique history (not dumped into body) |
| Evidence over eloquence | Prefer “claim + citation” over marketing tone |

### Report chrome

- **View report** opens a **reading column** (max-width ~42–48rem) with TOC, sources, and save/export
- In the chat thread: summary + key findings as unbubbled prose; longer sections behind **More analysis**; no TOC or sources table; `[n]` opens the source
- Sticky mini-TOC for sections (reading column only)
- Actions: Save to vault · Export MD · (later PDF)
- Gaps/contradictions use **warning** semantic, not red panic

**Sources:** [elicit.com](https://elicit.com/), systematic review / reports product pages.

---

## 3. Linear → Overall polish (SpaceX/xAI aesthetic)

**Why:** Highest-quality dark product UI; closest industrial “operator tool” feel.

### Patterns to copy

| Linear concept | Nous rule |
|----------------|-----------|
| Near-black canvas | Ladder: canvas → elevated → surface (see tokens) |
| **Single chromatic accent** | Lavender-blue brand/live (`--accent-live`); no rainbow UI |
| Subtle status colors | Soft green / amber / red washes — never neon traffic lights |
| Hairline borders | 1px `--border` / `--border-subtle`; almost no shadows |
| Dense but calm | Tight vertical rhythm; align icons/labels like Linear sidebar |
| Typography | Small UI type (13–14px), clear hierarchy, mono for IDs/shortcuts |
| Cards | Flat surfaces, slight elevation via background step, not drop shadow |
| Loading | Skeletons / subtle progress — no spinners as primary language |
| Micro-interactions | ≤150ms; opacity and border, not bounce |
| Command palette | ⌘K as console (already present) |

### Linear-inspired surface ladder

| Step | Role | Approx |
|------|------|--------|
| Canvas | App background | `#010102`–`#0a0a0a` |
| Elevated | Header, panels | `#0f0f10` |
| Surface | Cards, lists | `#141516` |
| Hover | List row hover | `#1c1c1e` |
| Hairline | Borders | `#23252a` |

**Sources:** [Linear UI redesign](https://linear.app/blog/how-we-redesigned-the-linear-ui), Linear product dark theme.

### Settings dialog

Cursor-style **four-page** sheet (`AppSheet` settings-only: `min(860px, 94vw)` + left nav). Ingest/References stay the narrow 560px sheet.

| Page | Contents |
|------|----------|
| **Models** | Connected / Available providers + connect/config modal; default model dropdown (same list as the composer); Fast / Fallback under Advanced |
| **Knowledge** | Vault embedding status + re-ingest CTA; auto-add new files; embedding provider/model IDs under Advanced |
| **Connectors** | MCP slot — **Notion first**, opt-in (`ENABLE_MCP`, default off). Internal integration token; read-only REST adapter. Used on **hybrid** research only (not Library-only). Google Drive greyed for later. |
| **Research** | Web / arXiv / Tavily; **max goal passes** on the page; tokens / revisions / top-k under Advanced |

Persist on select or blur. No footer **Save settings** for the common path. Provider connect already saves.

---

## 4. Khoj + Obsidian → Knowledge Base

**Why:** Personal second brain + AI over *your* docs; hybrid personal/web is core to Nous.

### Patterns to copy

| Product | Pattern | Nous |
|---------|---------|------|
| **Obsidian** | File tree, wikilinks, local-first, graph of *notes* | Vault sidebar, TipTap notes, note graph (`force-graph`) |
| **Obsidian** | Focused editor, minimal chrome while writing | DocumentView workbench |
| **Khoj** | Natural-language search over personal vault | Semantic vault search + fuzzy |
| **Khoj** | Personal docs + web together | Hybrid retriever chips: Personal · Web · arXiv |
| **Khoj** | Side-pane AI, not replacing the vault | Knowledge panel + Mission as separate modes |

### KB UI rules

- Knowledge graph = **notes**, never confused with **agent graph**
- Ingest is a first-class drop zone (library), not buried
- Search results show path + excerpt + origin
- Always label source type in retrieval transparency

---

## 5. Cursor → Transparent AI actions (anti-chatbot)

**Why:** Modern technical dark UI; agents feel like tools, not a messaging app.

### Patterns to copy

| Cursor concept | Nous |
|----------------|------|
| User in a box, agent on the canvas | Left-aligned boxed user prompt; unbubbled ask/agent markdown |
| Composer as console | Bottom dock: mode (Research / Query), launch, cancel |
| Show what the agent did | Live tool lines; collapsed disclosure when done |
| Diff / change mindset | Critique panel: before/after iterations (revision timeline) |
| No fluffy empty states | Operator empty: “Ingest docs · set API key · launch research” |
| Keyboard-first | ⌘K, Esc, clear focus rings |

### Explicitly avoid

- Dumping full plans, source lists, or raw logs into the chat transcript
- “Assistant is typing…” without agent identity in status lines
- Hiding multi-agent structure — status lines should name Planner / Retriever / …

---

## Principles (synthesis)

1. **Chat for control** — Project → Chat is how you talk to agents; progress is readable text.
2. **Elicit for output** — reports are structured evidence, not chat.
3. **Linear for craft** — density, accent discipline, calm motion.
4. **Khoj/Obsidian for memory** — vault is the product core; session → project memory hierarchy.
5. **Cursor for agency** — actions and tools are transparent; Details on demand.
6. **Studio for the skill** — LangGraph roles inform status copy and critique, not primary chrome.

---

## Tokens (`desktop/src/app.css`)

Aligned with **Linear ladder** + live status accents.

| Token | Role |
|-------|------|
| `--bg`, `--bg-elevated`, `--surface`, `--pane-bg` | Linear-style surface ladder |
| `--text`, `--text-muted`, `--text-faint` | Hierarchy |
| `--accent` | Primary CTA (cold white on dark) |
| `--accent-live`, `--accent-link` | Brand / focus / running (Linear lavender-blue family) |
| `--success` / `--warning` / `--error` | Subtle status (Linear-like, not neon) |
| `--status-*` | Optional agent status accents |
| `--font-mono` | Status meta, metrics, shortcuts |

---

## Components (`desktop/src/lib/ui/`)

| Component | Primary reference |
|-----------|-------------------|
| Status lines / run blocks | Cursor + chat |
| `LogLine`, `MetricChip` | Cursor |
| `Button`, `Card`, `MissionCard`, `Skeleton` | Linear |
| `SectionHeader`, report layout | Elicit |
| Vault tree / search / note graph | Obsidian + Khoj |

---

## Implementation checklist by phase

### Agent chat (shipped)
- [x] `ChatThread` + `AgentRunBlock` as Agent center
- [x] Cursor-style messages: boxed user prompts, unbubbled ask/agent markdown
- [x] Readable status lines (`status-copy.ts`), collapsed when the run is done
- [x] Inline report in the thread; full reading view from **View report**
- [x] Optional Details drawer (plan / critique / project memory peek)
- [x] Plan Review as in-thread interrupt
- [x] Session → project memory hierarchy

### Report — Elicit
- [x] Sectioned report reading view
- [ ] Sources table with origin chips (ongoing)
- [x] Citation click-to-open (hover title); excerpt jump later
- [ ] Findings-first scanning

### Shell — Linear
- [x] Token ladder + rail/header polish (started)
- [x] Settings four-page dialog (Models · Knowledge · Connectors · Research)
- [ ] Consistent list density, hairlines, loading skeletons app-wide

### Knowledge — Khoj/Obsidian
- [ ] Library drop-zone + search results density
- [ ] Clear Personal/Web/arXiv labeling
- [x] Note graph (`GraphView`) kept separate from agent progress chrome

### Composer — Cursor
- [x] Composer dock, cancel, mode switch (Goal / Research / Ask)
- [ ] Further transparent step polish

---

## Do / Don’t

| Do | Don’t |
|----|--------|
| Study Studio demos before coding the graph | Invent a novel graph UX uninformed by Studio |
| Make reports look like Elicit briefs | Put the whole report only inside a chat bubble |
| Match Linear density and accent restraint | Neon multi-color dashboards |
| Keep vault local-first like Obsidian | Hide personal memory behind pure web chat |
| Show agent actions like Cursor Composer | Pretend it’s a single chatbot |

---

## Related

- Architecture: [`docs/SEMESTER2_ARCHITECTURE.md`](SEMESTER2_ARCHITECTURE.md)
- Code tokens: `desktop/src/app.css`
- Components: `desktop/src/lib/ui/*`
