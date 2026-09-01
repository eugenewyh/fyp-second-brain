# FYP Report Writer Context — Nous (CSAI)

**Purpose:** Single source of truth for an AI writer completing the APU School of Computing FYP final report.  
**Programme track:** **CSAI** (B.Sc. Hons Computer Science — Artificial Intelligence) — **NOT CSDA**.  
**Intake / class:** APD3F2601CSAI  
**Guideline sources:** *New FYP Structure Guidelines — updated 7 Oct 2024* (SOC & SOT, V1-AUGUST2023); *FYP Final Report Template* (APU, 2026).  
**Student:** Wong Yan Hao (TP068819)  
**Supervisor:** Mr. Amad Arshad  
**Second marker:** Ms. Mary Ting  
**Approved title source:** Student Proposed (submitted 2026-02-09; status **APPROVED**)  
**Investigation Report:** `Wong Yan Hao-TP068819-APD3F2601CSAI-IR.docx` (Semester 1)  
**Product name (in-app only):** Nous — **do not put the product name in the official FYP title**.  
**Python package / monorepo:** `fyp-second-brain` / `second_brain`  
**Shipped release (GitHub):** Nous **0.1.2** — last tagged public build (`.dmg` / `.exe`).  
**Local development:** Same tag + **uncommitted Sem 2 work** (Memory sidebar/graph, router retrain, UI polish, etc.) — treat **`CURRENT_STATUS.md` + working tree** as the product truth for the FYP report, not the release notes alone.  
**Last synced:** September 2026 (local codebase + IR + approved proposal + guidelines)

### Version wording for the FYP report (read this)

| Situation | What to write |
|-----------|----------------|
| **Final report (recommended)** | Describe the **completed Sem 2 system** as implemented at submission date. Version label is optional: *“Nous desktop application (development build, September 2026)”* or bump to **v0.2.0** / **v1.0.0** when you cut a final submission release. |
| **Citing a public download** | Only say **v0.1.2** if screenshots/UAT/demo actually use that `.dmg`. Examiners may ask to run what you describe. |
| **Feature claims** | Every “what the system does” claim must match **what you demo in viva** — usually your **latest local build**, not an older release missing Memory mode / router fixes. |
| **Objective 4** | Satisfied by delivering Tauri 2 + sidecar — the **patch version (0.1.2 vs 0.2.0) does not matter** to examiners. |
| **Before submission** | Either (a) **package a fresh release** (e.g. v0.2.0) from current main and align report + screenshots to it, or (b) keep version generic (*“final prototype”*) and date-stamp the implementation chapter. |

**Do not** freeze the report to v0.1.2 if your demo includes features shipped only after that release — that creates an examiner mismatch. **Do not** invent a version number you never tagged unless you plan to tag before hand-in.

**For this context file:** Sem 2 product facts = **current local app** (`CURRENT_STATUS.md`). “v0.1.2” appears only where noting the last **public** GitHub release or a specific release artifact.

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
9. Chapter 6 guideline PDF numbering says “4.1/4.2/4.3” — use **6.1 / 6.2 / 6.3** in the real report.
10. The 2026 report template adds extra Chapter 1 subsections (Target Users, Project Deliverables, Data Scope, Project Boundaries and Constraints, Model Deployment). Include them under the appropriate CSAI sections (see §2).

---

## 0. Product one-pager (memorise)

### 0.1 One-liner

Local-first **second brain**: each **workspace** (topic vault folder) holds isolated lifelong memory. The user talks in that workspace. An internal **Manager** routes Teach / Ask / Research / Watch as jobs in the same thread. Research and Watch can **write back** into that topic’s memory.

**Tagline:** Research that remembers *you*.

**Examiner / viva line:** Flagship chat AIs are general assistants. Nous is a local-first mind for the user’s knowledge: knowledge they own, multi-agent research that uses it, and results that update it over time.

**Vocabulary note:** Internal code and some docs say **channel**; the FYP report should prefer **workspace** or **topic vault**. They mean the same thing: one folder, one memory partition, one chat session binding.

### 0.2 Mental model (do not invert)

| Concept | Meaning |
|--------|---------|
| **Workspace** | Topic vault folder (e.g. Coffee, FYP, DLM) with isolated memory |
| **Chat** | One Manager thread bound to that workspace (`projectPath`) |
| **Manager** | Invisible router (`take_turn`) — not a UI character or sidebar member |
| **Memory** | Durable **claims** for that workspace — not a global chat history |
| **Skills / jobs** | `file` (Teach), `answer` (Ask), `research`, `watch`, `refuse`, topic ops |

**Forbidden framings in the report:**

- “ChatGPT with a sidebar”
- Hiring / adding agents; Planner/Retriever/Verifier as people in the UI
- Nesting Teach/Research/Watch as separate chats under a workspace
- Global user memory store across all topics
- Treating web search alone as the differentiator
- Claiming ingested files are automatically “remembered” without Teach/digest

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

1. To create and deploy a LangGraph-based multi-agent architecture that uses persistent vector database memory, making it possible to retain personal knowledge throughout life and to be aware of context across sessions. *(Delivered: Chroma + workspace claim memory + Manager recall/write-back + auto-recall hierarchy.)*  
2. To incorporate real-time hybrid retrieval systems that smoothly integrate the personal documents of the user, web search APIs (Tavily) and scholarly archives (arXiv, Semantic Scholar) into a single retrieval-augmented generation (RAG) pipeline. *(Delivered: personal Chroma + BM25 + Tavily + arXiv. Semantic Scholar was planned in IR; treat as partial/deferred unless student confirms integration — see §0.7.)*  
3. To test system performance in terms of a curated benchmark (52 research queries) of task completion rate, rate of hallucination, and citation accuracy against strong single-LLM baselines (Claude 3.5 Sonnet and Grok-3). *(Sem 2 corpus evolved: 20-query DLM suite replaced the retired Java 52-set — explain honestly in Ch5; baselines remain Claude/Grok chat.)*  
4. To roll out the solution as a cross-platform desktop application with Tauri 2.0, which offers native performance, local-first privacy, and optional Bring-Your-Own-Key cloud LLM access. *(Delivered: Tauri 2 + Svelte 5 + Python sidecar v0.1.2; BYOK / NVIDIA NIM / Groq / Ollama / OpenRouter.)*

### 0.6 LOCKED SDG + keywords (from IR / proposal)

**Primary SDG (proposal + IR):** **SDG 9** — Industry, Innovation and Infrastructure  
*Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation.*  
Map to Targets **9.5** (scientific research / technological capabilities) and **9.b** (local technology development) as in the IR.

Do **not** make SDG 4 the primary mapping. Optional secondary mention of education/lifelong learning is fine only if clearly secondary to SDG 9.

**IR abstract keywords (use these — max 6):**  
Multi-Agent Frameworks; Autonomous Research; Personal Knowledge Management; Retrieval-Augmented Generation; LangGraph; Second Brain

### 0.7 IR → Sem 2 evolution (writer must reconcile, not hide)

| IR / proposal promise | Sem 2 actual product (Nous 0.1.2) |
|----------------------|-------------------------------------|
| “Second Brain” / PKOS framing | Keep; in-app name **Nous**; UX uses **workspaces** (topic folders) |
| 52-query Java/lecture-style benchmark | Retired; **20-query DLM vault** suite (`evaluation/benchmarks.json` v2.0) |
| Ollama as default free local LLM | Still supported; **NVIDIA NIM** default in release builds; embeddings default **fastembed** (Ollama not required for embeds) |
| Semantic Scholar | Not a first-class tool in core hybrid path; **arXiv + Tavily** are |
| MCP toolkit (Notion, Drive, etc.) | **Optional** Notion MCP-shaped adapter (`ENABLE_MCP`, off by default) |
| Cloud-hosted deployment out of scope | Vault remains local-first; **optional** Auth + Cloud Watch for identity/briefs only |
| Agents as research pipeline | Same five nodes **inside Research**; user-facing jobs via **Manager**: Teach / Ask / Research / Watch |
| Self-critique / Verifier | Implemented (grounding + LLM verifier + revision loop; `critique_history`) |
| Survey n=62 (April 2026) | LOCKED for Ch3; Sem 2 adds UAT (target 5–8) |
| Simple keyword router | **Multi-tier router**: rules → local TF-IDF job model → Gemini Flash-Lite → heuristic fallback → `apply_policy` clamp |
| Empty workspace behaviour | **v0.1.2:** general questions on empty topics **auto-route to Research** (hybrid lookup) instead of refuse |

---

## 1. Front matter checklist (guidelines)

