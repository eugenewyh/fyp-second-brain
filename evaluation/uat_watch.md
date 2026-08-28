# User Acceptance Testing — Scheduled Research (Local + Cloud)

**Project:** Nous — Graph-Based Multi-Agent System  
**Student:** Wong Yan Hao (TP068819)  
**Feature:** Scheduled Research (standing briefs) + Cloud Scheduled Research (asleep Mac)  
**Duration:** ~15–20 minutes  
**Demo topic:** Home coffee (`data/documents/Coffee`)

Round 2 UAT covers Teach / Ask / Research. This script covers **Scheduled Research only**.

---

## Pre-test (facilitator)

1. Sidecar on `:8765`, desktop open, Models key connected (OpenRouter/Groq).
2. Auth service up (`auth/` on `:3000`) + Cloud Scheduled Research API (`:8787`) with `AUTH_URL` / `AUTH_INTERNAL_SECRET`.
3. Participant signed in via **Settings → Account** (email OTP; local OTP is in auth server logs).
4. Workspace **Coffee** open (copy from `evaluation/demo/Coffee` if missing).

```bash
# Optional seed
cp -R evaluation/demo/Coffee data/documents/Coffee
```

---

## Task A — Local Scheduled Research (8–10 min)

**Goal:** Prove Scheduled Research works while Nous is open (no cloud required for this task).

1. Open **Scheduled Research** (sidebar / sheet).
2. **New schedule** (or chat: “schedule research for new espresso gear and bean notes relevant to my home setup”).
3. Confirm **Focus** + **Include** are filled (not placeholders). Set **Exclude** / **Trusted sources** if shown.
4. Turn **Active** on. Save.
5. Hit **Run**. Wait for the brief (often 1–3 minutes).
6. Confirm:
   - Brief appears under history / latest brief
   - List shows **Brief ready**
   - Status can show “N briefs ready” (click opens Scheduled Research)
7. Hit **Run** again the same day — must rewrite (no “already exists” block).

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| W1 | Creating / editing a schedule felt clear | | | | | |
| W2 | Copy about “while Nous is open / catch-up” matched what happened | | | | | |
| W3 | Run produced a useful morning-style brief | | | | | |
| W4 | I could find today’s brief without hunting the vault | | | | | |
| W5 | Running again the same day worked as expected | | | | | |

**Facilitator pass/fail (local)**

- [ ] Schedule created with `complete: true`
- [ ] Active only when Focus+Include filled
- [ ] Brief written to `Coffee/watches/{id}/briefs/YYYY-MM-DD.md`
- [ ] Same-day Run with force succeeds
- [ ] Brief ready / status chip visible

---

## Task B — Cloud Scheduled Research (6–8 min)

**Goal:** Prove the asleep-Mac path: definition on server → remote run → brief pulled into vault.

1. Stay signed in (Settings → Account). Settings → Connectors → Cloud Scheduled Research: **Models key on server** (or **Sync Models key**).
2. With the active schedule open, **Save** (desktop syncs to cloud) — or facilitator calls sync API with Bearer.
3. Facilitator triggers due run (do **not** wait for 9am):

```bash
# From repo root — uses CLOUD_WATCH_CRON_TOKEN from .env
set -a && source .env && set +a
curl -fsS -X POST http://127.0.0.1:8787/internal/run-due \
  -H "Authorization: Bearer $CLOUD_WATCH_CRON_TOKEN"
```

4. In the app: reopen Scheduled Research / wait for status refresh, or facilitator:

```bash
curl -fsS -X POST http://127.0.0.1:8765/api/cloud-watch/pull
```

5. Confirm a brief is in the vault (new or updated) and UI shows **Brief ready**.

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| W6 | Account email-code sign-in made sense (notes still local) | | | | | |
| W7 | I did not have to paste a second LLM key (Models key reused) | | | | | |
| W8 | I understand Cloud Scheduled Research is for when the Mac is asleep | | | | | |
| W9 | After the cloud run, the brief showed up in Scheduled Research like a local one | | | | | |
| W10 | I would leave an active schedule on for weekday mornings | | | | | |

**Facilitator pass/fail (cloud)**

- [ ] Signed in + `has_api_key`
- [ ] `POST /api/cloud-watch/sync` returns ok for active schedule
- [ ] `/internal/run-due` returns a result for that watch (not skipped for missing key)
- [ ] `POST /api/cloud-watch/pull` writes/acks brief
- [ ] File exists under `Coffee/watches/{id}/briefs/`

---

## Open feedback

1. What was confusing about Scheduled Research vs Research?
2. Would you use local Run only, Cloud, both, or neither?
3. Anything broken or slow?

---

## Facilitator notes

- Local Run ≈ one light Research pass (`WATCH_MAX_PASSES=1`) — budget time.
- Cloud cron uses **server local time**; for Singapore weekday ≥ hour (default 9), noon demos are fine.
- If Cloud Scheduled Research URL is empty, Account is still available but cloud schedules stay off — local catch-up still works.
- Do not put the operator’s free-tier key as the only server key for many users; BYOK sync from Models is required.
- No `CLOUD_WATCH_USER_TOKEN` in `.env` — session is Better Auth Bearer from the desktop.

---

## Facilitator run log — 2026-08-26 (API-assisted)

| Check | Result |
|-------|--------|
| Sidecar `:8765` + Cloud Scheduled Research `:8787` | Pass |
| Signed in + Models key on server (`has_api_key`) | Pass |
| Create active schedule on Coffee (`uat-espresso-watch-2`, complete) | Pass |
| Exclude / Trusted sources update | Pass |
| Cloud sync (`POST /api/cloud-watch/sync`) | Pass |
| Models key sync (`POST /api/cloud-watch/llm/sync`) | Pass |
| Local Run (`force`) → brief on disk (~1.8 min) | Pass |
| `has_brief_today` after local run | Pass |
| Cloud `/internal/run-due` for that watch | Pass (~1.1 min) |
| Cloud pull → vault brief ack | Pass (1 written) |
| Brief file `Coffee/watches/uat-espresso-watch-2/briefs/2026-08-26.md` | Pass |

**Not scored in this automated pass (needs eyes in the desktop UI):** W1–W10 Likert items, status-bar chip click, same-day **Run** button UX.

**Schedule under test:** `uat-espresso-watch-2` on topic Coffee.
