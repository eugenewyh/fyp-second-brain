# User Acceptance Testing (UAT) Questionnaire — Round 2

**Project:** Nous — Graph-Based Multi-Agent System  
**Student:** Wong Yan Hao (TP068819)  
**Round:** 2 (Aug 2026)  
**Target participants:** 5–8 knowledge workers or students  
**Duration:** ~20–25 minutes per session  
**Demo topic:** Home coffee / espresso (`evaluation/demo/Coffee` → workspace **Coffee**)

---

## Pre-test (1 min)

1. Have you used AI tools for research or note-taking before? (Yes / No)
2. Briefly describe your main use case (student / developer / researcher / other):
3. Did you take part in an earlier Nous UAT? (Yes / No)

---

## Setup (facilitator, before participant arrives)

```bash
# From repo root
cp -R evaluation/demo/Coffee data/documents/Coffee
# Optional: python scripts/ingest.py --input data/documents/Coffee
```

1. Start sidecar + desktop app; confirm AI provider is connected (Settings).
2. Open workspace **Coffee** in the sidebar (expand with the chevron).
3. Prefer a **clean chat** for Task 1: **+** on Coffee → **New Chat** (centered composer).
4. Notes may already exist under `Coffee/notes/`, but **Ask only uses claims** under `Coffee/memory/claims/`. Task 1 makes participants Teach first so they see files ≠ memory.

---

## Task 1: Teach → Ask (memory loop) (6–7 min)

**Part A — Teach / Remember**

Use the **Teach** chip (or Shift+Tab until Teach), then paste `evaluation/demo/TEACH_DUMP.txt` and send (or ⌘K → Remember topic notes if the dump file is awkward).

You should see a **Remembered** card, then a manager line like *“Remembered N ideas into #Coffee memory. Ask me about them when you’re ready.”*

**Part B — Ask from memory**

Stay in the same chat (or keep Coffee). Send:

> According to my notes, what do I care about when making espresso at home besides just a strong taste?

| # | Statement | Strongly Disagree (1) | Disagree (2) | Neutral (3) | Agree (4) | Strongly Agree (5) |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| Q1 | Teaching / Remember made it clear notes were filed into memory | | | | | |
| Q2 | After Remember, Ask answered from my notes (not a generic chat reply) | | | | | |
| Q3 | The sources / citations helped me trust the answer | | | | | |
| Q4 | The response time was acceptable | | | | | |
| Q5 | Starting in the centered New Chat composer felt clear | | | | | |

---

## Task 2: Research in the same workspace (8–10 min)

**Instructions:** Stay in **Coffee**. Prefer a **new chat** under Coffee (sidebar **+**), or continue in the same thread. Tap the **Research** chip (or Shift+Tab until Research), then send:

> Looking at my notes, how do I make espresso at home? Cover grind and dose, steaming milk, and what I’d buy next.

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| Q6 | The report was well-structured and easy to read | | | | | |
| Q7 | Citations were present and useful | | | | | |
| Q8 | Gaps / honesty about what the notes don’t cover felt useful | | | | | |
| Q9 | Progress / status while running was understandable | | | | | |
| Q10 | I would use this instead of a single ChatGPT-style query for this kind of research | | | | | |

---

## Task 3: Parallel chats (3 min) — *new in Round 2*

**Instructions:** While a long answer or research is running (or after Task 2), create a **second chat** under Coffee (sidebar **+**). In that chat, send a short Ask:

> What’s my weekday morning coffee routine according to my notes?

Then switch back to the first chat.

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| Q11 | I could tell the two chats apart in the sidebar | | | | | |
| Q12 | Messages stayed in the correct chat (no mix-up) | | | | | |
| Q13 | Chat titles after sending made sense (not just “Coffee”) | | | | | |

---

## Post-test (2 min)

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| Q14 | Overall, I am satisfied with Nous | | | | | |
| Q15 | I would recommend this tool to a colleague | | | | | |

**Open feedback:** What was confusing? What would you change?

---

## Facilitator notes

- Ensure the AI service is ready (OpenRouter / Groq / etc.) before the session.
- **Files on disk ≠ Ask memory.** Claims must exist under `memory/claims/` or Ask will refuse. Task 1 forces Teach → Ask so participants experience that loop.
- After Teach, point at the digest card + manager nudge (“Ask me about them…”) before Part B.
- Workspace header shows **Coffee** (no `#`). Sidebar still uses `#` + Hash icon for the folder.
- New chat: centered tall composer → after first send, bottom dock.
- Multiple chats per workspace are supported; deleting the last chat leaves “No chats yet” (does not auto-recreate).
- Task 1 = Teach → Ask. Task 2 = Research / synthesis. If Task 2 routes to Ask, force **Research** chip.
- Expected themes: sweet/balanced over bitter-strong, burr grinder > machine upgrade, 18g→36g, milk 60–65°C, filtered water, next buy = better grinder / naked portafilter.
- Record time-to-first-token (Task 1 Ask) and time-to-report (Task 2).
- Watch for parallel-chat leaks (Task 3) — Round 2 regression check.
