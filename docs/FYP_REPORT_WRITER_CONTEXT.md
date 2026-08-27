# FYP Report Writer Context — Nous (CSAI)

**Purpose:** Single source of truth for an AI writer completing the APU School of Computing FYP final report.  
**Programme track:** **CSAI** (B.Sc. Hons Computer Science — Artificial Intelligence) — **NOT CSDA**.  
**Intake / class:** APD3F2601CSAI  
**Guideline source:** *New FYP Structure Guidelines — updated 7 Oct 2024* (SOC & SOT, V1-AUGUST2023).  
**Student:** Wong Yan Hao (TP068819)  
**Supervisor:** Mr. Amad Arshad  
**Second marker:** Ms. Mary Ting  
**Approved title source:** Student Proposed (submitted 2026-02-09; status **APPROVED**)  
**Investigation Report:** `Wong Yan Hao-TP068819-APD3F2601CSAI-IR.docx` (Semester 1)  
**Product name (in-app only):** Nous — **do not put the product name in the official FYP title**.  
**Python package / monorepo:** `fyp-second-brain` / `second_brain`  
**Last synced:** August 2026 (codebase + IR + approved proposal)

---

## How the AI writer must use this file

1. Follow the **CSAI / CS** chapter outlines below. **Never** use CSDA chapter outlines (CRISP-DM, model ABC/XYZ, dataset preprocessing as Chapter 4 main path, etc.).
2. Treat **LOCKED (IR/proposal)** fields as immutable for cover page, aim, objectives wording, SDG, supervisors, and survey facts. Treat **Sem 2 product facts** as what was actually built. Where they diverge, use §0.7 *IR → Sem 2 evolution* — do **not** invent delivery of IR promises that were deferred or changed.
3. Treat **Placeholders** as items still needed for final submission (Turnitin, remaining log sheets, completed UAT scores, full eval runs).
4. Write in formal academic English, APA citations, past/present tense consistent with a completed system.
5. Map every claim about “what the system does” to the mental model in §0. Do not invent sidebar “agents,” global chat memory, or CSDA-style ML training pipelines.
6. Prefer journals/books/conference papers over random websites in References. Reuse IR citations where valid (Alansari & Luqman, 2025; Chen et al., 2025; Renze, 2024; Regona et al., 2024; etc.).
7. Abstract ≤ **200 words**; official title is locked (13 words). No product/system brand name in the title.
8. Each of: Cover, Acknowledgement, Abstract, ToC, List of Figures, List of Tables must start on a **new page**.
9. Chapter 6 guideline numbering says “4.1/4.2/4.3” — use **6.1 / 6.2 / 6.3** in the real report.

---

## 0. Product one-pager (memorise)

### 0.1 One-liner

Local-first **second brain**: each **workspace** is a lifelong topic folder with its own vault memory. The user talks in that workspace. An internal **Manager** routes Teach / Ask / Research / Watch as jobs in the same thread. Research and Watch can **write back** into that topic’s memory.

**Tagline:** Research that remembers *you*.

**Examiner / viva line:** Flagship chat AIs are general assistants. Nous is a local-first mind for the user’s knowledge: knowledge they own, multi-agent research that uses it, and results that update it over time.

### 0.2 Mental model (do not invert)

| Concept | Meaning |
|--------|---------|
| **Workspace** | Topic vault folder (e.g. Coffee, FYP, DLM) with isolated memory |
| **Chat** | One Manager thread bound to that workspace |
| **Manager** | Invisible router (`take_turn`) — not a UI character or sidebar member |
| **Memory** | Durable **claims** for that workspace — not a global chat history |
| **Skills / jobs** | `file` (Teach), `answer` (Ask), `research`, `watch`, `refuse`, topic ops |

**Forbidden framings in the report:**

- “ChatGPT with a sidebar”
- Hiring / adding agents; Planner/Retriever/Verifier as people in the UI
- Nesting Teach/Research/Watch as separate chats under a workspace
- Global user memory store across all topics
- Treating web search alone as the differentiator

**Correct differentiator:** lifelong **local** topic memory + multi-agent research with **self-critique** + **hybrid personal-first** retrieval + **write-back**.

### 0.3 LOCKED official FYP title (APPROVED — do not change)

**Developing a Graph-Based Multi-Agent Framework for Autonomous Research and Lifelong Personal Knowledge Management**

- Status: **APPROVED** (Student Proposed; submitted 2026-02-09)  
- Word count: 13 (≤15). Action verb: *Developing*. No product/brand name.  
- Proposal registration keywords (portal): Artificial intelligence, Deep Learning — **prefer IR abstract keywords in the report abstract** (richer and more accurate).

### 0.4 LOCKED aim (Ch 1.3 — from IR; keep this sentence)

To develop a graph-based multi-agent system of autonomous research and lifelong personal knowledge management that is a privacy preserving, local-first Second Brain of knowledge workers and students.

*(Proposal portal wording is close: “To design and develop a multi-agent artificial intelligence system that autonomously conducts research tasks and serves as a persistent personal knowledge operating system to enhance knowledge work efficiency and reduce hallucinations in generated outputs.” Prefer the **IR aim** above for Chapter 1 consistency with the Investigation Report.)*

### 0.5 LOCKED objectives (Ch 1.4 — from IR; four “To…” items)

