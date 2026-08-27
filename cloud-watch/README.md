# Nous Cloud Watch — Better Auth sessions + BYOK

Hosted morning briefs. Identity lives on **Nous Auth** (`auth/` — Better Auth + Postgres email OTP). This service stores watches, briefs, and encrypted LLM keys only.

## User experience

1. Open Nous → vault works immediately (no gate)
2. Settings → **Account** → email → 6-digit code (same flow for new and returning users)
3. Settings → **Models** — add Groq/OpenRouter key; signed-in clients sync it to Cloud Watch
4. Activate Watches — briefs run ~9am on the server and sync when they open Nous

## Operator

### Desktop / sidecar `.env`

```bash
CLOUD_WATCH_URL=https://watch.your-domain.com
# No CLOUD_WATCH_USER_TOKEN — session is Better Auth Bearer from the app
```

### Auth service

See [`auth/README.md`](../auth/README.md). Set the same `AUTH_INTERNAL_SECRET` here:

```bash
AUTH_URL=https://auth.your-domain.com
AUTH_INTERNAL_SECRET=...
CLOUD_WATCH_CRON_TOKEN=$(openssl rand -hex 24)
CLOUD_WATCH_SECRET=$(openssl rand -hex 32)
```

### Start Cloud Watch

```bash
cd cloud-watch && docker compose up --build -d
```

### Cron

```bash
0 9 * * 1-5 curl -fsS -X POST \
  -H "Authorization: Bearer $CLOUD_WATCH_CRON_TOKEN" \
  http://127.0.0.1:8787/internal/run-due
```

## API

| Method | Path | Auth |
|--------|------|------|
| GET | `/v1/me` | Better Auth Bearer (resolved via AUTH_URL) |
| PUT | `/v1/me/llm` | Bearer (BYOK) |
| PUT | `/v1/watches/{id}` | Bearer |
| GET | `/v1/briefs/pending` | Bearer |
| POST | `/v1/briefs/{id}/ack` | Bearer |
| POST | `/internal/run-due` | cron token |

## Local catch-up

If a user never signs in, Nous still runs Watch catch-up **while the app is open**. Cloud is additive.
