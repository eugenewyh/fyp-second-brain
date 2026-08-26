# Demo prompts — Coffee channel

Prompts drawn from the actual notes in `evaluation/demo/Coffee/notes/` so answers are grounded and checkable on screen. Grouped by function, in script order.

Setup: `cp -R evaluation/demo/Coffee data/documents/Coffee`, then Teach before Ask/Research (files ≠ memory until taught).

---

## 1. Teach

Paste one of these, or the full `evaluation/demo/TEACH_DUMP.txt`, into the composer / Teach chip.

> Remember my coffee notes: I brew espresso at home on a compact machine. The biggest upgrade was a burr grinder — a blade grinder made shots inconsistent. I weigh beans in and liquid out with a digital scale. I dose 18g in for about 36g out in 25–30 seconds. I prefer medium or light-medium roast beans; dark oily beans taste flat on my setup. Filtered water around 100–150ppm works best. I steam milk to 60–65°C — hotter tastes cooked. I want to build a habit that tastes sweet and balanced, not bitter-strong, and I'd rather fix grinding and water before buying a fancier machine.

*(Watch for the "Remembered" card / manager line confirming N claims filed.)*

---

## 2. Ask (grounded, cited answer)

Pick 2–3 for the recording — each should pull a distinct, checkable claim.

> According to my notes, what do I care about when making espresso at home besides just a strong taste?

> What's my dose and yield for a normal shot, according to my notes?

> What water quality works best for my espresso, based on my notes?

> What temperature should I steam milk to, and why, according to what I've taught it?

> What was my biggest mistake before I fixed my espresso setup?

**Good follow-up (shows refuse-instead-of-hallucinate):**
> What espresso machine brand do I own?
*(Notes never name a brand — good moment to show it refuses / says it doesn't know, instead of guessing.)*

---

## 3. Research (multi-agent, cited report, write-back)

> Looking at my notes, how do I make espresso at home? Cover grind and dose, steaming milk, and what I'd buy next.

**Alternative if you want a gap-finding angle (notes literally list open questions):**
> Based on my notes, would a naked portafilter or a single-dose grinder make a bigger difference to my setup, and is there anything my notes don't answer?

*(This one is nice because `mistakes.md` has explicit "Open questions I still want answers for" — good moment to show honesty about gaps.)*

---

## 4. Watch (standing brief)

> Watch for new espresso gear and bean notes relevant to my home setup — I'm especially interested in single-dose grinders and naked portafilters.

---

## 5. Second chat / parallel-session check (optional)

Open a second chat under the same channel:

> What's my weekday morning coffee routine according to my notes?

*(Confirms channel memory is shared across chats but chats stay distinct in the sidebar.)*

---

## Notes on what each prompt proves

| Prompt | Proves |
|---|---|
| Teach dump | Raw notes → durable claims (memory write) |
| "what do I care about besides taste" | Personal-first retrieval, not generic web answer |
| "dose and yield" / "water quality" / "milk temp" | Specific, checkable recall — verifiable against source notes on screen |
| "what machine brand" | Refuses instead of hallucinating when memory doesn't cover it |
| "how do I make espresso... cover grind, milk, next buy" | Multi-agent Research: plan → retrieve → verify → synthesize → write-back |
| "naked portafilter vs single-dose grinder... gaps" | Honesty about what notes don't cover (verifier / gap surfacing) |
| Watch prompt | Standing brief, same memory, proactive |
| Second-chat prompt | Shared channel memory, isolated chat threads |