Use these as the official Chapter 1 objectives (trace to RTM / survey). Sem 2 delivery notes in parentheses are for the writer’s accuracy — **do not replace the objective text** unless the student explicitly revises with supervisor approval:

1. To create and deploy a LangGraph-based multi-agent architecture that uses persistent vector database memory, making it possible to retain personal knowledge throughout life and to be aware of context across sessions. *(Delivered: Chroma + workspace claim memory + Manager recall/write-back.)*  
2. To incorporate real-time hybrid retrieval systems that smoothly integrate the personal documents of the user, web search APIs (Tavily) and scholarly archives (arXiv, Semantic Scholar) into a single retrieval-augmented generation (RAG) pipeline. *(Delivered: personal + Tavily + arXiv. Semantic Scholar was planned in IR; treat as partial/deferred unless student confirms integration — see §0.7.)*  
3. To test system performance in terms of a curated benchmark (52 research queries) of task completion rate, rate of hallucination, and citation accuracy against strong single-LLM baselines (Claude 3.5 Sonnet and Grok-3). *(Sem 2 corpus evolved: 20-query DLM suite replaced the retired Java 52-set — explain honestly in Ch5; baselines remain Claude/Grok chat.)*  
4. To roll out the solution as a cross-platform desktop application with Tauri 2.0, which offers native performance, local-first privacy, and optional Bring-Your-Own-Key cloud LLM access. *(Delivered: Tauri 2 + Svelte 5 + Python sidecar; BYOK / Groq / Ollama / OpenRouter.)*

### 0.6 LOCKED SDG + keywords (from IR / proposal)

**Primary SDG (proposal + IR):** **SDG 9** — Industry, Innovation and Infrastructure  
*Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation.*  
Map to Targets **9.5** (scientific research / technological capabilities) and **9.b** (local technology development) as in the IR.

Do **not** make SDG 4 the primary mapping. Optional secondary mention of education/lifelong learning is fine only if clearly secondary to SDG 9.

**IR abstract keywords (use these — max 6):**  
Multi-Agent Frameworks; Autonomous Research; Personal Knowledge Management; Retrieval-Augmented Generation; LangGraph; Second Brain

### 0.7 IR → Sem 2 evolution (writer must reconcile, not hide)

| IR / proposal promise | Sem 2 actual product |
|----------------------|----------------------|
| “Second Brain” / PKOS framing | Keep; in-app name **Nous**; UX uses **workspaces** (topic folders), not “channels” |
| 52-query Java/lecture-style benchmark | Retired; **20-query DLM vault** suite (`evaluation/benchmarks.json`) |
| Ollama as default free local LLM | Still supported; demos often use **Groq** / cloud BYOK; embeddings default **fastembed** |
| Semantic Scholar | Not a first-class tool in core hybrid path; **arXiv + Tavily** are |
| MCP toolkit (Notion, Drive, etc.) | **Optional** Notion MCP-shaped adapter (`ENABLE_MCP`, off by default) |
| Cloud-hosted deployment out of scope | Vault remains local-first; **optional** Auth + Cloud Watch for identity/briefs only |
| Agents as research pipeline | Same five nodes **inside Research**; user-facing jobs via **Manager**: Teach / Ask / Research / Watch |
| Self-critique / Verifier | Implemented (grounding + LLM verifier + revision loop) |
| Survey n=62 (April 2026) | LOCKED for Ch3; Sem 2 adds UAT (target 5–8) |

---

## 1. Front matter checklist (guidelines)

| Item | Writer instructions |
|------|---------------------|
| **Cover page** | Use APU template. Dual degree → APU + DMU logos; non-dual → APU logo only (right). No header/footer on cover. **Title = locked §0.3.** Student: Wong Yan Hao / TP068819 / APD3F2601CSAI. |
| **Declaration of Thesis Confidentiality** | Student inserts official form from FYP manager folder. |
| **Library form** | Student inserts official form. |
| **Acknowledgement** | One page. Thank **Mr. Amad Arshad** (supervisor), **Ms. Mary Ting** (second marker), April 2026 survey participants (n=62), APU, family/friends. IR acknowledgement can be adapted for the final report. |
| **Abstract** | One paragraph, ≤200 words: purpose, problem, methods, results/conclusion, significance, **SDG 9**, then IR keywords (§0.6). Evolve IR abstract from future tense to completed-system tense; update eval numbers to Sem 2 evidence. |
| **Table of Contents** | Mirror chapters below. |
| **List of Figures / Tables** | Auto from report; each on new page. |

---

## 2. CHAPTER 1 — INTRODUCTION (CSAI)

### Outline (must follow)

1.1 Introduction  
1.2 Problem Background  
1.3 Project Aim  
1.4 Objectives  
1.5 Scope  
1.6 Potential Benefit  
1.7 Overview of the FYP Documentation  
1.8 Project Plan  

### Facts for 1.2 Problem Background (align with IR + proposal)

Lead with IR themes (cite IR sources where possible):

