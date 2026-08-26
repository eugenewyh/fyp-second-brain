# Nous — workflow demo script

Step-by-step script matching the actual UI flow: what you click, what you type, what appears. No pitch/opening — this is a pure "here's how you use it" walkthrough. Read the quoted lines aloud; do the bracketed actions on screen.

---

## 1. Create a workspace

**[Action: sidebar → `+` → "New workspace" opens]**

> "To start, I create a workspace. A workspace is a topic — everything I teach or research under it shares one memory."

**[Action: type a name, e.g. "Coffee"; optionally add a folder or paste a short idea in the Idea box; click Create]**

> "I give it a name, optionally add a folder of existing notes, and a one-line idea of what it's for. That idea gets saved as `IDEA.md` — it's the topic's intent, not a throwaway prompt."

**[Result: a new chat tab opens automatically, bound to this workspace]**

---

## 2. Land on the empty chat

**[Screen: chat landing, "seed" phase — title "Give Nous something to remember", only a Teach chip visible]**

> "Because this workspace is empty, it only offers one thing to do: Teach. Ask and Research stay locked until there's something in memory — it won't pretend to know things it doesn't."

**[Action: point at composer placeholder — "Teach Nous something about this workspace…"]**

---

## 3. Teach — give it memory

**[Action: click the Teach chip, or type directly into the composer]**

> "I click Teach, or just type. It pre-fills a prompt: 'Here are my notes on Coffee.' I paste in real notes and send."

**[Action: paste notes / send]**

> "Nous digests this into memory claims scoped to this workspace — not just storing raw text."

**[Result: Remembered confirmation appears in the thread]**

> "That confirmation is the moment it actually has memory to work with."

---

## 4. Landing changes — now "ready"

**[Screen: chat landing updates — title "Long-term memory with autonomous agents", four chips now visible: Teach / Ask / Research / Watch]**

> "Now that there's something in memory, the other three actions unlock: Ask, Research, and Watch. The composer placeholder changes too — 'Teach, ask from memory, or start research.'"

---

## 5. Ask — recall from memory

**[Action: click the Ask chip, or type a question]**

> "Ask answers from what's already in this workspace's memory."

**[Type / send a question grounded in what was just taught]**

**[Result: answer appears inline with source citations back to the taught notes]**

> "It's citing my own notes, not a generic web answer."

---

## 6. Research — run the agents

**[Action: click the Research chip, or type a research goal]**

> "Research runs a multi-agent pipeline on a real goal."

**[Type / send a research prompt]**

**[Screen: status lines stream in the same thread — plan, retrieve, verify, synthesize]**

> "I can watch it work — plan, retrieve, verify, synthesize — all in this same chat, no separate screen."

**[Result: structured report appears with clickable citations]**

> "And it writes back — new claims get added to this workspace's memory, so the next Ask already knows this."

---

## 7. Watch — set up a standing brief

**[Action: sidebar → Watch nav, or type a watch instruction in chat]**

> "Watch sets up a recurring brief on this topic — same memory, but checked proactively instead of only when I ask."

**[Action: describe what to watch for, save/activate]**

---

## 8. New chat, same workspace

**[Action: hover the workspace in the sidebar → `+` next to it → new chat opens under the same workspace]**

> "I can open a second chat under the same workspace. It's a fresh conversation, but it shares the same memory — so I can ask something unrelated to the last thread and it still recalls what was taught earlier."

**[Type a quick Ask in the new chat to prove recall carries over]**

---

## 9. Memory view

**[Action: sidebar → Memory nav]**

> "Last, the Memory view — this isn't another chat, it's a direct look at what the workspace actually knows: the claims, how they connect, what's settled versus still contested."

---

## Quick reference — click path only

1. `+` (sidebar) → name workspace → optional folder/idea → Create
2. Empty chat → Teach chip → paste notes → send → "Remembered"
3. Chips unlock → Ask chip → question → cited answer
4. Research chip → goal → status lines → report → write-back
5. Watch nav (or chat) → describe focus → save/run
6. Workspace `+` → new chat → same memory, new thread
7. Memory nav → claims / graph for that workspace
