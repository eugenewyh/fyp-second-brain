# UAT demo pack — Home Coffee

Fun, non-technical topic for facilitators and participants who are not AI researchers.

## What’s inside

| Path | Purpose |
|------|---------|
| `Coffee/` | Topic folder ready to copy into the vault (`data/documents/Coffee`) |
| `Coffee/IDEA.md` | Personal stance the Manager treats as topic intent |
| `Coffee/notes/*.md` | Dump-style personal notes (gear, beans, routine, recipes, mistakes) |
| `TEACH_DUMP.txt` | Long paste for **Teach** if you prefer chat dump over file ingest |

## Important: files ≠ memory

Copying `Coffee/` into the vault shows notes in Edit workspace, but **Ask only uses memory claims** (`Coffee/memory/claims/`). Until notes are **Remembered / Taught**, the Manager will say the topic has no notes.

The app auto-runs Remember when it sees unfiled notes. You can also:

- Paste `TEACH_DUMP.txt` into the channel, or
- Command palette → Remember topic notes, or
- Open **Coffee** and wait for the digest turn to finish

## Quick setup

```bash
# From repo root — copies the seed into the live vault
cp -R evaluation/demo/Coffee data/documents/Coffee

# Optional: index via CLI (desktop Add docs / vault watcher also works)
python scripts/ingest.py --input data/documents/Coffee
```

In the app: open workspace **Coffee**, expand chats, **+** New Chat if you want a clean thread, wait for Remember if it starts, then follow `uat_questionnaire.md` (Round 2).

## Suggested prompts (Round 2)

**Ask (vault answer)**  
> According to my notes, what do I care about when making espresso at home besides just a strong taste?

**Research (goal run)**  
> Looking at my notes, how do I make espresso at home? Cover grind and dose, steaming milk, and what I’d buy next.

**Second chat (parallel / titles)**  
> What’s my weekday morning coffee routine according to my notes?

**Teach (optional)**  
Paste the full contents of `TEACH_DUMP.txt` into the channel composer.