1. Standalone LLMs are largely **stateless**: hallucinate citations/facts, lose long-horizon context, need constant supervision (Alansari & Luqman, 2025; Singh et al., 2025).  
2. Knowledge workers spend substantial weekly time on literature review / verification; a large fraction is spent fixing AI output (Chen et al., 2025 — as cited in IR).  
3. Tools like ChatGPT / Claude / Grok do not seamlessly combine **local personal documents** with **real-time web/academic** sources in a privacy-preserving way.  
4. Note apps and basic RAG lack autonomous planning, self-critique loops, and lifelong write-back.  
5. **Survey evidence (n=62, April 2026):** top difficulties — summarising long papers **43.5%**; combining personal files/notes with AI **38.7%**; **79%** “Very Willing” to adopt a system that addresses these; Self-Check mean **4.52**; Unified Search highly valued; **80.6%** prefer hybrid or fully local deployment.  
6. Gap links to **SDG 9** Targets 9.5 and 9.b (IR).

Also weave Sem 2 product angles: workspace isolation; files ≠ memory until Teach; refuse-on-thin-memory.

### Scope (1.5) — IR baseline + Sem 2 delivery

**In scope (IR + delivered):**

- LangGraph multi-agent workflow: Planner, Hybrid Retriever, Document Analyst, Verifier/Self-Critic, Report Synthesizer  
- Persistent local vector DB (**Chroma**) + personal document ingest (PDF/TXT/MD)  
- Hybrid retrieval: personal vault + **Tavily** web + **arXiv**  
- Self-critique / revision loops; cited reports with gaps  
- **Tauri 2.0** desktop + **Python** FastAPI sidecar; BYOK / local (Ollama) + cloud LLMs  
- Optional MCP-shaped connectors (Notion adapter present; default off)  
- Sem 2 UX: **workspaces**, Manager jobs (Teach / Ask / Research / Watch), claim memory write-back  

**Out of scope (IR — keep unless supervisor agreed otherwise):**

- Full multi-user collaborative cloud SaaS as the primary product  
- Fine-tuning foundation models  
- Multimodal figure/table/image understanding inside PDFs (future)  

**Constraints:** local hardware for Ollama; user-supplied API keys for cloud models; optional Auth/Cloud Watch does **not** move the vault off-device by default.

### Potential benefits (1.6)

**Tangible (IR + product):** architecture + Chroma pipeline + desktop app; reduced literature-review friction (IR predicted 40–60% time reduction — treat as *projected* unless UAT measures it); cited reports; claim write-back; Watch briefs.  
**Intangible (IR):** design patterns for local-first agentic AI; hallucination mitigation via self-critique; inclusive innovation / SDG 9.  
**Target users (proposal + IR):** UG/PG students; researchers/academics; knowledge professionals (analysts, consultants, policy); institutions wanting low-cost local + scalable cloud BYOK.

### Project plan (1.8)

**IR methodology:** Agile Scrum-style **two-week sprints**, ~10 sprints across two semesters; student as developer/Scrum Master; supervisor as Product Owner.  
Map to delivery phases:

| Phase | Goal |
|-------|------|
| 0 | Setup, ingestion, Chroma |
| 1 | Personal RAG (Ask) |
| 2 | LangGraph multi-agent + verifier |
| 3 | Hybrid retrieval (personal + web + arXiv) |
| 4 | Tauri desktop + sidecar |
| 5 | Evaluation + packaging |
| Sem 2 | Workspace/Manager UX, durable claims, write-back, Watch, optional auth/cloud-watch |

Reuse IR Table 1 / Gantt (Appendix E) and Sem 2 extension.

### Documentation overview (1.7)

Ch2 literature → Ch3 methodology (Agile + survey n=62 + RTM) → Ch4 design & implementation → Ch5 unit/UAT/benchmark results → Ch6 conclusion.

---

## 3. CHAPTER 2 — LITERATURE REVIEW (CSAI)

### Outline

2.1 Introduction  
2.2 Domain Research (general → specific; critical review per sub-topic)  
2.3 Similar Works (characteristics, strengths/weaknesses, conclusion)  
2.4 Technical Research (HW/SW justification; OS; optional IDE/libs/DB/server)  
2.5 Summary  

### 2.2 Domain topics the writer should cover

Reuse and extend IR Chapter 2 structure (critical, not brochure-style):

1. **Agentic AI & graph-based multi-agent orchestration** — LangGraph vs CrewAI vs AutoGen (IR §§2.2.1).  
2. **RAG & persistent memory** — Chroma vs FAISS; lifelong local memory (IR §§2.2.2).  
3. **Second-Brain / PKM architectures** — Forte/Khoj framing; privacy vs Notion AI (IR §§2.2.3).  
4. **Self-critique / reflection** for hallucination mitigation (Renze, 2024; Park et al., 2026 as in IR).  
5. **Hybrid retrieval** — personal + web + academic.  
6. **Evaluation of grounded assistants** — completion, hallucination, citation accuracy; Sem 2 gold-hit / honest-gap / invented-fact.

### 2.3 Similar works (IR Table 2 + Sem 2)

| System / class | Strengths | Weaknesses vs this project |
|----------------|-----------|----------------------------|
| LangGraph (library) | Stateful graph, critique loops | Not a complete local desktop PKM product by itself |
| CrewAI | Easy role teams | Weak lifelong local shared state; less fit for privacy PKM |
| Microsoft AutoGen | Flexible multi-agent chat | Config overhead; harder rigorous critique |
| LlamaIndex Agents | Strong RAG indexing | Weaker full plan→verify→synthesise graph |
| Khoj | Self-hostable Second Brain | Limited autonomous research + citation-level critique |
| ChatGPT / Claude / Grok | Strong general reasoning | No owned local topic vault / write-back by default |
| Notion AI | Workspace integration | Cloud-centric |