| Item | Writer instructions |
|------|---------------------|
| **Cover page** | Use APU template. Dual degree → APU + DMU logos; non-dual → APU logo only (right). No header/footer on cover. **Title = locked §0.3.** Student: Wong Yan Hao / TP068819 / APD3F2601CSAI. Degree: B.Sc. (Hons) Computer Science (Artificial Intelligence). |
| **Declaration of Thesis Confidentiality** | Student inserts official form from FYP manager folder. |
| **Library form** | Student inserts official form (cataloguing detail + abstract + keywords). |
| **Acknowledgement** | One page. Thank **Mr. Amad Arshad** (supervisor), **Ms. Mary Ting** (second marker), April 2026 survey participants (n=62), APU, family/friends. IR acknowledgement can be adapted for the final report. |
| **Abstract** | One paragraph, ≤200 words: purpose, problem, methods, results/conclusion, significance, **SDG 9**, then IR keywords (§0.6). Evolve IR abstract from future tense to completed-system tense; update eval numbers to Sem 2 evidence. |
| **Table of Contents** | Mirror chapters below. Each chapter starts on a new page. |
| **List of Figures / Tables** | Auto from report; each on new page. |

---

## 2. CHAPTER 1 — INTRODUCTION (CSAI)

### Outline (must follow guidelines Table 1 + 2026 template)

1.1 Introduction  
1.2 Problem Background  
1.3 Project Aim  
1.4 Objectives  
1.5 Scope  
1.6 Potential Benefit  
1.7 Overview of the FYP Documentation  
1.8 Project Plan  

**2026 template additions** (fold into the sections above — do not invent new chapter numbers):

| Template subsection | Where to place |
|--------------------|----------------|
| Target Users | Under **1.6 Potential Benefit** (or its own bullet list within 1.6) |
| Project Deliverables | Under **1.5 Scope** or **1.7 Overview** |
| Data Scope | Under **1.5 Scope** — vault documents, survey data, eval corpus (DLM notes), not training datasets |
| Project Boundaries and Constraints | Under **1.5 Scope** — hardware, API keys, local-first, no fine-tuning |
| Model Deployment | Under **1.5 Scope** or **1.6** — Tauri desktop bundle, sidecar, optional cloud Watch; **not** a hosted SaaS vault |

### Facts for 1.2 Problem Background (align with IR + proposal)

Lead with IR themes (cite IR sources where possible):

1. Standalone LLMs are largely **stateless**: hallucinate citations/facts, lose long-horizon context, need constant supervision (Alansari & Luqman, 2025; Singh et al., 2025).  
2. Knowledge workers spend substantial weekly time on literature review / verification; a large fraction is spent fixing AI output (Chen et al., 2025 — as cited in IR).  
3. Tools like ChatGPT / Claude / Grok do not seamlessly combine **local personal documents** with **real-time web/academic** sources in a privacy-preserving way.  
4. Note apps and basic RAG lack autonomous planning, self-critique loops, and lifelong write-back.  
5. **Survey evidence (n=62, April 2026):** top difficulties — summarising long papers **43.5%**; combining personal files/notes with AI **38.7%**; **79%** “Very Willing” to adopt a system that addresses these; Self-Check mean **4.52**; Unified Search highly valued; **80.6%** prefer hybrid or fully local deployment.  
6. Gap links to **SDG 9** Targets 9.5 and 9.b (IR).

Also weave Sem 2 product angles: workspace isolation; files ≠ memory until Teach; refuse-on-thin-memory when user explicitly grounds in notes; auto-research on empty topics for general questions.

### Scope (1.5) — IR baseline + Sem 2 delivery

**In scope (IR + delivered in Nous 0.1.2):**

- LangGraph multi-agent workflow: Planner, Hybrid Retriever, Document Analyst, Verifier/Self-Critic, Report Synthesizer  
- Persistent local vector DB (**Chroma**) + personal document ingest (PDF/TXT/MD/DOCX)  
- Hybrid retrieval: personal vault (Chroma + BM25) + **Tavily** web + **arXiv**  
- Self-critique / revision loops; cited reports with gaps; `critique_history`  
- **Tauri 2.0** desktop + **Python** FastAPI sidecar; BYOK / NVIDIA NIM / Groq / Ollama / OpenRouter  
- Multi-tier Manager router (rules + local ML job router + LLM + policy)  
- Optional MCP-shaped connectors (Notion adapter present; default off)  
- Sem 2 UX: **workspaces**, Manager jobs (Teach / Ask / Research / Watch), claim memory write-back  
- **Memory mode:** knowledge graph with `MemorySidebar` + `GraphView` (force-graph)  
- **Mission Control:** live research status, plan review, run details (`AgentWorkPanel`, `RunDetailsDrawer`)  
- Optional Auth (Better Auth + Postgres) + Cloud Watch (hosted briefs when Mac asleep)

**Out of scope (IR — keep unless supervisor agreed otherwise):**

- Full multi-user collaborative cloud SaaS as the primary product  
- Fine-tuning foundation models  
- Multimodal figure/table/image understanding inside PDFs (future)  
- Semantic Scholar as shipped first-class integration (unless student confirms otherwise)

**Constraints:** local hardware for Ollama; user-supplied API keys for cloud models; optional Auth/Cloud Watch does **not** move the vault off-device by default.

### Project deliverables (for template)

1. `second_brain` Python package — agents, memory, graph, ingestion, tools  
2. FastAPI sidecar (`sidecar/server.py`) — HTTP + SSE API on port 8765  
3. Tauri 2 desktop app (**Nous 0.1.2**) — macOS `.dmg` / Windows `.exe` via `scripts/package_release.sh`  
4. **Custom trained Manager job router** — TF-IDF + logistic regression classifier (`data/job_router/model.json`); see §16  
5. **Auth service + PostgreSQL database** — Better Auth email OTP, sessions, custom `devices` table; see §17  
6. Evaluation harness — 20-query DLM benchmark, job-router eval, baseline comparison scripts  
7. Documentation — IR, architecture docs, UAT instruments, demo packs (Coffee, Plants)  
8. Test suite — pytest (~37 modules, ~5,850 lines) + Vitest (~35 test files)

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
| Sem 2 | Workspace/Manager UX, durable claims, write-back, Watch, Memory graph UI, multi-tier router, v0.1.2 polish |

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
2. **RAG & persistent memory** — Chroma vs FAISS; lifelong local memory; claim-based PKM (IR §§2.2.2).  
3. **Second-Brain / PKM architectures** — Forte/Khoj framing; privacy vs Notion AI (IR §§2.2.3).  
4. **Self-critique / reflection** for hallucination mitigation (Renze, 2024; Park et al., 2026 as in IR).  
5. **Hybrid retrieval** — personal + web + academic; BM25 + dense retrieval.  
6. **Evaluation of grounded assistants** — completion, hallucination, citation accuracy; Sem 2 gold-hit / honest-gap / invented-fact.  
7. **Desktop local-first AI** — Tauri vs Electron; sidecar pattern for Python AI stacks.

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
| Elicit / Perplexity | Research synthesis | No lifelong personal vault write-back |

**Conclusion:** Gap = local-first lifelong memory + graph multi-agent research with self-critique + hybrid personal-first retrieval + desktop delivery (+ Sem 2 workspace claim write-back).

### 2.4 Technical research — stack (IR + Sem 2 / v0.1.2)

| Layer | Choice | Justification |
|-------|--------|---------------|
| Language | Python 3.12 | AI ecosystem / LangGraph |
| IDE | VS Code / Cursor (IR) | Debugging, Git, AI workflows |
| Orchestration | LangGraph | Deterministic routing, verifier loops |
| Vectors | Chroma (local persistent) | Lifelong personal KB; metadata; collection `personal_knowledge` |
| Lexical | BM25 (`rank-bm25`) | Hybrid personal retrieval |
| Embeddings | fastembed default (`BAAI/bge-small-en-v1.5`); optional Ollama / OpenAI-compatible | Local-friendly; Ollama not required for embeds |
| LLM | NVIDIA NIM default (`nvidia/nemotron-3-super-120b-a12b`); Groq, OpenRouter, Ollama BYOK | Release builds bundle NVIDIA key; matches hybrid/local survey preference |
| Fast LLM tier | `LLM_FAST_MODEL` | Ask, analyst, verifier (cost/latency) |
| Web | Tavily | Tool search API |
| Academic | arXiv (Semantic Scholar deferred/partial) | IR planned both; implement honestly |
| Job router | TF-IDF + logistic regression (`data/job_router/model.json`) + Gemini Flash-Lite | Deterministic policy clamp on top |
| Tools / MCP | Optional Notion adapter | Survey valued Notion / Drive integrations |
| Desktop | Tauri 2 + Svelte 5 + SvelteKit (static) + Python sidecar | Cross-platform, local files, small footprint |
| Frontend graph | force-graph | Memory/knowledge graph view |
| Editor | TipTap 3 | In-app notes |
| Auth / Cloud Watch | Optional Better Auth + Postgres; Cloud Watch service | Identity + morning briefs; vault stays local |
| OS | Windows / macOS / Linux (Tauri); primary demo macOS | IR cross-platform claim |
| VCS | Git / GitHub | IR |
| Bundle ID | `com.tp068819.nous` | Release identity |

