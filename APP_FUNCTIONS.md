# Nous — what to explain (app functions)

Use this when presenting or recording a demo. Speak the **Explain** lines; use **Show** as on-screen cues.

**One-liner:** Nous is a local-first second brain. Each **channel** is a topic you own. You talk there; Teach, Ask, Research, and Scheduled Research share that topic’s memory — and research can write back into it.

**Tagline:** Research that remembers *you*.

---

## Mental model (say this first)

| Concept | Meaning |
|--------|---------|
| **Channel** | A lifelong topic folder (e.g. `#Coffee`, `#FYP`) with its own vault memory |
| **Chat** | One conversation thread bound to that channel |
| **Manager** | Invisible router: turns your message into Teach / Ask / Research / Scheduled Research |
| **Memory** | Durable claims and notes for *that* channel only — not a global chat history |

**Do not explain it as:** “ChatGPT with a sidebar,” separate agents you hire, or pipeline roles (Planner, Retriever…) as people in the UI. Those roles only appear as status lines *inside* Research.

---

## 1. Channels (topics)

**What it does:** Organises knowledge by topic. Each channel is a vault folder; memory stays isolated to that topic.

**Explain:**
> “A channel is a topic, not a random chat. Everything I teach or research here stays under Coffee — it doesn’t bleed into my FYP notes.”

**Show:** Sidebar channel list (`#Name`), open one channel, composer: “Message this channel…”

---

## 2. Teach (Remember / file)

**What it does:** Turns notes or pasted dumps into durable **memory claims** for the channel (`origin=dump`).

**Explain:**
> “Files on disk are not memory yet. Teach digests my notes into claims this channel can recall. That’s private knowledge I own — not a one-off attachment.”

**Show:** Paste notes / Teach chip / Remember → **Remembered** card → manager line that you can Ask about them.

**Key point:** Files ≠ Ask memory until Remembered.

---

## 3. Ask (answer)

**What it does:** Answers from **this channel’s** memory (personal RAG / recall). Prefers settled claims; can surface contested disagreements honestly. Does not invent from thin memory (refuse).

**Explain:**
> “I’m asking *my* notes — not a generic web essay. Sources and citations show where the answer came from.”

**Show:** Question grounded in taught notes → answer in-thread → source chips / citations.

**Example prompt:**
> According to my notes, what do I care about when making espresso at home besides just a strong taste?

---

## 4. Research (multi-agent)

**What it does:** Runs a LangGraph pipeline in the same channel: **Planner → Retriever → Analyst ⇄ Verifier → Synthesizer**. Hybrid retrieval: personal vault first, plus web / arXiv when useful. Can save a report and write claims back into channel memory.

**Explain:**
> “For a real goal, Research plans, retrieves from my vault and the web, checks itself, then synthesises a report — still in this channel. Findings can write back so next time Ask isn’t starting from zero.”

**Show:** Research goal in composer → muted status lines for agents → report with `[n]` citations → open report / remembered claims / Past research.

**Example prompt:**
> Looking at my notes, how do I make espresso at home? Cover grind and dose, steaming milk, and what I’d buy next?

**What to stress:** Architectural self-critique (verifier) + write-back — not “we can also search the web.”

---

## 5. Scheduled Research (standing briefs)

**What it does:** Recurring research on the channel topic. Produces briefs (while the app is open; optional cloud path when the Mac is asleep via Settings → Account email sign-in). Schedule-origin claims can expire; they must not silently overwrite Teach dumps.

**Explain:**
> “Scheduled Research keeps this topic current over time — a morning-style brief filed back into the same channel memory.”

**Show:** Scheduled Research nav → create/edit focus → Run → brief ready / history.

---

## 6. Memory (knowledge view)

**What it does:** Browse the knowledge graph / channel memory surface — not a separate chat agent.

**Explain:**
> “Memory is where I see what this mind already believes for a topic — claims, structure, links — not another chatbot.”

**Show:** Memory nav → graph / claims for the open topic.

---

## 7. Supporting surfaces (mention briefly)

| Surface | Function |
|--------|----------|
| **Document peek** | Read notes beside chat without leaving the thread |
| **Settings** | Models, connectors, appearance, knowledge / research prefs |
| **Ingest / Add docs** | Bring folders into the vault (index); Teach still needed for claim memory |
| **Command palette (`⌘K`)** | Fast actions (e.g. Remember topic notes) |
| **Refuse** | Thin memory → honest “I don’t know from your notes” instead of hallucinating |

---

## Differentiation (closing lines)

Use one of these:

1. **Vs flagship chat AIs:** They are general assistants. Nous is a **local-first mind for your knowledge** — knowledge you own, research that uses it, results that update it.
2. **Loop:** Teach → Ask → Research → write-back → Ask again richer.
3. **Not the differentiator:** Web search alone. The differentiator is **lifelong local memory + multi-agent research with self-critique + hybrid personal-first retrieval + write-back**.

---

## Demo order (recommended)

1. Open a channel → mental model (10s)  
2. Teach → Remembered  
3. Ask from notes + sources  
4. Research → status lines → report → write-back  
5. (Optional) Scheduled Research brief  
6. Close with differentiation one-liner  

**Avoid first:** Empty library + web-only question; IDE/file-manager tour; treating pipeline agents as sidebar “members.”

---

## Examiner / viva one-liner

> Flagship chat AIs are general assistants. **Nous** is a **local-first mind for your knowledge**: knowledge you own, multi-agent research that uses it, and results that update it over time.