**Conclusion:** Gap = local-first lifelong memory + graph multi-agent research with self-critique + hybrid personal-first retrieval + desktop delivery (+ Sem 2 workspace claim write-back).

### 2.4 Technical research — stack (IR + Sem 2)

| Layer | Choice | Justification |
|-------|--------|----------------|
| Language | Python 3.12 | AI ecosystem / LangGraph |
| IDE | VS Code / Cursor (IR) | Debugging, Git, AI workflows |
| Orchestration | LangGraph | Deterministic routing, verifier loops |
| Vectors | Chroma (local) | Lifelong personal KB; metadata |
| Embeddings | fastembed default; optional Ollama | Local-friendly; Ollama not required for embeds |
| LLM | Ollama (local) + BYOK cloud (Groq/OpenRouter/etc.) | Matches hybrid/local survey preference |
| Web | Tavily | Tool search API |
| Academic | arXiv (Semantic Scholar deferred/partial) | IR planned both; implement honestly |
| Tools / MCP | Optional Notion adapter | Survey valued Notion / Drive integrations |
| Desktop | Tauri 2 + Svelte 5 + Python sidecar | Cross-platform, local files, small footprint |
| Auth / Cloud Watch | Optional | Identity + morning briefs; vault stays local |
| OS | Windows / macOS / Linux (Tauri); primary demo macOS | IR cross-platform claim |
| VCS | Git / GitHub | IR |

**Hardware:** consumer laptop; Docker only if demonstrating auth/cloud-watch.

---

## 4. CHAPTER 3 — METHODOLOGY (CSAI / CS — not CSDA)

### Outline (mandatory for CSAI)

3.1 Introduction  
3.2 System Development Methodology  
3.3 Data Gathering Design  
3.4 Analysis  
3.5 Summary  

**Do not** write CRISP-DM / KDD / SEMMA as the main Ch3 methodology (that is CSDA).

### 3.2 LOCKED methodology framing (from IR)

**Choice:** **Agile** with Scrum-inspired **two-week sprints** (not Waterfall, not RUP, not CRISP-DM).

**Justification (IR):** multi-agent / LLM ecosystem changes rapidly; need iterative refinement of agent workflows and survey-driven backlog; single-developer project (student = developer + Scrum Master; supervisor = Product Owner).

Describe process **within** sprints (plan → develop → supervisor review → retrospective → shippable increment), plus CLI-first validation before Tauri polish.

Map IR Table 3 sprint plan + Sem 2 increments (workspace Manager, claims, Watch, eval/UAT).

### 3.3 Data gathering design — LOCKED survey (IR)

**Primary technique:** structured questionnaire (Tally.so), four sections:

- A — Demographics & background  
- B — Current challenges & tool usage  
- C — Proposed system features (5-point Likert)  
- D — Adoption & benefits / integrations  

**Sampling:** purposive + convenience; LinkedIn, university groups, Reddit, X, academic networks; **17–19 April 2026**.  
**Valid responses:** **n = 62** (after consent + core feature questions).  
**Pilot:** 5 target users before full deployment.  
**Ethics:** voluntary, anonymous, informed consent; APU student research ethics (Appendix B forms already in IR).  
**Demographics (IR):** 54.8% age 25–34; PG students 32.3%; industry 32.3%; academic/research staff 25.8%; Computing/AI/Engineering/Business ~65%.

**Sem 2 add-on:** UAT observation sessions (Coffee/Plants packs), target **5–8** participants — minimum **3** testers per guidelines.

**Benchmark evaluation** (not a survey): IR planned 52 queries; Sem 2 uses 20-query DLM suite + Claude/Grok baselines + optional ablation.

### 3.4 Analysis → LOCKED survey findings + RTM

**Key stats the writer must use:**

| Finding | Value |
|---------|--------|
| Summarising long papers (top difficulty) | 43.5% |
| Combining personal files/notes with AI | 38.7% |
| Self-Check / self-critique usefulness (mean) | 4.52 (87% rated 4 or 5) |
| Unified Search highly valued | mean ~4.31 (IR) |
| Deployment: Hybrid | 50% |
| Deployment: Fully local | 30.6% |
| Deployment: Fully web-hosted | 19.4% |
| Very Willing to adopt | 79% |
| Valued integrations | Google Drive/OneDrive (39), Notion (38) — counts from IR |

**Cross-tabs (IR):** PG students rated Self-Check higher (4.65) than industry (4.38); industry rated Unified Search slightly higher.

**Requirements Traceability Matrix:** reuse/extend IR Table 4 — map survey needs → FRs → objectives 1–4.

**Sem 2 FR refinements (add to RTM, do not erase IR):**

- FR1 Create/open topic **workspaces** with isolated memory  
- FR2 Teach → claims (`origin=dump`)  
- FR3 Ask from settled claims; refuse if thin  
- FR4 Research hybrid report + write-back  
- FR5 Watch briefs (`origin=watch`)  
- FR6 Index-only ingest  
- FR7 SSE / status lines  
- FR8 Settings / BYOK  
- FR9 Optional Account + cloud briefs  