**Hardware:** consumer laptop; Docker only if demonstrating auth/cloud-watch.

**User data paths (release):** macOS `~/Library/Application Support/com.tp068819.nous`; Windows `%APPDATA%\com.tp068819.nous`. Dev uses repo `data/`.

---

## 4. CHAPTER 3 — METHODOLOGY (CSAI / CS — not CSDA)

### Outline (mandatory for CSAI — guidelines Table 3)

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

Map IR Table 3 sprint plan + Sem 2 increments (workspace Manager, claims, Watch, Memory UI, router retrain, eval/UAT, v0.1.2 release).

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
- FR3 Ask from settled claims; refuse if thin (notes-intent + zero claims)  
- FR4 Research hybrid report + write-back  
- FR5 Watch briefs (`origin=watch`, optional `expires`)  
- FR6 Index-only ingest (files ≠ memory until Teach)  
- FR7 SSE / status lines / Mission Control transparency  
- FR8 Settings / BYOK / model tiers  
- FR9 Optional Account + cloud briefs  
- FR10 Memory graph browse (all workspaces or scoped)  
- FR11 Auto-research on empty-topic general questions (v0.1.2)  
- FR12 Topic ops: retarget, merge, split, also-retrieve  

**Survey limitations (IR):** n=62; Computing/AI overrepresentation; stated preference ≠ observed behaviour → motivate Sem 2 UAT.

---

## 5. CHAPTER 4 — DESIGN AND IMPLEMENTATION (CSAI / CS)

### Outline (guidelines Table 4)

4.1 Introduction  
4.2 Design (architecture, UML as appropriate)  
4.3 Database Design (optional — include persistence design)  
4.4 Interface Design  
4.5 Implementation (screenshots + discussion; AI pipeline steps allowed here)  
4.6 Sample codes  
4.7 Summary  

### 4.2 Architecture (facts — Nous 0.1.2)

```
┌─────────────────────────────────────────────────────────────┐
│  Desktop: Tauri 2 + Svelte 5 + SvelteKit (static)         │
│  AppShell · MemorySidebar · GraphView · AgentPane         │
│  WatchHome · ComposerDock · Settings · ⌘K                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP + SSE (:8765)
┌──────────────────────────▼──────────────────────────────────┐
│  Sidecar: FastAPI + Uvicorn (sidecar/server.py)             │
│  /api/manager/turn · /api/chat · /api/digest                │
│  /api/research/stream · /api/goals/stream · /api/watches    │
│  ingest · vault search · settings · cloud-watch sync        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  second_brain (src/second_brain/)                           │
│  Manager take_turn → router/turn.py → policy.py             │
│  LangGraph: planner → retriever → analyst ⇄ verifier        │
│             → synthesizer                                     │
│  Memory: claims, digest, recall, learning, Chroma           │
│  Tools: Tavily, arXiv; optional Notion MCP                  │
└─────────────────────────────────────────────────────────────┘
         optional
┌────────────────────┐  ┌─────────────────────────┐
│ auth/              │  │ cloud-watch/            │
│ Better Auth + PG   │  │ Hosted briefs + BYOK    │
└────────────────────┘  └─────────────────────────┘
```

**Full stack detail:** backend §18 (Tauri Rust → sidecar → `second_brain` → auth/cloud-watch); frontend §19 (Svelte 5 SPA, stores, component tree, vault/editor layers).

**Manager routing pipeline (Sem 2):**

```
User message
  → forced job / attachments?
  → topic ops (retarget, merge, split)?
  → meta / capabilities reply?
  → rule tier (search intent, notes intent, empty-topic question → research)
  → recall snapshot (claim count, thin memory)
  → local TF-IDF job-router model
  → Gemini Flash-Lite LLM router
  → heuristic fallback_job
  → apply_policy (hard invariants — code, not model)
  → dispatch | clarify (max 2) | refuse
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
| `refuse` | Thin memory + notes-intent — do not invent |
| `retarget` / `merge` / `split` | Topic folder operations |

Dispatch-first; at most **two** clarifying asks when vague.

**Policy highlights (`agent/policy.py`):**

- Attachments / long dumps → `file`  
- Explicit search/research phrasing → `research`  
- “According to my notes” with 0 claims → `refuse`  
- General question on empty topic → `research` (auto-research, v0.1.2)  
- “Teach me about X” → `answer` (explain from notes, not remember)  
- Watch claims cannot silently overwrite dump (`PROTECTED_ORIGINS`)

### 4.3 Database / persistence design

The project uses **multiple persistence layers**. The vault is **not** stored in Postgres — distinguish them clearly in the report.

#### 4.3.1 Vault + vector memory (primary product data)

1. **Filesystem vault** under `data/documents/{topic}/` (or `NOUS_DATA_DIR`)  
   - `memory/claims/{slug}.md` — frontmatter claim schema  
   - `memory/project.md`, `project-log.md`, `agents/{session_id}/`, learnings  
   - `research/`, `briefs/`, `watches/`, notes  
2. **Chroma** local vector DB (`data/chroma/`) — chunks for retrieval; collection `personal_knowledge`  
3. **BM25 index** — lexical hybrid alongside dense vectors  
4. **Client state** — `localStorage` for assistant sessions (`sb-agent-sessions-v2`), theme prefs

#### 4.3.2 Custom ML artifact (bundled, not a DB)

5. **Job router model** — `data/job_router/model.json` (serialized TF-IDF vocabulary + logistic-regression weights). Full spec in **§16**.

#### 4.3.3 Auth PostgreSQL database (identity only — §17)

6. **PostgreSQL 16** via `auth/` service — Better Auth tables + custom `devices` table. Stores **identity and sessions only**; vault/claims/Chroma never touch this DB.  
7. **Cloud Watch store** (optional) — watches/briefs + encrypted BYOK keys (separate from auth Postgres and personal markdown vault)

**Auth ER (writer should diagram):**

```
user (Better Auth) ──< session (Better Auth)
       │
       └──< devices (custom migration)
              id UUID PK
              user_id TEXT → user
              device_id TEXT UNIQUE
              public_key TEXT
              name TEXT
              created_at TIMESTAMPTZ
