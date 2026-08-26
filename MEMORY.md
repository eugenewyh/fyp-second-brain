# Memory contract

Reuse targets (do not fork): `src/second_brain/memory/claims.py`, `digest_link.py`, `learning.py` (`persist_research_memory`), `recall.py`, `src/second_brain/agent/goal_loop.py`, `daily_review.py`, `sidecar/scheduler.py`.

The five memory stages are a checklist on existing Manager jobs, not a sixth agent. One chat binds to one vault topic (`project_path`). Specialists only read and write `{topic}/memory`. There is no global user store.

| Stage | Owner |
|-------|--------|
| Capture | Manager job (`file` / `answer` / `research` / `watch` / `refuse`) |
| Consolidate | `upsert_claims_from_learning` / `digest_and_link` |
| Retrieve | Manager `recall_snapshot` (cheap); Planner `recall_for_query` (~3.5k); Retriever scoped Chroma |
| Reconcile | Dump beats watch (`PROTECTED_ORIGINS`); verifier gates settled claims; contested siblings stay visible |
| Decay | Daily review / scheduler only; expire watch-origin claims (~30d), never dump or settled research |

## Fail closed

Writes require `project_path`. `project_memory_root(None)` does **not** fall back to `DOCUMENTS_DIR/memory`. Missing topic → skip write, `memory_written: false`.

## Claim schema

Frontmatter on `{topic}/memory/claims/{slug}.md`:

- `id` — stable slug/id
- `claim` — atomic sentence
- `status` — `settled` (legacy: `active`) | `contested` | `superseded`
- `origin` — `dump` | `watch` | `research` (plan name: source)
- `source_path` — relative or absolute path of the dump/report
- `source_quote` / span — verbatim evidence, or empty
- `content_hash` — dump hash for idempotency
- `created` / `updated` — ISO date
- `supersedes` — prior claim id when revising
- `expires` — ISO date on **watch-origin** claims only (~+30d)

Ask prefers `settled` (and legacy `active`) personal claims for the main answer, but recall also injects matching `contested` siblings so Ask/Research can say the disagreement in plain language. Watch must not silently overwrite a `dump` claim; it may only add a `contested` sibling. Persist / chat return `contested_claims` so the Manager line can show the fight.

## Skip-list (no digest / no recursive ingest)

Do not treat these as Teach dumps. Vault watcher may still index files; digest-and-link and Watch skip them.

- `{topic}/memory/**` — claims, digests, learnings, agents, project.md
- `{topic}/briefs/**`
- `{topic}/watches/**` — named Watch instructions and briefs
- `{topic}/research/**`
- `{topic}/instruction.md`

## Capture classes (no separate engine)

`origin` + optional `expires` **are** the durable tags. Do not add a MemoryClass enum or global user store.

| Capture class | Job / origin | Durable? |
|---------------|--------------|----------|
| Dump | Teach → `origin=dump` | Yes |
| Research | Research → `origin=research` | Yes if filed (`should_file_research`) |
| Expiring watch | Watch → `origin=watch` + `expires` (~30d) | Yes until decay |
| Ephemeral | Ask / refuse / chat | No write |

Decay stays narrow: daily review expires **watch-origin** claims only (`expire_watch_claims`). Never fade dump or settled research. Retrieve stays thin: ~3.5k chars, handful of settled+contested claims, short `project.md`, few Chroma chunks; `claim_count == 0` → Ask refuses.

## Write paths

| Job | User move | Writer | May write |
|-----|-----------|--------|-----------|
| Teach (`file`) | Dump / files / inferred Send | `digest_and_link` | inbox note, claims (`origin=dump`), `project.md` |
| Research | Manager lookup | `persist_research_memory` | report + learning card + claims if `should_file_research`; settled only when verifier approved (forced max-revisions → contested) |
| Watch | Run now / scheduler | `run_goal_stream` + brief formatter | `research/`, claims (`origin=watch`, optional `expires`), `briefs/` |
| Ask (`answer`) | Question from notes | `chat_with_context` | nothing |
| Refuse | Off-topic | — | nothing |
| Index | Vault watcher | `ingest_file` | Chroma only |

Watcher ingest is index-only: no auto-digest, no auto-Watch.

## Topic routing

One chat binds to one vault folder via `session.projectPath`. Isolation is a hard partition: specialists read and write only that folder unless the user asks otherwise. Similar names never auto-merge.

| Move | User phrase | Effect |
|------|-------------|--------|
| Bind | First real job with no folder | Create/reuse a topic folder; set `projectPath` |
| Retarget | “this is part of FYP”, “file this under DLM”, “switch to FYP” (existing folder) | Move `session.projectPath`. Do **not** copy claims. Old folder stays on disk. |
| Merge | “combine JustGRPO into DLM” only | Copy claims into dest, rewrite `supersedes`, leave source on disk. Bind the chat to dest. |
| Split | “forget JustGRPO, let’s do thesis structure”, “new chat”, “switch to …” (unknown name) | New chat + new folder. Old chat keeps its `projectPath`. Old claims stay put. |
| Also-retrieve | “also check my thesis notes” | Temporary read union of a second `project_path`. Writes stay on the bound topic. Scratchpad stays bound-only. |

Default retrieve is still prefix-scoped. `also_project_paths` is opt-in for that turn only. Do not mix two topics in one `projectPath`.