**Survey limitations (IR):** n=62; Computing/AI overrepresentation; stated preference ≠ observed behaviour → motivate Sem 2 UAT.

---

## 5. CHAPTER 4 — DESIGN AND IMPLEMENTATION (CSAI / CS)

### Outline

4.1 Introduction  
4.2 Design (architecture, UML as appropriate)  
4.3 Database Design (optional — include what exists)  
4.4 Interface Design  
4.5 Implementation (screenshots + discussion; ML/analysis steps if any)  
4.6 Sample codes  
4.7 Summary  

### 4.2 Architecture (facts)

```
┌─────────────────────────────────────────┐
│  Desktop: Tauri 2 + Svelte 5            │
│  Sidebar workspaces · Chat (AgentPane)    │
│  Memory · Watch · Settings · ⌘K         │
└──────────────────┬──────────────────────┘
                   │ HTTP + SSE
┌──────────────────▼──────────────────────┐
│  Sidecar: FastAPI :8765                 │
│  /api/query · /api/chat · /api/research │
│  /api/research/stream · ingest · vault  │
│  Manager take_turn · Watch scheduler    │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  second_brain                           │
│  Manager → jobs                         │
│  LangGraph: planner → retriever →       │
│    analyst ⇄ verifier → synthesizer     │
│  Memory: claims, digest, recall         │
│  Chroma + tools (Tavily, arXiv)         │
└─────────────────────────────────────────┘
         optional
┌──────────────────┐  ┌───────────────────┐
│ auth/ Better Auth│  │ cloud-watch/      │
│ Email OTP        │  │ Hosted briefs+BYOK│
└──────────────────┘  └───────────────────┘
```

**Research graph topology:**

```
START → planner → retriever → analyst → verifier
                         ↑_______| (REVISE if not approved
                                   and revision_count < MAX_REVISIONS)
verifier → synthesizer → END
```

Default `MAX_REVISIONS` = 1 (configurable). Forced approve path after max revisions; research claims may be contested if not cleanly approved.

**Manager jobs:**

| Job | Behaviour |
|-----|-----------|
| `file` | Digest → claims `origin=dump` |
| `answer` | Workspace RAG / recall; no durable write |
| `research` | Full graph; persist report + claims if policy allows |
| `watch` | Create/run standing brief |
| `refuse` | Thin/off-topic — do not invent |
| retarget / merge / split | Topic folder operations |

Dispatch-first; at most **two** clarifying asks when vague.

### 4.3 Database / persistence design

Not a classic SQL app for the vault. Document as **persistence design**:

1. **Filesystem vault** under `data/documents/{topic}/`  
   - `memory/claims/{slug}.md` — frontmatter claim schema  
   - `memory/project.md`, `project-log.md`, learnings, agent session memory  
   - `research/`, `briefs/`, `watches/`, notes  
2. **Chroma** local vector DB (`data/chroma/`) — chunks for retrieval  
3. **Optional Postgres** (auth service only) — sessions/devices, not vault content  
4. **Cloud Watch store** — watches/briefs + encrypted BYOK keys (not personal markdown vault)

**Claim schema (frontmatter):** `id`, `claim`, `status` (`settled`|`contested`|`superseded`), `origin` (`dump`|`watch`|`research`), `source_path`, `source_quote`, `content_hash`, dates, `supersedes`, `expires` (watch only).

**Skip-list (not Teach dumps):** `memory/**`, `briefs/**`, `watches/**`, `research/**`, `instruction.md`.

### Diagrams the writer should produce (suggest)

- System architecture (above)  
- Use case diagram: Student/KnowledgeWorker × Teach, Ask, Research, Watch, Ingest, Settings, Account  
- Activity / sequence: User message → Manager → Research SSE → write-back  
- Component diagram: desktop / sidecar / agents / memory / tools  
- Optional ER for auth Postgres devices/sessions only  

### 4.4 Interface design

Surfaces:

| Surface | Role |
|---------|------|
| Sidebar | New workspace; flat `#Name` list; Memory nav; Watch nav |
| Chat / AgentPane | Landing vs thread; composer “Message this workspace…”; job chips |
| Remembered card | Teach confirmation |
| Research status lines | Planner → Retriever → Analyst → Verifier → Synthesizer (not sidebar people) |
| Report viewer | Citations `[n]`, gaps, save/open report |
| Memory home | Browse claims / knowledge graph for topic |
| Watch UI | Focus editor, run, history |
| Document peek | Read notes beside chat |
| Settings | Models, connectors, knowledge, Account |
| Command palette ⌘K | e.g. Remember topic notes |

UI references used in product thinking: LangGraph Studio (transparency), Elicit (report), Linear (polish), Khoj/Obsidian (KB), Cursor (anti-chatbot transparency).

### 4.5 Implementation subsections (screenshot + discuss)

Suggested structure for 4.5.x:

1. Workspace sidebar and new workspace  
2. Empty workspace / Chat landing  
3. Teach → Remembered  
4. Ask with source chips / refuse  
5. Research run with status lines and report  
6. Memory / claims view  
7. Watch brief  
8. Settings (models, Tavily)  
9. Account OTP (optional)  
10. Ingest / Library import  