```

Better Auth also creates standard tables (`user`, `session`, `verification`, `account`, etc.) via `npm run migrate`. The student added a **custom `devices`** table via `auth/src/migrate-devices.ts` for desktop device registration (Cloud Watch sync).

**Claim schema (frontmatter):** `id`, `claim`, `status` (`settled`|`active`|`contested`|`superseded`), `origin` (`dump`|`watch`|`research`), `source_path`, `source_quote`, `content_hash`, dates, `supersedes`, `expires` (watch only).

**Skip-list (not Teach dumps):** `memory/**`, `briefs/**`, `watches/**`, `research/**`, `instruction.md`.

**Memory lifecycle (five stages — not a sixth agent):** Capture → Consolidate → Retrieve → Reconcile → Decay (watch-only expiry). See `MEMORY.md`.

### Diagrams the writer should produce (suggest)

- System architecture (above)  
- Use case diagram: Student/KnowledgeWorker × Teach, Ask, Research, Watch, Ingest, Memory browse, Settings, Account  
- Activity / sequence: User message → Manager → Research SSE → write-back  
- Component diagram: desktop / sidecar / agents / memory / tools  
- Optional ER for auth Postgres devices/sessions only  
- Memory graph node types: note, research, learning, digest, topic  

### 4.4 Interface design

Surfaces (Nous 0.1.2):

| Surface | Role | Key files |
|---------|------|-----------|
| Sidebar | New workspace; flat `#Name` list; Memory nav; Watch nav | `WorkspaceChatTree.svelte`, `AppShell.svelte` |
| Chat / AgentPane | Landing vs thread; composer “Message this workspace…”; job chips | `AgentPane.svelte`, `ChatThread.svelte`, `ComposerDock.svelte` |
| Remembered card | Teach confirmation | `AgentRunBlock.svelte` |
| Research status / Mission Control | Planner → Retriever → Analyst → Verifier → Synthesizer; plan review | `AgentWorkPanel.svelte`, `RunDetailsDrawer.svelte`, `components/mission/*` |
| Report viewer | Citations `[n]`, gaps, save/open report | research render components |
| Memory mode | Sidebar controls + knowledge graph canvas | `MemorySidebar.svelte`, `MemoryHome.svelte`, `GraphView.svelte`, `memory.svelte.ts` |
| Watch UI | Focus editor, run, history | `WatchHome.svelte`, `WatchEditor.svelte` |
| Document peek | Read/edit notes beside chat (TipTap) | peek + `NoteEditor` |
| Settings | Models, connectors, appearance (nous/ember/mono/**lilac**), Account | `AppSheet.svelte`, `theme/palette-registry.ts` |
| Command palette ⌘K | e.g. Remember topic notes | `CommandPalette.svelte` |
| Topic picker | Scope memory graph / cross-workspace filter | `TopicPicker.svelte` |

UI references used in product thinking: LangGraph Studio (transparency), Elicit (report), Linear (polish), Khoj/Obsidian (KB), Cursor (anti-chatbot transparency).

### 4.5 Implementation subsections (screenshot + discuss)

Suggested structure for 4.5.x:

1. Workspace sidebar and new workspace  
2. Empty workspace / Chat landing (auto-research behaviour)  
3. Teach → Remembered  
4. Ask with source chips / refuse on thin notes-intent memory  
5. Research run with status lines, plan review, and report  
6. Memory mode — sidebar filters + knowledge graph  
7. Watch brief  
8. Settings (models, Tavily, Lilac theme)  
9. Account OTP (optional)  
10. Ingest / Library import (index-only)  

For each: what it does, which requirement it satisfies, how it maps to Manager job or graph node.

**AI pipeline “analysis steps” (allowed under Ch4.5 for ML/AI systems):**

1. Ingest / chunk / embed → Chroma (+ BM25 index)  
2. Teach digest → claims (`digest_and_link`)  
3. Auto-recall snapshot for Ask/Research (`recall.py` hierarchy)  
4. Planner tagged queries `[personal]|[web]|[arxiv]`  
5. Hybrid retrieve + analyst draft  
6. Grounding + verifier critique / revise (`critique_history`)  
7. Synthesizer report + bibliography  
8. Persist learning/claims if policy says so (`persist_research_memory`)  
9. Optional goal loop (`/api/goals/stream`) for multi-pass deepening  

### 4.6 Sample code pointers (for Appendix F + Ch4.6)

| Program / module | Path | Role |
|------------------|------|------|
| Research graph | `src/second_brain/graph.py` | `build_graph`, `route_after_verifier`, streaming wrappers |
| Graph state | `src/second_brain/state.py` | `GraphState` TypedDict, `critique_history` |
| Manager | `src/second_brain/agent/manager.py` | `take_turn` |
| Router | `src/second_brain/agent/router/turn.py` | Multi-tier routing pipeline |
| Policy | `src/second_brain/agent/policy.py` | Deterministic job clamp |
| Claims | `src/second_brain/memory/claims.py` | Durable memory |
| Hybrid retriever | `src/second_brain/agents/hybrid_retriever.py` | Source routing |
| Verifier / grounding | `agents/verifier.py`, `agents/grounding.py` | Self-critique |
| Sidecar | `sidecar/server.py` | HTTP/SSE API |
| Desktop API client | `desktop/src/lib/api.ts` | UI ↔ sidecar |
| Chat UI | `desktop/src/lib/components/app/AgentPane.svelte` | In-session jobs |
| Memory store | `desktop/src/lib/stores/memory.svelte.ts` | Graph mode shared state |

Include 1–2 short excerpts with explanation (not entire files).

### Monorepo map

```
fyp-second-brain/
├── src/second_brain/     # Core AI package
├── sidecar/              # FastAPI
├── desktop/              # Tauri 2 + Svelte 5 (Nous 0.1.2)
├── auth/                 # Optional Better Auth
├── cloud-watch/          # Optional hosted Watch
├── evaluation/           # Benchmarks, UAT, demo packs, results
├── scripts/              # CLI ingest/query/research/eval/package_release
├── tests/                # ~37 pytest modules (~5,850 lines)
└── data/documents/       # User vault (local)
```

---

## 6. CHAPTER 5 — RESULTS AND DISCUSSIONS (CSAI / CS — not CSDA)

### Outline (guidelines Table 5)

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

### 5.2.1 Unit / automated testing — map to pytest + Vitest

Present as formal test cases (Expected / Actual / Pass|Fail) **and** summarise automated suite:

**Python (`tests/` — ~37 modules, ~5,850 lines):**

| Area | Test modules (examples) |
|------|-------------------------|
| Ingestion / retrieval | `test_ingestion.py`, `test_retrieval.py`, `test_retrieval_notes.py` |
| Agents / graph routing | `test_agents.py`, `test_graph_integration.py`, `test_plan_execute.py` |
| Hybrid / grounding / citations | `test_hybrid.py`, `test_hybrid_retrieval.py`, `test_grounding.py`, `test_citations.py` |
| Manager / router / policy | `test_manager.py`, `test_router.py`, `test_supervisor.py`, `test_job_router.py` |
| Topics | `test_topic_ops.py`, `test_topic_memory.py` |
| Memory / claims | `test_claim_provenance.py`, `test_digest_link.py`, `test_agent_memory.py` |
| Watch / cloud | `test_watch.py`, `test_watch_api.py`, `test_cloud_watch.py`, `test_cloud_watch_sync.py` |
| Deep Ask | `test_deep_ask.py`, `test_deep_ask_pipeline.py` |
| Evaluation harness | `test_evaluation.py` |
| Daily review / critique | `test_daily_review.py`, `test_critique.py` |

**Frontend (`desktop/` — ~35 Vitest `*.test.ts` files):**

| Area | Examples |
|------|----------|
| Assistant routing / intent | `intent.test.ts`, `channel-empty.test.ts`, `composer-skills.test.ts` |
| Vault / graph | `vault-graph.test.ts`, `graph-data.test.ts`, `search-dispatch.test.ts` |
| Research UI | `status-copy.test.ts`, `render.test.ts`, `agent-graph.test.ts` |
| Theme / auth | `theme-prefs.test.ts`, `auth-prefs.test.ts` |

Example unit-style rows (writer expands):

| TC | Component | Input | Expected | Status |
|----|-----------|-------|----------|--------|
| TC-M1 | Manager | Clear research goal | `job=research` dispatch | Passed |
| TC-M2 | Manager | Empty vault + notes-intent ask | `refuse` | Passed |
| TC-M3 | Manager | Empty vault + general question | `job=research` (auto-research) | Passed |
| TC-V1 | Verifier | Bad citation bounds | Revision / fail grounding | Passed |
| TC-C1 | Claims | Watch vs dump collision | Contested sibling, no silent overwrite | Passed |
| TC-R1 | Router | TF-IDF model | Job prediction + policy clamp | Passed |

### 5.2.2 + 5.3.2 UAT

Use `evaluation/uat_questionnaire.md` structure:

- Demographics per tester (Appendix G)  
- UI criteria Likert (adapt “webpage” wording to **desktop app**)  
- Functionality Yes/No  
- Tasks: Teach→Ask, Research, Memory graph, parallel chats  
- Aggregate means, discuss themes (trust in sources, clarity of status lines, files≠memory insight)

**Placeholder:** insert real scores when collected. Status as of Sep 2026: **UAT responses pending**.

### AI / research evaluation evidence (fold into 5.3 discussion — still CSAI “results”, not CSDA model chapter)

**IR plan:** curated **52** research queries; metrics = task completion, hallucination rate, citation accuracy; baselines = Claude 3.5 Sonnet and Grok-3; ablation multi-agent vs single-LLM.

**Sem 2 actual suite:** `evaluation/benchmarks.json` v2.0 — **20 queries** on **DLM** vault (diffusion-LM notes). The Semester 1 Java 52-query set was **retired** because those PDFs are no longer the ingested corpus. Writer must explain this corpus change when discussing Objective 3.

| Category | Count | Mode | Intent |
|----------|-------|------|--------|
| personal_vault | 8 | query | Grounded in notes |
| hybrid | 4 | research | Personal + web/arXiv |
| research | 4 | research | Multi-step synthesis |
| edge_gaps | 4 | query/research | Must refuse / not invent |

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

### Outline (guidelines Table 6 — note PDF typo “4.1”; use 6.x)

6.1 Critical Evaluation  
6.2 Limitation  
6.3 Recommendation  

### 6.1 Critical evaluation — talking points

- Objectives met: topic memory, multi-agent research, desktop delivery (v0.1.2), evaluation harness  
- Contribution: local-first workspace memory + write-back loop vs generic chat  
- Strengths: hybrid personal-first retrieval; verifier/grounding; refuse path; dump protection; transparent stages; Memory graph UX; multi-tier router with policy safety net  
- SDG 9 alignment: local technology development (9.b), research capability infrastructure (9.5)

### 6.2 Limitations

- Research latency / LLM API rate limits and model availability (see 404 failures in research eval)  
- Quality depends on upstream LLM; not a trained custom domain model  
- UAT/full benchmark/baseline comparison may still be incomplete at draft time  
- Desktop primarily macOS for demos; cloud Watch needs hosting + auth ops  
- Claim extraction quality bounded by digest prompts  
- Not a full collaborative multi-user vault  
- Semantic Scholar and full MCP connector suite not shipped as IR originally scoped  
- Router ML model requires periodic retraining as UX intents evolve  

### 6.3 Recommendations / future work

- Complete full 20-query + ablation + Claude/Grok baselines + ≥3–8 UAT  
- Stronger plan-review UX and cancel semantics polish (server-side abort)  
- Broader connectors (Notion MCP already flagged optional; Drive next)  
- PDF/DOCX export; richer knowledge graph UX (backlinks, layout presets)  
- Mobile companion or improved cloud brief reliability  
- Better eval metrics for contested-claim honesty  
- Semantic Scholar integration if academic coverage must match IR Objective 2 literally  

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
| **F** | Sample code implementation | From §5.4.6 paths |
| **G** | Respondent demographic profile (survey/interview + system testers; pseudonyms OK) | Student |
| **H** | Turnitin first 2 pages; similarity ≤ **20%** | Student |

*Note: Some older template variants list Appendix H as “System Deployment”; the Oct 2024 guidelines use Turnitin for Appendix H. Follow the guidelines PDF unless supervisor specifies otherwise.*

---

## 10. Feature catalogue (for accurate wording)

### Teach (Remember / file)

Turns notes or pasted dumps into durable claims (`origin=dump`). Produces Remembered card. **Files ≠ Ask memory until Remembered.** Vault watcher may index files to Chroma only.

### Ask (answer)

Answers from **this workspace’s** memory. Prefers settled claims; can surface contested disagreements. Refuses when memory too thin **and** user used notes-intent phrasing (“according to my notes”).

### Research

LangGraph: Planner → Retriever → Analyst ⇄ Verifier → Synthesizer. Hybrid retrieval. Report with citations/gaps. Can write claims back (`origin=research`). Plan review on by default. Goal mode for multi-pass deepening.

### Watch (Scheduled Research)

Standing topic briefs. Watch-origin claims may expire (~30d). Must not silently overwrite dump. Local catch-up while app open; optional cloud ~9am cron when signed in.

### Memory mode

Browse claims / knowledge graph for one or all workspaces — not a separate chat agent. `MemorySidebar` provides search, type filters, topic scope, selection peek, “Ask about this” shortcut.

### Supporting

Document peek (TipTap); Settings; Ingest/Library import (index); ⌘K; Account OTP (optional); themes (nous, ember, mono, lilac).

---

## 11. Demo / evidence packs

| Pack | Path | Use |
|------|------|-----|
| Coffee | `evaluation/demo/Coffee/` | UAT Round 2 (espresso notes) |
| Plants | `evaluation/demo/Plants/` | Import → memory UAT |
| DLM corpus | `data/documents/dlm` (local) | Benchmark suite |
| Demo script | `DEMO.md`, `APP_FUNCTIONS.md` | Viva / recording |
| Teach dump | `evaluation/demo/TEACH_DUMP.txt` | UAT paste text |

---

## 12. Config & runtime (accuracy — v0.1.2)

- Sidecar: `http://127.0.0.1:8765`  
- Desktop: `cd desktop && npm run tauri dev` (auto-spawns sidecar)  
- Env: `.env` / `operator.env` / user data `.env` — `LLM_PROVIDER`, `LLM_MODEL`, `LLM_FAST_MODEL`, `GROQ_API_KEY`, `TAVILY_API_KEY`, `EMBEDDING_PROVIDER`, `AUTO_MEMORY`, `AUTO_RECALL`, `MAX_REVISIONS`, `PLAN_REVIEW_DEFAULT`, `ENABLE_MCP`, etc.  
- Default LLM provider: **nvidia** (`nvidia/nemotron-3-super-120b-a12b`)  
- Default embeddings: **fastembed** (`BAAI/bge-small-en-v1.5`)  
- Auth local: `auth/` Docker Postgres `:5433`, Better Auth `:3000`  
- Cloud Watch: `cloud-watch/` Docker; `CLOUD_WATCH_URL`, `AUTH_INTERNAL_SECRET`  
- Release: `scripts/package_release.sh`, `scripts/ship_release.sh`, `docs/RELEASE.md`  
- Bundle ID: `com.tp068819.nous`

---

## 13. Abstract draft seed (≤200 words — update numbers after final eval)

In the fast-evolving context of artificial intelligence, knowledge workers and students still face inefficiencies in autonomous research and literature synthesis because single large language models frequently hallucinate, lose long-term context, and demand constant human supervision. This project develops a graph-based multi-agent framework for autonomous research and lifelong personal knowledge management as a privacy-preserving, local-first Second Brain. Using Agile two-week sprints and requirements from a survey of 62 respondents, the system implements LangGraph multi-agent workflows, retrieval-augmented generation with a persistent Chroma store, hybrid personal, web, and academic retrieval, and verifier self-critique loops, delivered as a Tauri 2.0 desktop application (Nous 0.1.2) with a Python sidecar and optional Bring-Your-Own-Key cloud models. Workspace-scoped Teach, Ask, Research, and Watch jobs share durable claim memory with write-back, while a knowledge-graph Memory mode makes lifelong learning inspectable. Evaluation uses grounded Ask and research benchmarks and user acceptance testing alongside single-LLM baselines. The work aligns with United Nations Sustainable Development Goal 9 by advancing inclusive, resilient AI knowledge infrastructure for individual researchers and small organisations.

**Keywords:** Multi-Agent Frameworks; Autonomous Research; Personal Knowledge Management; Retrieval-Augmented Generation; LangGraph; Second Brain

---

## 14. Writing rules specific to this project

1. Programme is **CSAI** (APD3F2601CSAI) → Chapters 3–5 follow **CS/CSAI** tables only.  
2. **Official title is locked** (§0.3). Product name **Nous** may appear in body after first mention; never in the title.  
3. **Aim, objectives, SDG 9, survey n=62 stats, supervisors** are locked from IR/proposal.  
4. Never claim the five LangGraph nodes are user-visible “team members.”  
5. Never claim files are automatically “remembered” without Teach/digest.  
6. Never claim Semantic Scholar, full MCP suite, or completed 52-query Java suite unless true — use §0.7.  
7. Prefer “topic workspace / vault memory / Manager router / write-back” vocabulary for Sem 2 UX; note “channel” only when quoting code.  
8. When describing databases, distinguish vault files + Chroma from optional Auth Postgres.  
9. Chapter 6 numbering: **6.1 Critical Evaluation, 6.2 Limitation, 6.3 Recommendation**.  
10. Primary SDG is **9**, not 4.  
11. UAT questionnaire wording says “website” in the guidelines sample — adapt to **desktop application** for this project.  
12. Prefer **“final Sem 2 implementation”** or a **new release tag you actually ship** over hard-coding **0.1.2** unless the report explicitly discusses that GitHub release artifact.

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
| `docs/RELEASE.md` | Packaging and release process |
| `PROJECT_SUMMARY.md` | Phase history (may lag workspace model) |
| `evaluation/EVIDENCE.md` | Eval checklist status |
| `evaluation/uat_questionnaire.md` | UAT instrument |
| `evaluation/job_router_report.md` | Custom router eval (accuracy, tier split) |
| `scripts/train_job_router.py` | Train custom classifier |
| `auth/README.md` | Auth + Postgres setup |
| `auth/src/migrate-devices.ts` | Custom `devices` table |
| `docs/RELEASE.md` | Packaging (sidecar bundle, Tauri release) |
| `sidecar/server.py` | Full HTTP/SSE API surface |
| `desktop/src/lib/api.ts` | Frontend API client + stream types |
| `desktop/src-tauri/src/lib.rs` | Tauri IPC + sidecar spawn |
| `.github/release_notes/v0.1.2.md` | Latest release highlights |

---

## 16. Custom trained model — Manager job router (Ch4 + Ch5)

**This is a real custom ML component** — not foundation-model fine-tuning, but a **project-trained classifier** shipped in the release bundle. Give it its own subsection in Ch4.5 (implementation) and Ch5.3 (evaluation).

### What it is

A lightweight **local job router** that predicts which Manager skill to dispatch (`file` | `answer` | `research` | `refuse`) from the user’s natural-language message plus routing context. It sits in the multi-tier pipeline **after rule-based routing** and **before** the Gemini Flash-Lite LLM router, with `apply_policy` as the final safety clamp.

### Algorithm

| Component | Detail |
|-----------|--------|
| Features | User text + enriched tokens: `claims=c0|c1|c3`, `attach`, `phase=empty|seed|ready`, `qlen=short|medium|long`, `qmark` (`features.py`) |
| Vectorizer | TF-IDF, 1–3 word n-grams, max 1,200 features |
| Classifier | Logistic regression, balanced class weights, per-class confidence thresholds |
| Classes | `file`, `answer`, `research`, `refuse` |
| Inference | Pure Python in `local_model.py` — no sklearn at runtime; weights serialized to JSON |
| Min confidence | 0.42 default; tuned per class on validation split |

### Training data & scripts

| Artifact | Path |
|----------|------|
| Labeled corpus | `data/job_router/labeled_turns.json` — **521** hand-curated / expanded turns |
| Class distribution | research 306, answer 96, refuse 72, file 47 |
| Train script | `scripts/train_job_router.py` |
| Expand / relabel | `scripts/expand_job_router_dataset.py`, `scripts/relabel_job_router_empty_ask.py` |
| Eval script | `scripts/eval_job_router.py` |
| Bundled weights | `data/job_router/model.json` |
| Train metrics | `evaluation/job_router_train_metrics.json` (held-out test macro-F1 ≈ **0.937**) |
| Eval report | `evaluation/job_router_report.md`, `evaluation/job_router_report.json` |

### Reported performance (`evaluation/job_router_report.md`)

| Baseline | Accuracy | Macro-F1 |
|----------|----------|----------|
| Regex-only | 0.867 | 0.786 |
| **Local model (custom)** | **1.000** | **1.000** |
| Gemini JSON router | 0.867 | 0.786 |
| **Full pipeline** (rules + local + policy) | **0.956** | **0.953** |

Pipeline tier distribution on 518 eval turns: **rule 86%**, **local model 14%**, fallback 0%, Gemini 0% (local model + rules handle almost all routing without cloud LLM cost).

### Why it matters for the FYP

- Demonstrates **custom ML beyond calling APIs** — dataset curation, train/eval loop, shipped artifact  
- Reduces latency and cloud dependency for routine routing (aligns with survey hybrid/local preference)  
- Pairs with deterministic `policy.py` so the model cannot violate safety invariants (refuse on thin notes-intent, attachments → file, etc.)  
- Objective 1 / FR7: intelligent dispatch without exposing LangGraph nodes as UI agents

### Ch4 screenshot / diagram suggestions

- Confusion matrix from eval report  
- Pipeline diagram showing rule → **local model** → LLM fallback → policy  
- Short code excerpt from `train_job_router.py` or `local_model.py` (Appendix F)

### Ch5 test cases

| TC | Component | Input | Expected |
|----|-----------|-------|----------|
| TC-JR1 | Job router | “According to my notes…” + c0 | `refuse` or low confidence → policy |
| TC-JR2 | Job router | Research phrasing + ready phase | `research` |
| TC-JR3 | Job router | Attachment present | `file` (bypass model) |
| TC-JR4 | `test_job_router.py` | Held-out labeled turns | Macro-F1 ≥ threshold |

---

## 17. Auth service & PostgreSQL database (Ch4)

**This is a real relational database** — separate from Chroma and the vault filesystem. The report should include it in **§4.3 Database Design** (auth is the SQL database; vault persistence is filesystem + Chroma).

### Architecture

```
Desktop (Settings → Account)
    │  email OTP via Better Auth client (desktop/src/lib/auth/)
    ▼
auth/ service (Node, port 3000)
    │  Better Auth + emailOTP plugin
    ▼
PostgreSQL 16
    ├── Better Auth tables (user, session, verification, account, …)
    └── devices (custom — migrate-devices.ts)
```

**Critical privacy line:** Auth DB holds **identity only**. Personal notes, claims, Chroma embeddings, and research reports stay **on-device** in the vault. Cloud Watch uses auth sessions to resolve the user but does not store the vault in Postgres.

### Stack

| Layer | Choice |
|-------|--------|
| Service | `auth/` — Node + TypeScript |
| Auth library | [Better Auth](https://www.better-auth.com/) with `emailOTP` + `bearer` plugins |
| Driver | `pg` (`Pool`) — `auth/src/auth.ts` |
| Local DB | Docker Compose `postgres:16-alpine` on **port 5433**, database `nous_auth` |
| Production option | Neon Postgres (pooled `DATABASE_URL`) + Render deploy — see `auth/README.md`, `auth/DEPLOY_PATH_A.md` |
| Email | Resend API (production) or stdout OTP in dev (`AUTH_DEV_LOG_OTP=1`) |

### Schema (document in report)

**Better Auth managed** (via `npm run migrate`):

- `user` — email, name, emailVerified, createdAt, …  
- `session` — token, userId, expiresAt, ipAddress, userAgent, …  
- `verification` — OTP codes (hashed via `storeOTP: "hashed"`)  
- `account` — linked auth providers (if any)

**Custom table** (`auth/src/migrate-devices.ts`):

```sql
devices (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,      -- FK to Better Auth user
  device_id TEXT NOT NULL UNIQUE,
  public_key TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ
)
CREATE INDEX devices_user_id_idx ON devices (user_id);
```

Purpose: register desktop instances per user for **Cloud Watch** sync / device-aware brief delivery. Not used for vault storage.

### Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| * | `/api/auth/*` | Sign-in, OTP verify, session (Better Auth) |
| GET | `/internal/session` | Sidecar/Cloud Watch session resolution (`X-Internal-Secret`) |
| POST | `/devices/register` | Register desktop device |
| GET | `/devices/me` | List user devices |
| GET | `/health` | Health check |

### Desktop integration

- `desktop/src/lib/auth/client.ts`, `auth-session.svelte.ts`, `auth-prefs.ts`  
- `VITE_AUTH_URL` in `desktop/.env` (e.g. `http://localhost:3000` dev, Render URL prod)  
- Settings → Account UI for email OTP sign-in  
- Root `.env`: `AUTH_URL`, `AUTH_INTERNAL_SECRET` (must match `auth/.env` for Cloud Watch)

### Ch4 content to include

- ER diagram: `user` → `session`, `user` → `devices`  
- Screenshot: Settings → Account OTP flow  
- Screenshot or `docker compose ps` showing local Postgres  
- Table comparing **three stores**: vault filesystem, Chroma, auth Postgres (what each holds)  
- Note: optional for offline-only use; required for Cloud Watch / cross-device identity

### Ch5 test cases

- `desktop/src/lib/auth/auth-prefs.test.ts` — client prefs  
- Manual UAT: sign in → session persists → Cloud Watch status (if enabled)  
- `test_cloud_watch*.py` — session resolution against auth (if run with auth up)

---

## 18. Backend architecture (Ch4 — full stack)

Use this section for **backend / sidecar / AI core** implementation detail. The product has **four backend layers**: Tauri Rust shell → Python sidecar → `second_brain` package → optional `auth/` + `cloud-watch/` services.

### 18.1 Layer overview

| Layer | Tech | Path | Role |
|-------|------|------|------|
| **Presentation host** | Tauri 2 (Rust) | `desktop/src-tauri/` | Window, IPC, spawn/kill sidecar, vault FS watch, PDF bytes |
| **API gateway** | FastAPI + Uvicorn | `sidecar/server.py` | HTTP + SSE on `127.0.0.1:8765`; CORS `*` for webview |
| **AI core** | Python 3.12 | `src/second_brain/` | Manager, LangGraph, RAG, memory, ingest, tools |
| **Identity** | Node + Better Auth | `auth/` | Email OTP, Postgres sessions, `devices` table |
| **Hosted Watch** | FastAPI + SQLite | `cloud-watch/` | Cron briefs, sealed BYOK keys (optional) |

### 18.2 Tauri Rust shell (`desktop/src-tauri/src/lib.rs`)

**Lifecycle:** On app setup → spawn Python sidecar → expose URL via `get_sidecar_url`. On `RunEvent::Exit` → kill child process.

**Dev vs release:**

| Mode | Python | Roots |
|------|--------|-------|
| Dev | Repo `.venv/bin/python` + `sidecar/server.py` | `NOUS_DATA_DIR` = repo root |
| Release | Bundled `sidecar-bundle/venv` + `sidecar/server.py` | `NOUS_BUNDLE_ROOT` = bundle resources; `NOUS_DATA_DIR` = app data dir |

Release sets `FASTEMBED_CACHE_PATH` for bundled embeddings.

**Tauri commands (IPC):**

| Command | Purpose |
|---------|---------|
| `get_sidecar_url` | Base URL for `api.ts` |
| `get_project_root` | Dev vault root |
| `restart_sidecar` | Recover crashed sidecar |
| `read_vault_file_bytes` / `read_vault_file_base64` | PDF/note bytes (sandboxed under vault) |
| `start_vault_watch` / `stop_vault_watch` | Filesystem notify → `vault-file-changed` event |
| `copy_dir_into_vault` | Import folder into topic vault |

**Tauri plugins:** `shell`, `dialog`, `fs`, `opener` (`Cargo.toml`).

**Vault watcher:** Rust `notify` crate watches topic folders recursively; emits events to Svelte; UI debounces and triggers sidecar ingest.

### 18.3 Sidecar (`sidecar/server.py`)

- **Single-module API** (~1,650 lines) — no APIRouter split; all routes in one file.
- **Startup:** `@app.on_event("startup")` starts daily-review scheduler thread (`sidecar/scheduler.py`).
- **Middleware:** `CORSMiddleware` — localhost webview → sidecar.
- **Path setup:** Inserts `src/` on `sys.path`; imports `second_brain` + `sidecar.runs` + `sidecar.scheduler`.
- **Settings API:** `GET/PUT /api/settings` — user-editable env persisted to `DATA_ROOT/.env`. **Hidden keys** (never in UI): `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `NOUS_NVIDIA_API_KEY`, `CLOUD_WATCH_URL`, router model keys.

### 18.4 Complete API route map

| Group | Methods | Paths |
|-------|---------|-------|
| Health | GET | `/health`, `/api/status`, `/api/mcp/status`, `/api/agent/defaults` |
| Router | POST | `/api/act`, `/api/manager/turn`, `/api/session-title` |
| Ask / Teach | POST | `/api/chat`, `/api/query`, `/api/digest`, `/api/memory/merge` |
| Digests / review | GET/POST | `/api/digest/today`, `/api/digests`, `/api/review/status`, `/api/review/plan`, `/api/review/run-now` |
| Research | POST/GET/DELETE | `/api/research`, `/api/research/plan`, `/api/research/execute`, `/api/research/stream`, `/api/research/runs/{id}` |
| Goals | POST | `/api/goals/stream` |
| Watches | GET/POST | `/api/watches`, `/api/watches/{id}`, `update`, `move`, `delete`, `promote`, `run`, `stream`, `steer` |
| Ingest | POST | `/api/ingest`, `/api/ingest/file` |
| Vault | POST | `/api/vault/search`, `/api/vault/related` |
| Settings | GET/PUT | `/api/settings` |
| Cloud Watch proxy | GET/POST/PUT | `/api/cloud-watch/sync`, `pull`, `sync-all`, `delegate`, `status`, `llm`, `llm/sync` |

Client: `desktop/src/lib/api.ts` — typed wrappers for all of the above.

### 18.5 SSE / streaming contract

**Transport:** HTTP POST → `text/event-stream` body (`data: {json}\n\n`). Client uses **fetch + ReadableStream** (not `EventSource`).

**Stream endpoints:** `/api/research/stream`, `/api/research/execute`, `/api/goals/stream`, `/api/watches/stream`.

**Event types** (`ResearchStreamEvent` in `api.ts` — client ignores unknown types):

| Type | Purpose |
|------|---------|
| `stage` | Legacy step label (node, step, detail) |
| `agent_status` | Live node status (running / done / error) for Mission Control |
| `plan` | Planner output + retrieval queries (plan review HITL) |
| `artifact` | Retrieval stats, analysis excerpt |
| `critique` | Verifier output, approval flag, structured critique, history entry |
| `memory` | Recall/write phases, confidence, report path |
| `goal_pass` / `goal_status` | Multi-pass goal loop progress |
| `watch_brief` | Watch run brief ready |
| `result` | Final payload |
| `done` / `error` | Stream termination |

### 18.6 Research run registry (plan review HITL)

**File:** `sidecar/runs.py`

- In-memory `RUNS` registry for plan → approve → execute flow.
- Statuses: `pending_approval` → `executing` → `completed` | `cancelled` | `expired`.
- **TTL:** 30 minutes per run.
- **Concurrency:** `MAX_CONCURRENT_RUNS = 4`; project-scoped single-flight for auto runs.
- Daily review scheduler shares this lock (`try_begin_auto` / `end_auto`).

### 18.7 Config & environment layering

**File:** `src/second_brain/config.py`

Load order (later overrides earlier):

1. `BUNDLE_ROOT/operator.env` — build-time defaults (bundled NVIDIA key, etc.)  
2. `DATA_ROOT/.env` — user Settings UI writes here  
3. Dev checkout `.env` — only when `DATA_ROOT == PROJECT_ROOT`

**Split roots:**

- `NOUS_BUNDLE_ROOT` — code, sidecar bundle, job-router model, operator.env  
- `NOUS_DATA_DIR` — vault (`data/documents/`), Chroma (`data/chroma/`), user `.env`

**Notable knobs:** `LLM_PROVIDER` / `LLM_MODEL` / `LLM_FAST_MODEL` / `LLM_FALLBACK_MODEL`; `EMBEDDING_PROVIDER`; `MAX_REVISIONS`; `PLAN_REVIEW_DEFAULT`; `AUTO_MEMORY` / `AUTO_RECALL`; `DEEP_ASK_*`; `HYBRID_RRF_K`; chunk size 1000/200; `DAILY_REVIEW_*`; `WATCH_MAX_PASSES`; `ENABLE_MCP`.

### 18.8 LLM provider abstraction

**File:** `src/second_brain/memory/llm.py`

| Provider | Notes |
|----------|-------|
| `nvidia` | Default in release; `NOUS_NVIDIA_API_KEY` bundled fallback |
| `groq`, `openrouter`, `ollama`, `openai`, `xai`, `openai_compatible` | BYOK via Settings |

**Roles:** `main` (planner, synthesizer) vs `fast` (Ask, analyst, verifier) via `LLM_FAST_MODEL`.

**Resilience:** `invoke_llm` retries 429/502/503 (parse retry-after or exponential backoff) → fallback model (`LLM_FALLBACK_MODEL`).

### 18.9 RAG & retrieval pipeline

| Stage | Module | Detail |
|-------|--------|--------|
| Ingest | `ingestion/pipeline.py` | RecursiveCharacterTextSplitter; metadata `chunk_index`, `source_hash`, `ingested_at`; Chroma upsert |
| Section summaries | `ingestion/sections.py` | Optional per-section embed summaries |
| Personal retrieve | `memory/retriever.py` | Dense Chroma + BM25 → **RRF merge** (`HYBRID_RRF_K=60`); optional rerank; `project_path` scope + `also_project_paths` |
| Hybrid research | `agents/hybrid_retriever.py` | Tagged queries `[personal]\|[web]\|[arxiv]`; scope allow-list; arXiv reformulation on empty |
| Ask | `rag/chain.py` | Thin-memory refuse; source chips |
| Deep Ask | `rag/ask_depth.py` | Map-reduce over long corpora; study cache; claim-first; source pinning (`DEEP_ASK_*` flags) |
| Embeddings | `memory/embeddings.py` | fastembed / Ollama / OpenAI-compatible; `reindex_required` on provider change |

### 18.10 Scheduler & background jobs

**File:** `sidecar/scheduler.py` + `agent/daily_review.py`

- Background thread; gated by `DAILY_REVIEW_ENABLED` and scheduled hour.
- Catch-up only **after** scheduled hour (avoids early-launch LLM spend).
- Skips when research lock busy; retries every 15 min.
- Watch local runs while app open; Cloud Watch handles asleep-Mac cron (optional).

### 18.11 Cloud Watch service (optional fourth backend)

**Dir:** `cloud-watch/`

| Piece | Detail |
|-------|--------|
| API | `app.py` — FastAPI; validates Bearer via `AUTH_URL/internal/session` + `AUTH_INTERNAL_SECRET` |
| Store | `store.py` — **SQLite** (`cloud-watch.db`); watches per user |
| BYOK | Sealed provider keys (HMAC + XOR with `CLOUD_WATCH_SECRET`) |
| Worker | `worker.py` — cron-due watches; temporarily swaps process env to user's provider/key; default TZ Asia/Singapore |
| Desktop path | Sidecar **proxies** `/api/cloud-watch/*`; `api.ts` auto-injects Bearer from Better Auth session |

Vault content never uploaded — only watch instructions + brief metadata + encrypted API keys.

### 18.12 Backend Ch4 diagram suggestions

- **Deployment diagram:** Tauri → sidecar → second_brain → Chroma/Tavily/arXiv; optional auth + cloud-watch  
- **Sequence diagram:** POST `/api/manager/turn` → dispatch → POST `/api/research/stream` → SSE events → write-back  
- **Component diagram:** sidecar modules vs `second_brain` packages  
- **ER diagram:** auth Postgres (§17) + note Cloud Watch SQLite is separate  

---

## 19. Frontend architecture (Ch4 — full stack)

Use this section for **desktop UI** implementation. Nous is a **Tauri-hosted SPA** (not a traditional web app with SSR).

### 19.1 Build & routing

| Piece | Detail |
|-------|--------|
| Framework | Svelte 5 + SvelteKit |
| Adapter | `@sveltejs/adapter-static` — SPA mode |
| Routing | `routes/+layout.ts`: `ssr = false`, `prerender = true`; essentially single-page (`+page.svelte` → `AppShell`) |
| Bundler | Vite 6; `base: "./"` for Tauri custom protocol |
| Dev server | Port **1420** (strict); HMR **1421** when `TAURI_DEV_HOST` set |
| Version | **0.1.2** aligned across `package.json`, `Cargo.toml`, `tauri.conf.json` |
| Bundle ID | `com.tp068819.nous`; window 1400×900, overlay titlebar |

### 19.2 State management (Svelte 5 runes)

All app state uses **class stores with `$state` / `$derived` / `$effect`** — not legacy Svelte stores.

| Store | File | Responsibility |
|-------|------|----------------|
| `app` | `stores/app.svelte.ts` | View modes (agent/document/watch/memory); sheets; settings tab; home navigation |
| `workspace` | `stores/workspace.svelte.ts` | Active topic path, pins, vault refresh, knowledge panel, watcher status |
| `assistant` | `stores/assistant.svelte.ts` | Chat sessions (`localStorage` `sb-agent-sessions-v2`), turns, research progress, step list |
| `tabs` | `stores/tabs.svelte.ts` | Open session + document tabs (`sessionStorage` `sb-open-tabs-v1`) |
| `memory` | `stores/memory.svelte.ts` | Memory mode: search, topic filter, type toggles, selection (sidebar ↔ graph) |
| `connection` | `stores/connection.svelte.ts` | Sidecar health poll, embedding reindex status, Cloud Watch sync/pull |
| `watchRuns` | `stores/watchRuns.svelte.ts` | Watch run UI state |
| `authSession` | `auth/auth-session.svelte.ts` | Better Auth session (separate from vault) |

**Session model:** One `assistant` session per workspace (`ensureChannelSession`); `projectPath` binds chat to vault folder.

### 19.3 Component hierarchy

```
AppShell.svelte
├── Sidebar OR MemorySidebar (mode-dependent)
│   ├── WorkspaceChatTree — flat #topic list, + new workspace
│   └── TopicPicker — scope filters
├── PaneResizer
├── main column
│   ├── titlebar drag region (Tauri Overlay)
│   ├── CommandPalette (⌘K)
│   ├── AppSheet — Settings / Ingest / Account sheets
│   └── mode content:
│       ├── ChatHome → ChatHeader + AgentPane [+ DocumentView peek]
│       │   ├── ChatLanding (offline / no key / bootstrap)
│       │   ├── ChatThread + ComposerDock
│       │   ├── AgentRunBlock (Remembered, status)
│       │   └── AgentWorkPanel + RunDetailsDrawer
│       ├── WatchHome / WatchEditor / WatchList
│       ├── MemoryHome → GraphView (force-graph canvas)
│       └── DocumentView — full note editor
├── components/mission/* — MissionStage, PlanReview, SelfCritique, LiveActivity, AgentGraph
└── KnowledgePanel (conditional vault browse)
```

**Keyboard shortcuts (AppShell):** ⌘K palette, ⌘B sidebar, ⌘N new chat, etc.

### 19.4 API client layer

**File:** `desktop/src/lib/api.ts`

- Base URL from Tauri `get_sidecar_url()` (fallback `http://127.0.0.1:8765`).
- Typed request/response interfaces for all endpoints.
- **SSE helpers:** `researchStream`, `executeResearch`, `goalStream`, `watchStream` — parse `data:` lines into `ResearchStreamEvent`.
- **Cloud Watch:** auto-attaches `Authorization: Bearer` from auth session for `/api/cloud-watch/*`.
- **AbortController:** per-stream cancel (client-side; server may continue until improved).

### 19.5 Assistant layer (client-side routing hints)

Client heuristics **complement** server `take_turn` — they do not replace it.

| Module | Role |
|--------|------|
| `assistant/intent.ts` | Teach vs explain vs lookup; note-dump detection (≥800 chars); auto-research hints |
| `assistant/session-jobs.ts` | Per-session `AbortController`; max **4 concurrent research** streams; pending-turn lock |
| `assistant/composer-skills.ts` | Composer skill chips (Teach, Research, etc.) |
| `assistant/channel-agents.ts` | Empty-workspace onboarding copy + placeholders |
| `assistant/channel-empty.ts` | Pure emptiness check for vault |
| `assistant/workspace-chats.ts` | Multi-session binding to one workspace |
| `assistant/transparency.ts` | Status-line copy for research stages |

### 19.6 Vault layer (client)

| Module | Role |
|--------|------|
| `vault/watcher.ts` | Listen for Tauri `vault-file-changed`; UI debounce **250ms**; auto-ingest debounce **2s** |
| `vault/watcher-skip.ts` | Skip `memory/**`, briefs, watches, research (mirror backend skip-list) |
| `vault/vault-graph.ts` + `graph-data.ts` | Build graph nodes/edges from vault tree |
| `vault/graph-peek.ts` | Selection neighbours for MemorySidebar |
| `vault/search-dispatch.ts` | Fuse.js fuzzy (client) vs sidecar semantic search |
| `vault/notes.ts`, `markdown.ts`, `wikilinks.ts` | Note I/O, wikilink resolution |
| `vault/pdf.ts` + `PdfViewer` | pdfjs-dist; bytes via Tauri `read_vault_file_*` |

**Graph node types:** `note`, `research`, `learning`, `digest`, `topic` — colours in `memory.svelte.ts` `GRAPH_TYPE_STYLE`.

### 19.7 Editor (TipTap)

| Piece | Detail |
|-------|--------|
| Component | `components/editor/NoteEditor.svelte` |
| Stack | TipTap 3 + StarterKit + custom **WikiLink** extension |
| Serialization | Markdown ↔ HTML via **marked** + **turndown** |
| Session | `editor/note-editor-session.ts` — view mode, split ratio prefs |
| Frontmatter | Preserved on save |

### 19.8 Research UI

| Component | Role |
|-----------|------|
| `AgentWorkPanel.svelte` | Live mission panel beside chat |
| `RunDetailsDrawer.svelte` | Run trace, critique history |
| `components/mission/AgentGraph.svelte` | Visual graph of pipeline nodes |
| `components/mission/PlanReview.svelte` | HITL plan approve/edit before execute |
| `components/mission/SelfCritique.svelte` | Verifier iteration display |
| `lib/research/render.ts` | Report markdown + citation `[n]` rendering |
| `lib/research/status-copy.ts` | Human-readable stage labels |

### 19.9 Theme & appearance

| Piece | Detail |
|-------|--------|
| Palettes | **nous**, **ember**, **mono**, **lilac** — `theme/palette-registry.ts` + `theme/palettes/*.css` |
| Mode | light / dark / system — `theme/theme-prefs.ts`, `apply-theme.ts` |
| Fonts | `@fontsource/inter`, `@fontsource/jetbrains-mono` |
| Persistence | `localStorage` via theme prefs |

### 19.10 Auth UI (frontend)

| File | Role |
|------|------|
| `auth/client.ts` | Better Auth client (`VITE_AUTH_URL`) |
| `auth/session.ts` | Session token helpers |
| `auth/auth-session.svelte.ts` | Reactive sign-in state |
| Settings → Account | Email OTP flow; Cloud Watch enablement |

### 19.11 Packaging (frontend + shell)

Release pipeline (`scripts/package_release.sh`, `docs/RELEASE.md`):

1. Build Svelte static assets → `desktop/build/`  
2. Bundle Python venv + `sidecar/` → `sidecar-bundle/`  
3. Include `operator.env`, job-router `model.json`, fastembed cache path  
4. Tauri packages `.dmg` (macOS) / `.exe` (Windows)  
5. User data lives **outside** bundle in Application Support  

### 19.12 Frontend Ch4 screenshot checklist

1. AppShell with sidebar + chat  
2. Composer with skill chips  
3. Research Mission Control / agent graph  
4. Plan review modal  
5. Memory mode — sidebar + force-graph  
6. Watch editor  
7. TipTap note editor + document peek  
8. Settings (models, appearance, account)  
9. Theme palette switch (incl. Lilac)  

---

## 20. Placeholders remaining for final FYP submission

Already known from IR/proposal (do not treat as missing):  

- [x] Locked FYP title  
- [x] Supervisor Mr. Amad Arshad; second marker Ms. Mary Ting  
- [x] Survey n=62 + analysis + RTM (carry into Ch3; refresh figures from IR)  
- [x] Ethics forms / PPF / Sem 1 log sheets / Sem 1 Gantt / Turnitin pages exist in IR appendices — **re-include / update** for final report as required  
- [x] Shipped desktop app Nous 0.1.2  
- [x] Custom job router model trained + bundled (`model.json`, eval report)  
- [x] Auth service + Postgres schema (Better Auth + `devices`)  
- [x] Full frontend + backend architecture documented (§18–§19)  

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

*End of writer context. Prefer LOCKED IR/proposal fields for identity/aim/objectives/SDG/survey; prefer `CURRENT_STATUS.md` and the **current local working tree** for what the software actually does — not necessarily the last GitHub release (v0.1.2). Backend detail: §18. Frontend detail: §19.*