For each: what it does, which requirement it satisfies, how it maps to Manager job or graph node.

**AI pipeline “analysis steps” (allowed under Ch4.5 note for ML/AI systems):**

1. Ingest / chunk / embed → Chroma  
2. Teach digest → claims  
3. Recall snapshot for Ask/Research  
4. Planner tagged queries `[personal]|[web]|[arxiv]`  
5. Hybrid retrieve + analyst draft  
6. Grounding + verifier critique / revise  
7. Synthesizer report + bibliography  
8. Persist learning/claims if policy says so  

### 4.6 Sample code pointers (for Appendix F + Ch4.6)

| Program / module | Path | Role |
|------------------|------|------|
| Research graph | `src/second_brain/graph.py` | `build_graph`, `route_after_verifier`, streaming wrappers |
| Graph state | `src/second_brain/state.py` | `GraphState` TypedDict |
| Manager | `src/second_brain/agent/manager.py` | `take_turn` |
| Claims | `src/second_brain/memory/claims.py` | Durable memory |
| Hybrid retriever | `src/second_brain/agents/hybrid_retriever.py` | Source routing |
| Verifier / grounding | `agents/verifier.py`, `agents/grounding.py` | Self-critique |
| Sidecar | `sidecar/server.py` | HTTP/SSE API |
| Desktop API client | `desktop/src/lib/api.ts` | UI ↔ sidecar |
| Chat UI | `desktop/src/lib/components/app/AgentPane.svelte` | In-session jobs |

Include 1–2 short excerpts with explanation (not entire files).

### Monorepo map

```
fyp-second-brain/
├── src/second_brain/     # Core AI package
├── sidecar/              # FastAPI
├── desktop/              # Tauri + Svelte
├── auth/                 # Optional Better Auth
├── cloud-watch/          # Optional hosted Watch
├── evaluation/           # Benchmarks, UAT, demo packs, results
├── scripts/              # CLI ingest/query/research/eval
├── tests/                # ~30+ pytest modules (~4.8k+ lines)
└── data/documents/       # User vault (local)
```

---

## 6. CHAPTER 5 — RESULTS AND DISCUSSIONS (CSAI / CS — not CSDA)

### Outline

5.1 Introduction  
5.2 Test Plan  
  5.2.1 Unit Testing  
  5.2.2 User Acceptance Testing (UAT)  
5.3 Testing Results and Discussion  
  5.3.1 Unit Testing  
  5.3.2 User Acceptance Testing  
5.4 Summary  

**Guidelines:** Minimum **3** UAT testers (project targets 5–8). Use Likert 1–5 + Yes/No functionality tables as in the PDF samples.

**Do not** structure this as “Evaluation of Model ABC/XYZ” (CSDA).

### 5.2.1 Unit / automated testing — map to pytest

Present as formal test cases (Expected / Actual / Pass|Fail) **and** summarise automated suite:

| Area | Test modules (examples) |
|------|-------------------------|
| Ingestion / retrieval | `test_ingestion.py`, `test_retrieval.py` |
| Agents / graph routing | `test_agents.py`, `test_graph_integration.py`, `test_plan_execute.py` |
| Hybrid / grounding / citations | `test_hybrid.py`, `test_grounding.py`, `test_citations.py` |
| Manager / topics | `test_manager.py`, `test_topic_ops.py`, `test_channel_empty.py` |
| Memory / claims | `test_claim_provenance.py`, `test_digest_link.py`, `test_topic_memory.py`, `test_agent_memory.py` |
| Watch / cloud | `test_watch.py`, `test_watch_api.py`, `test_cloud_watch.py` |
| Evaluation harness | `test_evaluation.py` |

Example unit-style rows (writer expands):

| TC | Component | Input | Expected | Status |
|----|-----------|-------|----------|--------|
| TC-M1 | Manager | Clear research goal | `job=research` dispatch | Passed |
| TC-M2 | Manager | Empty vault ask | `refuse` or clarify | Passed |
| TC-V1 | Verifier | Bad citation bounds | Revision / fail grounding | Passed |
| TC-C1 | Claims | Watch vs dump collision | Contested sibling, no silent overwrite | Passed |

### 5.2.2 + 5.3.2 UAT

Use `evaluation/uat_questionnaire.md` structure:

- Demographics per tester (Appendix G)  
- UI criteria Likert  
- Functionality Yes/No  
- Tasks: Teach→Ask, Research, parallel chats  
- Aggregate means, discuss themes (trust in sources, clarity of status lines, files≠memory insight)

**Placeholder:** insert real scores when collected. Status as of Aug 2026 docs: **UAT responses pending**.

### AI / research evaluation evidence (fold into 5.3 discussion — still CSAI “results”, not CSDA model chapter)

**IR plan:** curated **52** research queries; metrics = task completion, hallucination rate, citation accuracy; baselines = Claude 3.5 Sonnet and Grok-3; ablation multi-agent vs single-LLM.

**Sem 2 actual suite:** `evaluation/benchmarks.json` v2 — **20 queries** on **DLM** vault (diffusion-LM notes). The Semester 1 Java 52-query set was **retired** because those PDFs are no longer the ingested corpus. Writer must explain this corpus change when discussing Objective 3.

| Category | Mode | Intent |
|----------|------|--------|
| personal_vault (8) | Ask/query | Grounded in notes |
| hybrid (research) | Research graph | Personal + web/arXiv |
| research | Research graph | Multi-step synthesis |
| edge_gaps | Ask/research | Must refuse / not invent |

**Metrics:** success rate, latency, citation rate, gaps section rate, gold-hit rate, honest-gap rate, invented-fact rate; optional self-critique ablation ON/OFF; Claude/Grok chat baselines (no vault).

**Recorded partial results (cite carefully; note incompleteness):**

Ask/query run (`evaluation/results/nous_dlm_query.md`, 2026-08-22):

- 10/10 success (8 personal_vault + 2 edge_gaps in that file’s category split)  
- Gold-hit 100%, honest-gap 100%, invented-fact 0%, citation 80%, avg latency ~25s  

Research run (`evaluation/results/nous_dlm_research.md`, 2026-08-22):

- 7/10 success; 3 failures due to **model_not_found** (`llama-3.3-70b-versatile`) — infrastructure/config issue, discuss as limitation  
- Citation 100%, gaps 100%, gold-hit 86%, invented-fact 14%, avg latency ~214s  

**Status checklist (`evaluation/EVIDENCE.md`):** full 20-run, ablation, baseline CSV, UAT — several **pending**. Writer must not invent completed numbers; use placeholders or run artifacts when student finishes eval.

### How to discuss vs baselines

Argument: general chat without vault may sound fluent but fails personal gold-hits and honest-gap behaviour; Nous is evaluated on **grounding to the user’s notes**, not open-ended eloquence.

---

## 7. CHAPTER 6 — CONCLUSION (use 6.1–6.3)

### Outline

6.1 Critical Evaluation  
6.2 Limitation  
6.3 Recommendation  

### 6.1 Critical evaluation — talking points

- Objectives met: topic memory, multi-agent research, desktop delivery, evaluation harness  
- Contribution: local-first workspace memory + write-back loop vs generic chat  
- Strengths: hybrid personal-first retrieval; verifier/grounding; refuse path; dump protection; transparent stages  

### 6.2 Limitations

- Research latency / LLM API rate limits and model availability (see 404 failures in research eval)  
- Quality depends on upstream LLM; not a trained custom domain model  
- UAT/full benchmark/baseline comparison may still be incomplete at draft time  
- Desktop primarily macOS; cloud Watch needs hosting + auth ops  
- Claim extraction quality bounded by digest prompts  
- Not a full collaborative multi-user vault  

### 6.3 Recommendations / future work

- Complete full 20-query + ablation + Claude/Grok baselines + ≥3–8 UAT  
- Stronger plan-review UX and cancel semantics polish  
- Broader connectors (Notion MCP already flagged optional)  
- PDF/DOCX export; richer knowledge graph UX  
- Mobile companion or improved cloud brief reliability  
- Better eval metrics for contested-claim honesty  

---

## 8. REFERENCES

- APA style  
- Prefer journals, conference papers, books on: multi-agent LLMs, RAG, LangGraph/LangChain technical reports, PKM, HCI for AI assistants, information retrieval  
- Cite arXiv papers carefully (acceptable in CS if formatted APA)  
- Discourage bare website-only citations; tool docs may appear sparingly with justification  

**Placeholder:** student/IR bibliography — writer should not fabricate DOIs.

---

## 9. APPENDICES (guidelines structure)

| Appendix | Content | Owner |
|----------|---------|--------|
| **A** | PPF title registration screenshots (all pages) | Student |
| **B** | Ethics forms (Fast/Full track) | Student |
| **C** | Log sheets — **6** meetings (3/semester incl. IR) | Student |
| **D** | A3 colour poster (APU logo, title, name, TP, programme, supervisor & second marker titles, intro/objectives/problem/methodology/screenshots/conclusion) | Student + designer |
| **E** | Gantt chart (IR + FYP) | Student |
| **F** | Sample code implementation | From §4.6 paths |
| **G** | Respondent demographic profile (survey/interview + system testers; pseudonyms OK) | Student |
| **H** | Turnitin first 2 pages; similarity ≤ **20%** | Student |

---

## 10. Feature catalogue (for accurate wording)

### Teach (Remember / file)

Turns notes or pasted dumps into durable claims (`origin=dump`). Produces Remembered card. **Files ≠ Ask memory until Remembered.**

### Ask (answer)

Answers from **this workspace’s** memory. Prefers settled claims; can surface contested disagreements. Refuses when memory too thin.

### Research

LangGraph: Planner → Retriever → Analyst ⇄ Verifier → Synthesizer. Hybrid retrieval. Report with citations/gaps. Can write claims back (`origin=research`).

### Watch

Standing topic briefs. Watch-origin claims may expire (~30d). Must not silently overwrite dump. Local catch-up while app open; optional cloud ~9am cron when signed in.

### Memory surface

Browse claims / graph for the open topic — not a separate chat agent.

### Supporting

Document peek; Settings; Ingest/Library import (index); ⌘K; Account OTP (optional).

---

## 11. Demo / evidence packs

| Pack | Path | Use |
|------|------|-----|
| Coffee | `evaluation/demo/Coffee/` | UAT Round 2 |
| Plants | `evaluation/demo/Plants/` | Import → memory UAT |
| DLM corpus | `data/documents/dlm` (local) | Benchmark suite |
| Demo script | `DEMO.md`, `APP_FUNCTIONS.md` | Viva / recording |

---

## 12. Config & runtime (accuracy)

- Sidecar: `http://127.0.0.1:8765`  
- Desktop: `cd desktop && npm run tauri dev` (auto-spawns sidecar)  
- Env: `.env` / `.env.example` — `LLM_PROVIDER`, `GROQ_API_KEY`, `TAVILY_API_KEY`, embedding provider, `AUTO_MEMORY`, `AUTO_RECALL`, `MAX_REVISIONS`, `PLAN_REVIEW_DEFAULT`, etc.  
- Auth local: `auth/` Docker Postgres `:5433`, Better Auth `:3000`  
- Cloud Watch: `cloud-watch/` Docker; `CLOUD_WATCH_URL`, `AUTH_INTERNAL_SECRET`  

---

## 13. Abstract draft seed (≤200 words — update numbers after final eval)

In the fast-evolving context of artificial intelligence, knowledge workers and students still face inefficiencies in autonomous research and literature synthesis because single large language models frequently hallucinate, lose long-term context, and demand constant human supervision. This project develops a graph-based multi-agent framework for autonomous research and lifelong personal knowledge management as a privacy-preserving, local-first Second Brain. Using Agile two-week sprints and requirements from a survey of 62 respondents, the system implements LangGraph multi-agent workflows, retrieval-augmented generation with a persistent Chroma store, hybrid personal/web/academic retrieval, and verifier self-critique loops, delivered as a Tauri 2.0 desktop application with a Python sidecar and optional Bring-Your-Own-Key cloud models. Workspace-scoped Teach, Ask, Research, and Watch jobs share durable claim memory with write-back. Evaluation uses grounded Ask/research benchmarks and user acceptance testing alongside single-LLM baselines. The work aligns with United Nations Sustainable Development Goal 9 by advancing inclusive, resilient AI knowledge infrastructure for individual researchers and small organisations.

**Keywords:** Multi-Agent Frameworks; Autonomous Research; Personal Knowledge Management; Retrieval-Augmented Generation; LangGraph; Second Brain

---

## 14. Writing rules specific to this project

1. Programme is **CSAI** (APD3F2601CSAI) → Chapters 3–5 follow **CS/CSAI** tables only.  
2. **Official title is locked** (§0.3). Product name **Nous** may appear in body after first mention; never in the title.  
3. **Aim, objectives, SDG 9, survey n=62 stats, supervisors** are locked from IR/proposal.  
4. Never claim the five LangGraph nodes are user-visible “team members.”  
5. Never claim files are automatically “remembered” without Teach/digest.  
6. Never claim Semantic Scholar, full MCP suite, or completed 52-query Java suite unless true — use §0.7.  
7. Prefer “topic workspace / vault memory / Manager router / write-back” vocabulary for Sem 2 UX.  
8. When describing databases, distinguish vault files + Chroma from optional Auth Postgres.  
9. Chapter 6 numbering: **6.1 Critical Evaluation, 6.2 Limitation, 6.3 Recommendation**.  
10. Primary SDG is **9**, not 4.

---

## 15. Canonical internal docs (read if expanding)

| File | Use |
|------|-----|
| Investigation Report DOCX | LOCKED Ch1–3 narrative, survey, RTM, lit review baseline |
| Approved proposal (portal) | Title, SDG9, target users, early objectives |
| `CURRENT_STATUS.md` | How the app works **today** (wins product conflicts) |
| `APP_FUNCTIONS.md` | Demo explanation language |
| `MEMORY.md` | Claim/origin/isolation contract |
| `docs/AGENT_LAYER.md` | Recall, write-back, goal/watch loops |
| `docs/SEMESTER2_ARCHITECTURE.md` | Sem 2 design intent |
| `PROJECT_SUMMARY.md` | Phase history (may lag workspace model) |
| `evaluation/EVIDENCE.md` | Eval checklist status |
| `evaluation/uat_questionnaire.md` | UAT instrument |

---

## 16. Placeholders remaining for final FYP submission

Already known from IR/proposal (do not treat as missing):

- [x] Locked FYP title  
- [x] Supervisor Mr. Amad Arshad; second marker Ms. Mary Ting  
- [x] Survey n=62 + analysis + RTM (carry into Ch3; refresh figures from IR)  
- [x] Ethics forms / PPF / Sem 1 log sheets / Sem 1 Gantt / Turnitin pages exist in IR appendices — **re-include / update** for final report as required  

Still needed / verify:

- [ ] Dual vs non-dual cover logos  
- [ ] Sem 2 log sheets to complete **six** total meetings  
- [ ] Updated Gantt covering Sem 2  
- [ ] A3 poster (Appendix D)  
- [ ] Real UAT scores (≥3 testers; target 5–8)  
- [ ] Full DLM benchmark / ablation / Claude+Grok baseline numbers  
- [ ] Final Turnitin ≤20% on the **final** report  
- [ ] Confirm Semantic Scholar / MCP scope wording with supervisor if examiners will probe  

---

*End of writer context. Prefer LOCKED IR/proposal fields for identity/aim/objectives/SDG/survey; prefer Sem 2 product docs for what the software actually does.*
